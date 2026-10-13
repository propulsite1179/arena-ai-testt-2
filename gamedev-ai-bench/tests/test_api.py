from datetime import datetime,timedelta,timezone
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,inspect,update,text
from gamedev.database import User,Lead,Vote,ArenaMatch,UserSession,TaskVersion,Run,Campaign,AgentConfiguration,Artifact,ScoreSnapshot,RateBucket
from gamedev.security import digest,rate_limit
from gamedev.services.campaigns import create_campaign,claim_run,move_run,cancel_campaign
from gamedev.services.worker import expire_leases
from conftest import post,login,actor,fixture_payload,PASSWORD

@pytest.mark.parametrize('path',['/en','/fr','/en/leaderboard','/fr/leaderboard','/en/models','/en/roblox','/fr/web-games','/en/arena','/fr/compare','/en/lab','/en/news','/fr/methodology','/en/enterprise','/fr/partners','/en/contact','/en/pro','/fr/faq','/en/about','/en/privacy','/en/terms','/en/legal','/fr/login','/en/tasks/web-orbit'])
def test_public_routes(client,path):
    response=client.get(path)
    assert response.status_code==200,response.text[:200]
    assert '<!DOCTYPE html>' in response.text or '<!doctype html>' in response.text
    assert response.headers['x-content-type-options']=='nosniff'
    assert "script-src 'self'" in response.headers['content-security-policy']

def test_catalog_filters_no_fake_scores(client):
    result=client.get('/api/v1/models').json()
    assert result['total']==8 and result['independent_results'] is False
    assert all(m['status']=='not_evaluated' for m in result['items'])
    assert client.get('/api/v1/models?provider=openai').json()['total']==3
    assert client.get('/api/v1/models?limit=2&offset=1').json()['items']==result['items'][1:3]
    assert client.get('/api/v1/models?limit=999').status_code==422
    assert client.get('/api/v1/leaderboard').json()['rows']==[]
    assert client.get('/api/v1/runs').json()['items']==[]
    assert len(client.get('/api/v1/tasks?environment=roblox').json()['items'])==10
    ids=','.join(m['id'] for m in result['items'][:2])
    assert client.get('/api/v1/compare',params={'ids':ids}).json()['recommendation'] is None
    assert client.get('/api/v1/compare?ids=unknown').status_code==400

def test_admin_auth_boundary(client):
    assert client.get('/api/v1/admin/status').status_code==401
    assert client.get('/en/admin',follow_redirects=False).status_code==303
    login(client,'member')
    assert client.get('/api/v1/admin/status').status_code==403
    assert client.get('/en/admin').status_code==403
    assert post(client,'/api/v1/admin/campaigns',fixture_payload(),headers={'Idempotency-Key':'unit-test-abc'}).status_code==403

def test_csrf_and_origin(client):
    payload={'email':'admin@example.test','password':PASSWORD}
    assert client.post('/api/v1/auth/login',json=payload).status_code==403
    token=client.get('/api/v1/session').json()['csrf']
    assert client.post('/api/v1/auth/login',json=payload,headers={'Origin':'https://attacker.test','X-CSRF-Token':token}).status_code==403
    assert post(client,'/api/v1/auth/login',payload).status_code==200
    assert client.post('/api/v1/auth/logout',headers={'Origin':client.app.state.settings.origin,'X-CSRF-Token':token}).status_code==403
    assert post(client,'/api/v1/auth/logout').status_code==200
    assert client.get('/api/v1/session').json()['user'] is None

def test_login_hash_cookies_and_expiry(client,db):
    login(client)
    token=client.cookies['gdb_session']
    with db.session() as session:
        assert session.get(UserSession,token) is None
        record=session.get(UserSession,digest(token));assert record
        record.expires_at=1
    assert client.get('/api/v1/admin/status').status_code==401

def test_register_reject_role_injection_and_duplicate(client):
    payload={'name':'Test','email':'new@example.test','password':PASSWORD,'role':'admin'}
    assert post(client,'/api/v1/auth/register',payload).status_code==422
    del payload['role']
    assert post(client,'/api/v1/auth/register',payload).status_code==201
    assert post(client,'/api/v1/auth/register',payload).status_code==409
    assert post(client,'/api/v1/auth/login',{'email':payload['email'],'password':PASSWORD}).json()['role']=='member'

def test_body_limit(client):
    response=client.post('/api/v1/contact',content=b'x'*512001)
    assert response.status_code==413

def test_rate_limit_atomic_persistent(db):
    assert rate_limit(db,'test-key',2)
    assert rate_limit(db,'test-key',2)
    assert not rate_limit(db,'test-key',2)
    with db.session() as session:assert session.scalar(select(RateBucket.count).where(RateBucket.key.like('test-key:%')))==3

def test_lead_persisted_and_escaped(client,db):
    payload={'name':'<script>bad()</script>','email':'lead@example.test','message':'A real study request with twenty characters.','consent':True,'kind':'enterprise'}
    response=post(client,'/api/v1/contact',payload);assert response.status_code==201
    with db.session() as session:assert session.get(Lead,response.json()['reference']).message==payload['message']
    login(client);html=client.get('/en/admin').text
    assert '<script>bad()</script>' not in html and '&lt;script&gt;bad()&lt;/script&gt;' in html
    assert post(client,'/api/v1/contact',dict(payload,consent=False)).status_code==400

def test_arena_fixture_vote_owner_unique_and_no_ranking(client,db,application):
    match=post(client,'/api/v1/arena/matches',{'mode':'fixture'}).json()
    assert match['fixture'] and match['left']!=match['right']
    payload={'match_id':match['id'],'choice':'tie'}
    assert post(client,'/api/v1/arena/votes',payload).status_code==400
    with db.session() as session:session.get(ArenaMatch,match['id']).created_at=(datetime.now(timezone.utc)-timedelta(seconds=10)).isoformat()
    with TestClient(application) as stranger:
        assert post(stranger,'/api/v1/arena/votes',payload).status_code==404
    response=post(client,'/api/v1/arena/votes',payload)
    assert response.status_code==201,response.text
    assert response.json()['ranking_impact']=='none'
    assert post(client,'/api/v1/arena/votes',payload).status_code==409
    assert client.get('/api/v1/leaderboard').json()['rows']==[]

def test_arena_expired(client,db):
    match=post(client,'/api/v1/arena/matches',{'mode':'fixture'}).json()
    with db.session() as session:session.get(ArenaMatch,match['id']).expires_at=1
    assert post(client,'/api/v1/arena/votes',{'match_id':match['id'],'choice':'both_bad'}).status_code==410

def test_account_save_export_follow_and_delete(client,db):
    login(client,'member')
    ids=[m['id'] for m in client.get('/api/v1/models').json()['items'][:2]]
    assert post(client,'/api/v1/account/comparisons',{'name':'My comparison','model_ids':ids}).status_code==201
    assert post(client,'/api/v1/account/follow/'+ids[0]).status_code==200
    data=client.get('/api/v1/account/export').json()
    assert len(data['comparisons'])==1 and len(data['following'])==1
    assert 'password_hash' not in json.dumps(data)
    assert post(client,'/api/v1/account/delete',{'password':PASSWORD}).status_code==200
    assert client.get('/api/v1/account/export').status_code==401
    with db.session() as session:assert not session.scalar(select(User).where(User.email=='member@example.test'))

def test_last_admin_cannot_be_deleted(client):
    login(client)
    assert post(client,'/api/v1/account/delete',{'password':PASSWORD}).status_code==400

def test_private_task_not_public(client,db):
    with db.session() as session:
        version=session.scalar(select(TaskVersion).where(TaskVersion.task_id=='web-orbit'));version.visibility='private'
    assert not any(row['id']=='web-orbit' for row in client.get('/api/v1/tasks').json()['items'])
    assert client.get('/en/tasks/web-orbit').status_code==404

def test_worker_credentials_revocable(client):
    login(client)
    worker=post(client,'/api/v1/admin/workers',{'name':'Mock consent runner','environment':'roblox'}).json()
    body={'kind':'roblox-local-runner-receipt','verified':False,'test_only':True}
    assert client.post('/api/v1/runner/evidence',json=body).status_code==401
    response=client.post('/api/v1/runner/evidence',json=body,headers={'Authorization':'Bearer '+worker['token']})
    assert response.status_code==202 and response.json()['published'] is False
    assert post(client,'/api/v1/admin/workers/'+worker['id']+'/revoke').status_code==200
    assert client.post('/api/v1/runner/evidence',json=body,headers={'Authorization':'Bearer '+worker['token']}).status_code==401

def test_migrations_idempotent(db):
    db.migrate();db.migrate()
    assert len(inspect(db.engine).get_table_names())==40
    with db.engine.connect() as connection:assert connection.execute(text('PRAGMA foreign_keys')).scalar()==1

def test_campaign_idempotency_queue_lease_and_cancel(client,db):
    login(client);payload=fixture_payload()
    headers={'Idempotency-Key':'fixture-test-key-123'}
    first=post(client,'/api/v1/admin/campaigns',payload,headers=headers)
    assert first.status_code==201,first.text
    second=post(client,'/api/v1/admin/campaigns',payload,headers=headers)
    assert second.json()==first.json()
    assert post(client,'/api/v1/admin/campaigns',dict(payload,name='Changed request'),headers=headers).status_code==400
    claimed=claim_run(db,fixture_only=True);assert claimed
    run_id,token=claimed
    assert claim_run(db,fixture_only=True) is None
    assert client.get('/api/v1/runs/'+run_id).status_code==200
    with pytest.raises(PermissionError):move_run(db,run_id,'wrong','running')
    move_run(db,run_id,token,'running')
    with pytest.raises(ValueError):move_run(db,run_id,token,'completed')
    cancel_campaign(db,actor(db),first.json()['id'])
    with pytest.raises(PermissionError):move_run(db,run_id,token,'evaluating')
    with db.session() as session:
        run=session.get(Run,run_id);assert run.state=='cancelled'
        campaign=session.get(Campaign,run.campaign_id);assert campaign.reserved_microusd==0
    post(client,'/api/v1/auth/logout')
    assert client.get('/api/v1/runs/'+run_id).status_code==404

def test_expired_lease_is_not_retried(client,db):
    login(client)
    post(client,'/api/v1/admin/campaigns',fixture_payload(),headers={'Idempotency-Key':'expired-test-key'})
    run_id,_=claim_run(db)
    with db.session() as session:session.get(Run,run_id).lease_expires_at=1
    assert expire_leases(db)==1
    assert claim_run(db) is None
    with db.session() as session:assert session.get(Run,run_id).state=='failed'

def test_paid_disabled_and_unqualified_tasks(client):
    login(client)
    model=next(m for m in client.get('/api/v1/models').json()['items'] if m['provider_id']=='openai')
    config=model['configurations'][0]['id']
    payload=dict(fixture_payload(),configuration_id=config,authorized_microusd=1_000_000,paid_authorized=True)
    assert post(client,'/api/v1/admin/campaigns',payload,headers={'Idempotency-Key':'paid-never-test'}).status_code==400
    payload['task_ids']=['web-responsive']
    assert post(client,'/api/v1/admin/campaigns/quote',payload).status_code==400

def test_billing_unconfigured(client):
    assert client.post('/api/v1/billing/webhook',json={}).status_code==503
    login(client,'member')
    assert post(client,'/api/v1/billing/checkout',headers={'Idempotency-Key':'billing-test-key'}).status_code==503
