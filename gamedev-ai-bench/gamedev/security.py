"""Opaque sessions, Argon2id, CSRF, bounded input and persistent rate limits."""
import hashlib
import hmac
import re
import secrets
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from gamedev.database import User, UserSession, RateBucket

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(24))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def private_hash(secret: str, value: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r'[^\s@<>]{1,64}@[^\s@<>.]+(?:\.[^\s@<>.]+)+', email):
        raise ValueError('A valid email address is required')
    return email


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 128:
        raise ValueError('Use a password between 12 and 128 characters')
    return PASSWORD_HASHER.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    if len(password) > 128:
        return False
    try:
        return PASSWORD_HASHER.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def create_session(session, user: User) -> tuple[str, str]:
    token, csrf = secrets.token_urlsafe(36), secrets.token_urlsafe(32)
    session.add(UserSession(token_hash=digest(token), user_id=user.id, csrf_hash=digest(csrf),
                            expires_at=int(time.time())+7*86400))
    return token, csrf


def read_session(session, token: str | None):
    if not token or len(token) > 120:
        return None, None
    row = session.get(UserSession, digest(token))
    if not row or row.expires_at <= time.time():
        return None, None
    user = session.get(User, row.user_id)
    return (user, row) if user and user.active else (None, None)


def authorize(user: User | None, roles: tuple[str, ...] = ()) -> bool:
    return bool(user and user.active and (not roles or user.role in roles))


def verify_csrf(record: UserSession, token: str | None) -> bool:
    return bool(token and hmac.compare_digest(record.csrf_hash, digest(token)))


def csrf_token(secret: str, visitor: str) -> str:
    return private_hash(secret, 'csrf:'+visitor)


def redact(value):
    """Conservative public logging. Full prompts and provider payloads stay private."""
    if isinstance(value, dict):
        return {k: '[REDACTED]' if any(s in k.lower() for s in ('secret','password','authorization','api_key','cookie','token'))
                else redact(v) for k,v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'(?i)Bearer\s+\S+', 'Bearer [REDACTED]', value)
        value = re.sub(r'\bsk-[A-Za-z0-9_-]{10,}', '[REDACTED]', value)
        return value[:4000]
    return value


def rate_limit(db, key: str, limit: int, seconds: int = 60) -> bool:
    """DB-backed atomic increment; shared by all web processes.

    Never trusts X-Forwarded-For from arbitrary clients. Reverse-proxy trusted
    hosts must be configured by the operator at the ASGI server.
    """
    window = int(time.time()) // seconds
    full = f'{key}:{window}'
    with db.session() as session:
        if db.engine.dialect.name == 'postgresql':
            from sqlalchemy.dialects.postgresql import insert
        else:
            from sqlalchemy.dialects.sqlite import insert
        statement = insert(RateBucket).values(key=full, window=window, count=1)
        statement = statement.on_conflict_do_update(index_elements=['key'], set_={'count':RateBucket.count+1}).returning(RateBucket.count)
        count = session.execute(statement).scalar_one()
    return count <= limit


def cleanup(db) -> None:
    with db.session() as session:
        session.execute(delete(UserSession).where(UserSession.expires_at < int(time.time())))
        # Rate windows use 60 seconds for application limits.
        session.execute(delete(RateBucket).where(RateBucket.window < int(time.time())//60 - 1440))
