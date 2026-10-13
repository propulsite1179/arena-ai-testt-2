"""Portable operator commands. No default administrator or hidden paid job."""
import argparse
from datetime import datetime,timedelta,timezone
from getpass import getpass
from pathlib import Path
import json
import os
import secrets
import time
from sqlalchemy import select,delete,func
from gamedev.config import Settings
from gamedev.database import Database,User,Model,ModelVersion,AgentConfiguration,Provider,Run,RunEvent,Vote,ArenaMatch,Lead,now
from gamedev.catalog import seed_catalog
from gamedev.core.protocol import HARNESS_VERSION
from gamedev.security import hash_password,normalize_email,cleanup


def main():
    parser=argparse.ArgumentParser(prog='python -m gamedev.cli',description='GameDev AI Bench operator tools')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init',help='Apply migrations and seed sourced catalog; does not create an account or run an AI')
    sub.add_parser('migrate');sub.add_parser('seed')
    admin=sub.add_parser('admin',help='Create an administrator, reviewer or member using a hidden password prompt')
    admin.add_argument('--email',required=True);admin.add_argument('--name',default='Operator');admin.add_argument('--role',choices=['admin','reviewer','member'],default='admin')
    serve=sub.add_parser('serve');serve.add_argument('--host',default='127.0.0.1');serve.add_argument('--port',default=8000,type=int)
    worker=sub.add_parser('worker');worker.add_argument('--once',action='store_true');worker.add_argument('--fixture-only',action='store_true')
    fixture=sub.add_parser('fixture',help='Enqueue the original zero-cost reference fixture. Does not publish it.')
    fixture.add_argument('--email',required=True)
    sub.add_parser('cleanup',help='Remove expired sessions and minimize old contact/vote data')
    reg=sub.add_parser('register-model',help='Add a sourced API identifier; never marks a model evaluated')
    reg.add_argument('--provider',required=True);reg.add_argument('--api-id',required=True);reg.add_argument('--name',required=True);reg.add_argument('--source',required=True)
    reg.add_argument('--source-reviewed',action='store_true')
    args=parser.parse_args();settings=Settings.from_env();db=Database(settings.database_url)
    if args.command in ('init','migrate'):
        print('Migrations applied:',db.migrate())
        if args.command=='init':seed_catalog(db);print('Sourced catalog and original task specifications installed. No benchmark was executed.')
    elif args.command=='seed':seed_catalog(db);print('Catalog seeded idempotently')
    elif args.command=='admin':
        password=getpass('New password (12-128 characters): ')
        if password!=getpass('Repeat password: '):raise ValueError('Passwords do not match')
        with db.session() as session:
            user=User(email=normalize_email(args.email),name=args.name,role=args.role,password_hash=hash_password(password))
            session.add(user);session.flush();print('Created',args.role,user.id)
    elif args.command=='serve':
        import uvicorn
        uvicorn.run('gamedev.web.app:create_app',factory=True,host=args.host,port=args.port,proxy_headers=False)
    elif args.command=='worker':
        from gamedev.services.worker import execute_one,expire_leases
        while True:
            expired=expire_leases(db)
            if expired:print('Expired leases failed without retry:',expired)
            run=execute_one(db,settings,fixture_only=args.fixture_only)
            if run:
                with db.session() as session:print(run,session.get(Run,run).state,flush=True)
            if args.once:break
            if not run:time.sleep(3)
    elif args.command=='fixture':
        from gamedev.services.campaigns import create_campaign
        with db.session() as session:
            user=session.scalar(select(User).where(User.email==normalize_email(args.email)))
            if not user:raise ValueError('Create the operator first')
        print('Queued campaign',create_campaign(db,settings,user,name='Reference harness qualification',configuration_id='fixture-reference',
            suite_id='web-v1',task_ids=['web-orbit'],trials=1,authorized_microusd=0,paid_authorized=False,idempotency_key=secrets.token_hex(16)))
    elif args.command=='cleanup':
        cleanup(db);clock=datetime.now(timezone.utc);old_votes=(clock-timedelta(days=90)).isoformat(timespec='seconds');old_leads=(clock-timedelta(days=180)).isoformat(timespec='seconds')
        with db.session() as session:
            # Real research votes retain aggregated scientific utility; remove identifiers.
            session.execute(delete(Vote).where(Vote.created_at<old_votes,Vote.fixture.is_(True)))
            session.execute(delete(ArenaMatch).where(ArenaMatch.created_at<old_votes,~ArenaMatch.id.in_(select(Vote.match_id))))
            session.execute(delete(Lead).where(Lead.created_at<old_leads))
        print('Retention cleanup complete; published scientific snapshots preserved')
    elif args.command=='register-model':
        import re
        if not args.source_reviewed or not args.source.startswith('https://'):
            raise ValueError('Review the official source and pass --source-reviewed; no automatic confirmation is inferred')
        if not re.fullmatch(r'[A-Za-z0-9._/-]{1,140}',args.api_id):raise ValueError('Invalid API identifier')
        slug=re.sub(r'[^a-z0-9-]+','-',args.provider+'-'+args.api_id.lower()).strip('-')[:100]
        with db.session() as session:
            if not session.get(Provider,args.provider):raise ValueError('Unknown provider')
            if not session.get(Model,slug):session.add(Model(id=slug,name=args.name[:150],provider_id=args.provider));session.flush()
            version=ModelVersion(model_id=slug,api_id=args.api_id,source_url=args.source,source_checked_at=now(),status='not_evaluated',capabilities={'source':'operator-reviewed catalog','api_access_verified':False})
            session.add(version);session.flush();session.add(AgentConfiguration(model_version_id=version.id,harness_id=HARNESS_VERSION,name=args.name[:90]+' / API default',parameters={'max_output_tokens':4096}))
        print('Registered',slug,'as not evaluated. Add a dated price before any paid campaign.')
if __name__=='__main__':main()
