"""Relational persistence: PostgreSQL in production, SQLite for local development.

SQL migrations are checked in and applied transactionally. Published snapshots
are append-only at database level. Data fixtures never enter production rankings.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from hashlib import sha256
from sqlalchemy import (
    create_engine, event, String, Text, Integer, Boolean, JSON, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, select, inspect,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from sqlalchemy.pool import StaticPool


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Identified:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[str] = mapped_column(String(40), default=now, index=True)


class SchemaRevision(Base):
    __tablename__ = 'schema_revisions'
    revision: Mapped[str] = mapped_column(String(30), primary_key=True)
    checksum: Mapped[str] = mapped_column(String(64))
    applied_at: Mapped[str] = mapped_column(String(40), default=now)


class User(Identified, Base):
    __tablename__ = 'users'
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(80), default='')
    role: Mapped[str] = mapped_column(String(20), default='member')
    locale: Mapped[str] = mapped_column(String(2), default='en')
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("role IN ('member','reviewer','admin')"),)


class Organization(Identified, Base):
    __tablename__ = 'organizations'
    name: Mapped[str] = mapped_column(String(120))


class Membership(Identified, Base):
    __tablename__ = 'memberships'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'))
    role: Mapped[str] = mapped_column(String(20), default='member')
    __table_args__ = (UniqueConstraint('user_id', 'organization_id'),)


class UserSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


class Provider(Base):
    __tablename__ = 'providers'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    adapter: Mapped[str] = mapped_column(String(30))
    base_url: Mapped[str] = mapped_column(String(300))
    key_env: Mapped[str] = mapped_column(String(80))
    docs_url: Mapped[str] = mapped_column(String(500))


class Model(Base):
    __tablename__ = 'models'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey('providers.id'), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[dict] = mapped_column(JSON, default=dict)


class ModelVersion(Identified, Base):
    __tablename__ = 'model_versions'
    model_id: Mapped[str] = mapped_column(ForeignKey('models.id'), index=True)
    api_id: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default='not_evaluated')
    availability: Mapped[str] = mapped_column(String(30), default='documented')
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    source_url: Mapped[str] = mapped_column(String(500))
    source_checked_at: Mapped[str] = mapped_column(String(40))
    release_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    alias: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint('model_id', 'api_id'),)


class Harness(Base):
    __tablename__ = 'tool_harnesses'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[str] = mapped_column(String(40))
    tools: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text)


class AgentConfiguration(Identified, Base):
    __tablename__ = 'agent_configurations'
    model_version_id: Mapped[str | None] = mapped_column(ForeignKey('model_versions.id'), nullable=True)
    harness_id: Mapped[str] = mapped_column(ForeignKey('tool_harnesses.id'))
    name: Mapped[str] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(30), default='standardized')
    reasoning: Mapped[str] = mapped_column(String(30), default='provider-default')
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("mode IN ('standardized','agentic','fixture')"),)


class Suite(Base):
    __tablename__ = 'benchmark_suites'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[str] = mapped_column(String(30))
    environment: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[dict] = mapped_column(JSON)
    description: Mapped[dict] = mapped_column(JSON)
    protocol_version: Mapped[str] = mapped_column(String(60))


class Task(Base):
    __tablename__ = 'benchmark_tasks'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    suite_id: Mapped[str] = mapped_column(ForeignKey('benchmark_suites.id'), index=True)
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[dict] = mapped_column(JSON)
    difficulty: Mapped[str] = mapped_column(String(20), default='intermediate')


class TaskVersion(Identified, Base):
    __tablename__ = 'task_versions'
    task_id: Mapped[str] = mapped_column(ForeignKey('benchmark_tasks.id'), index=True)
    version: Mapped[str] = mapped_column(String(20))
    specification: Mapped[dict] = mapped_column(JSON)
    spec_hash: Mapped[str] = mapped_column(String(64))
    visibility: Mapped[str] = mapped_column(String(20), default='public')
    __table_args__ = (UniqueConstraint('task_id', 'version'),)


class Campaign(Identified, Base):
    __tablename__ = 'campaigns'
    name: Mapped[str] = mapped_column(String(150))
    suite_id: Mapped[str] = mapped_column(ForeignKey('benchmark_suites.id'))
    configuration_id: Mapped[str] = mapped_column(ForeignKey('agent_configurations.id'))
    created_by: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    state: Mapped[str] = mapped_column(String(30), default='queued', index=True)
    fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    authorized_microusd: Mapped[int] = mapped_column(Integer, default=0)
    reserved_microusd: Mapped[int] = mapped_column(Integer, default=0)
    spent_microusd: Mapped[int] = mapped_column(Integer, default=0)
    approval: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (
        CheckConstraint('authorized_microusd >= 0'),
        CheckConstraint('reserved_microusd >= 0'),
        CheckConstraint('spent_microusd >= 0'),
        CheckConstraint('reserved_microusd + spent_microusd <= authorized_microusd'),
    )


class Run(Identified, Base):
    __tablename__ = 'runs'
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id'), index=True)
    task_version_id: Mapped[str] = mapped_column(ForeignKey('task_versions.id'), index=True)
    state: Mapped[str] = mapped_column(String(30), default='pending', index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    trial: Mapped[int] = mapped_column(Integer, default=1)
    fixture: Mapped[bool] = mapped_column(Boolean, default=False)
    environment: Mapped[str] = mapped_column(String(20))
    frozen_config: Mapped[dict] = mapped_column(JSON)
    config_hash: Mapped[str] = mapped_column(String(64))
    lease_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    started_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    observed_cost_microusd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    score: Mapped[dict] = mapped_column(JSON, default=dict)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    __table_args__ = (
        UniqueConstraint('campaign_id', 'task_version_id', 'trial', 'attempt'),
        CheckConstraint("state IN ('pending','preparing','running','evaluating','awaiting-review','completed','failed','cancelled')"),
        Index('ix_run_queue', 'state', 'environment', 'created_at'),
    )


class RunEvent(Identified, Base):
    __tablename__ = 'run_events'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    public: Mapped[bool] = mapped_column(Boolean, default=False)


class ToolCall(Identified, Base):
    __tablename__ = 'tool_calls'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    tool: Mapped[str] = mapped_column(String(100))
    arguments_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[int] = mapped_column(Integer)


class AssertionResult(Identified, Base):
    __tablename__ = 'test_results'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    assertion_id: Mapped[str] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(20))
    weight: Mapped[int] = mapped_column(Integer)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False)
    observed: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint('run_id', 'assertion_id'), CheckConstraint("outcome IN ('passed','failed','not_run','error')"))


class Artifact(Identified, Base):
    __tablename__ = 'artifacts'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    name: Mapped[str] = mapped_column(String(180))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(100))
    public: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('run_id', 'name'),)


class HumanReview(Identified, Base):
    __tablename__ = 'human_reviews'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    verdict: Mapped[str] = mapped_column(String(20))
    rubric: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text)
    conflict_of_interest: Mapped[bool] = mapped_column(Boolean, default=False)


class ScoreSnapshot(Identified, Base):
    __tablename__ = 'score_snapshots'
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), index=True)
    protocol_version: Mapped[str] = mapped_column(String(60))
    snapshot: Mapped[dict] = mapped_column(JSON)
    sha256: Mapped[str] = mapped_column(String(64))
    supersedes: Mapped[str | None] = mapped_column(ForeignKey('score_snapshots.id'), nullable=True)


class ArenaMatch(Identified, Base):
    __tablename__ = 'arena_matches'
    visitor_hash: Mapped[str] = mapped_column(String(64), index=True)
    left_run_id: Mapped[str | None] = mapped_column(ForeignKey('runs.id'), nullable=True)
    right_run_id: Mapped[str | None] = mapped_column(ForeignKey('runs.id'), nullable=True)
    left_fixture: Mapped[str | None] = mapped_column(String(30), nullable=True)
    right_fixture: Mapped[str | None] = mapped_column(String(30), nullable=True)
    fixture: Mapped[bool] = mapped_column(Boolean, default=True)
    task_id: Mapped[str] = mapped_column(ForeignKey('benchmark_tasks.id'))
    expires_at: Mapped[int] = mapped_column(Integer)


class Vote(Identified, Base):
    __tablename__ = 'votes'
    match_id: Mapped[str] = mapped_column(ForeignKey('arena_matches.id'), unique=True)
    visitor_hash: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    choice: Mapped[str] = mapped_column(String(20))
    fixture: Mapped[bool] = mapped_column(Boolean)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (CheckConstraint("choice IN ('a','b','tie','both_bad')"),)


class ModelAnnouncement(Identified, Base):
    __tablename__ = 'model_announcements'
    provider_id: Mapped[str] = mapped_column(ForeignKey('providers.id'))
    api_id: Mapped[str] = mapped_column(String(150))
    source_url: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('provider_id', 'api_id'),)


class PriceHistory(Identified, Base):
    __tablename__ = 'price_history'
    model_version_id: Mapped[str] = mapped_column(ForeignKey('model_versions.id'), index=True)
    input_per_million: Mapped[str] = mapped_column(String(30))
    output_per_million: Mapped[str] = mapped_column(String(30))
    cached_per_million: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500))
    checked_at: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str] = mapped_column(Text, default='Standard text tier; not an invoice.')


class ResearchPost(Identified, Base):
    __tablename__ = 'research_posts'
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[dict] = mapped_column(JSON)
    body: Mapped[dict] = mapped_column(JSON)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    published: Mapped[bool] = mapped_column(Boolean, default=False)


class Notification(Identified, Base):
    __tablename__ = 'notifications'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    kind: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict] = mapped_column(JSON)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Subscription(Identified, Base):
    __tablename__ = 'subscriptions'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    provider_id: Mapped[str] = mapped_column(String(150), unique=True)
    status: Mapped[str] = mapped_column(String(40))
    plan: Mapped[str] = mapped_column(String(50), default='pro')
    __table_args__ = (UniqueConstraint('user_id', 'plan'),)


class Sponsorship(Identified, Base):
    __tablename__ = 'sponsorships'
    organization: Mapped[str] = mapped_column(String(150))
    disclosure: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    # Deliberately no relation granting score-edit permissions.


class Report(Identified, Base):
    __tablename__ = 'reports'
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey('runs.id'), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='open')


class APIKey(Identified, Base):
    __tablename__ = 'api_keys'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    scopes: Mapped[list] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Identified, Base):
    __tablename__ = 'audit_logs'
    actor_id: Mapped[str | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    target: Mapped[str] = mapped_column(String(150))
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Lead(Identified, Base):
    __tablename__ = 'leads'
    email: Mapped[str] = mapped_column(String(254))
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    consent: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(30), default='new')


class SavedComparison(Identified, Base):
    __tablename__ = 'saved_comparisons'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    model_ids: Mapped[list] = mapped_column(JSON)


class Follow(Identified, Base):
    __tablename__ = 'model_follows'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    model_id: Mapped[str] = mapped_column(ForeignKey('models.id'))
    email_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint('user_id', 'model_id'),)


class Worker(Identified, Base):
    __tablename__ = 'workers'
    name: Mapped[str] = mapped_column(String(100))
    environment: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[str | None] = mapped_column(String(40), nullable=True)


class RateBucket(Base):
    __tablename__ = 'rate_buckets'
    key: Mapped[str] = mapped_column(String(150), primary_key=True)
    window: Mapped[int] = mapped_column(Integer, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class WebhookEvent(Base):
    __tablename__ = 'webhook_events'
    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    kind: Mapped[str] = mapped_column(String(60))
    received_at: Mapped[str] = mapped_column(String(40), default=now)


class IdempotencyRecord(Base):
    __tablename__ = 'idempotency_records'
    key: Mapped[str] = mapped_column(String(150), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(80))


class Database:
    def __init__(self, url: str):
        kwargs = {'future': True, 'pool_pre_ping': True}
        if url.startswith('sqlite'):
            kwargs['connect_args'] = {'check_same_thread': False, 'timeout': 30}
            if ':memory:' in url:
                kwargs['poolclass'] = StaticPool
        self.engine = create_engine(url, **kwargs)
        if url.startswith('sqlite'):
            @event.listens_for(self.engine, 'connect')
            def sqlite_settings(connection, record):
                cursor = connection.cursor()
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.execute('PRAGMA busy_timeout=30000')
                cursor.execute('PRAGMA journal_mode=WAL')
                cursor.close()
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    @contextmanager
    def session(self):
        with self.sessions() as session:
            try:
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    def migrate(self, directory: Path | None = None) -> list[str]:
        directory = directory or Path(__file__).resolve().parents[1] / 'migrations'
        dialect = self.engine.dialect.name
        applied = []
        for path in sorted(directory.glob(f'*_{dialect}.sql')):
            revision = path.name.split('_')[0]
            data = path.read_bytes()
            checksum = sha256(data).hexdigest()
            with self.engine.begin() as connection:
                if inspect(connection).has_table('schema_revisions'):
                    old = connection.execute(select(SchemaRevision).where(SchemaRevision.revision == revision)).mappings().first()
                    if old:
                        if old['checksum'] != checksum:
                            raise RuntimeError(f'Applied migration {revision} was modified')
                        continue
                for statement in data.decode().split('\n-- statement\n'):
                    if statement.strip():
                        connection.exec_driver_sql(statement.strip())
                connection.execute(SchemaRevision.__table__.insert().values(revision=revision, checksum=checksum, applied_at=now()))
                applied.append(revision)
        if not inspect(self.engine).has_table('users'):
            raise RuntimeError('No schema migrations available for this database')
        return applied
