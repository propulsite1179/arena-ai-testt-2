"""Release engineering only: generate the INITIAL schema before first deployment.
Never overwrite an applied migration. Future changes need a new numbered file.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import sqlite, postgresql
from gamedev.database import Base

root = Path(__file__).resolve().parents[1] / 'migrations'
for name, dialect in [('sqlite', sqlite.dialect()), ('postgresql', postgresql.dialect())]:
    path = root / f'0001_{name}.sql'
    if path.exists():
        raise SystemExit(f'Refusing to overwrite {path}')
    statements = [str(CreateTable(t).compile(dialect=dialect)).strip() for t in Base.metadata.sorted_tables]
    statements += [str(CreateIndex(i).compile(dialect=dialect)) for t in Base.metadata.sorted_tables for i in t.indexes]
    if name == 'sqlite':
        statements += [f"CREATE TRIGGER immutable_snapshot_{verb.lower()} BEFORE {verb} ON score_snapshots BEGIN SELECT RAISE(ABORT, 'Published snapshots are append-only'); END" for verb in ['UPDATE', 'DELETE']]
    else:
        statements += ["CREATE FUNCTION reject_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Published snapshots are append-only'; END; $$",
                       "CREATE TRIGGER immutable_snapshot BEFORE UPDATE OR DELETE ON score_snapshots FOR EACH ROW EXECUTE FUNCTION reject_snapshot_mutation()"]
    path.write_text('\n-- statement\n'.join(statements)+'\n', encoding='utf-8')
    print(path.name, len(statements), 'statements')
