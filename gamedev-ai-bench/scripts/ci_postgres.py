"""Destructive-test-free qualification of a fresh, ephemeral local CI database."""
from pathlib import Path
import concurrent.futures,json,os,secrets,sys,tempfile
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,select,func,text
from gamedev.database import Database,User,Run,ScoreSnapshot,now
from gamedev.catalog import seed_catalog
from gamedev.config import Settings,ROOT
from gamedev.security import hash_password
from gamedev.services.campaigns import create_campaign,claim_run

def main():
    url=os.environ['POSTGRES_TEST_URL'];parsed=urlparse(url)
    if parsed.hostname not in ('127.0.0.1','localhost') or parsed.path!='/gamedev_ci':raise ValueError('Use only the ephemeral local gamedev_ci database')
    db=Database(url)
    if inspect(db.engine).get_table_names():raise ValueError('CI database must start completely empty')
    assert db.migrate()==['0001'] and db.migrate()==[]
    seed_catalog(db);seed_catalog(db)
    assert len(inspect(db.engine).get_table_names())==40
    with db.session() as session:
        person=User(email='postgres-ci@example.test',name='CI only',role='admin',password_hash=hash_password(secrets.token_urlsafe(30)))
        session.add(person);session.flush()
    with tempfile.TemporaryDirectory(prefix='gdb-pg-ci-') as temp:
        settings=Settings(database_url=url,data_dir=Path(temp),secret=secrets.token_urlsafe(48))
        campaign=create_campaign(db,settings,person,name='PostgreSQL lease qualification fixture',configuration_id='fixture-reference',suite_id='web-v1',task_ids=['web-orbit'],trials=8,authorized_microusd=0,paid_authorized=False,idempotency_key='pg-ci-unique')
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:claimed=list(pool.map(lambda _:claim_run(db,fixture_only=True),range(8)))
        assert all(claimed) and len({item[0] for item in claimed})==8
        assert claim_run(db,fixture_only=True) is None
        with db.session() as session:
            assert session.scalar(select(func.count()).select_from(Run).where(Run.campaign_id==campaign,Run.state=='preparing'))==8
    report={'kind':'ephemeral-postgresql-ci','dialect':db.engine.dialect.name,'tables':40,'migration_idempotence':True,'seed_idempotence':True,'concurrent_unique_leases':8,'paid_requests':0,'native_studio_tests':0}
    (ROOT/'evidence/postgresql-ci.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));db.engine.dispose()
if __name__=='__main__':main()
