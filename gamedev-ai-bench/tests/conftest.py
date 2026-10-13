"""Ephemeral, isolated test databases. No live model keys, no paid calls."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from gamedev.config import Settings
from gamedev.database import Database,User
from gamedev.security import hash_password
from gamedev.web.app import create_app

PASSWORD='Local-test-password-2026!'
@pytest.fixture(scope='session')
def encoded_password():return hash_password(PASSWORD)

@pytest.fixture
def application(tmp_path,encoded_password,monkeypatch):
    for key in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','DEEPSEEK_API_KEY','QWEN_API_KEY','ZAI_API_KEY','MOONSHOT_API_KEY','STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','STRIPE_PRICE_ID'):
        monkeypatch.delenv(key,raising=False)
    settings=Settings(data_dir=tmp_path/'data',database_url='sqlite:///'+str(tmp_path/'test.db'),secret='t'*64,allow_registration=True)
    db=Database(settings.database_url)
    app=create_app(settings,db)
    with db.session() as session:
        for role in ('admin','reviewer','member'):
            session.add(User(email=role+'@example.test',name=role.title(),password_hash=encoded_password,role=role,locale='en'))
    yield app
    db.engine.dispose()

@pytest.fixture
def client(application):
    with TestClient(application) as client:yield client

@pytest.fixture
def db(application):return application.state.db

def post(client,path,payload=None,**kwargs):
    headers={'Origin':client.app.state.settings.origin,'X-CSRF-Token':client.get('/api/v1/session').json()['csrf']}
    headers.update(kwargs.pop('headers',{}))
    return client.post(path,json=payload,headers=headers,**kwargs)

def login(client,role='admin'):
    response=post(client,'/api/v1/auth/login',{'email':role+'@example.test','password':PASSWORD})
    assert response.status_code==200,response.text
    return response

def actor(db,role='admin'):
    with db.session() as session:return session.scalar(select(User).where(User.role==role))

def fixture_payload(**overrides):
    return dict(name='Explicit harness fixture test',configuration_id='fixture-reference',suite_id='web-v1',task_ids=['web-orbit'],trials=1,authorized_microusd=0,paid_authorized=False,**overrides)
