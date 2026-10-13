"""Explicit configuration, safe local defaults, and production fail-closed checks."""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import os
import secrets

ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path | None = None) -> None:
    path = path or ROOT / '.env'
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key.isidentifier():
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    environment: str = 'development'
    origin: str = 'http://127.0.0.1:8000'
    database_url: str = 'sqlite:///var/bench.db'
    data_dir: Path = ROOT / 'var'
    secret: str = ''
    allow_registration: bool = False
    paid_runs: bool = False
    game_origin: str = ''
    contact_email: str = ''
    legal_entity: str = ''
    legal_address: str = ''

    @property
    def production(self) -> bool:
        return self.environment == 'production'

    @classmethod
    def from_env(cls) -> 'Settings':
        load_env()
        data = Path(os.getenv('DATA_DIR', str(ROOT / 'var'))).resolve()
        data.mkdir(parents=True, exist_ok=True)
        secret = os.getenv('APP_SECRET', '')
        production = os.getenv('APP_ENV') == 'production'
        if not secret and not production:
            key_file = data / '.local-session-key'
            if not key_file.exists():
                fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    stream.write(secrets.token_urlsafe(48))
            secret = key_file.read_text().strip()
        settings = cls(
            environment=os.getenv('APP_ENV', 'development'),
            origin=os.getenv('APP_ORIGIN', 'http://127.0.0.1:8000').rstrip('/'),
            database_url=os.getenv('DATABASE_URL', f'sqlite:///{data / "bench.db"}'),
            data_dir=data, secret=secret,
            allow_registration=os.getenv('ALLOW_REGISTRATION') == 'true',
            paid_runs=os.getenv('ENABLE_PAID_RUNS') == 'true',
            game_origin=os.getenv('GAME_ORIGIN', '').rstrip('/'),
            contact_email=os.getenv('CONTACT_EMAIL', ''),
            legal_entity=os.getenv('LEGAL_ENTITY', ''),
            legal_address=os.getenv('LEGAL_ADDRESS', ''),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        parsed = urlparse(self.origin)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('APP_ORIGIN must be an HTTP(S) origin')
        game = urlparse(self.game_origin)
        if self.game_origin and (game.scheme not in ('http', 'https') or not game.hostname or game.username or game.password or game.path not in ('', '/') or game.query or game.fragment):
            raise ValueError('GAME_ORIGIN must be a standalone HTTP(S) origin')
        if self.game_origin and game.netloc == parsed.netloc:
            raise ValueError('Generated games must use a distinct origin')
        if self.production:
            if len(self.secret) < 48:
                raise ValueError('Production requires a random APP_SECRET of at least 48 characters')
            if not self.origin.startswith('https://') or (self.game_origin and game.scheme != 'https'):
                raise ValueError('Production requires HTTPS')
            if not self.database_url.startswith('postgresql'):
                raise ValueError('Production requires PostgreSQL; SQLite is a development fallback')
