"""Server-rendered application and versioned, authenticated API."""
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from typing import Literal
from urllib.parse import quote
import csv
import hmac
import io
import json
import os
import secrets
import time
import uuid
from fastapi import FastAPI,Request,HTTPException,Query
from fastapi.responses import JSONResponse,HTMLResponse,RedirectResponse,Response,FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select,func,delete,update
from sqlalchemy.exc import IntegrityError
from jinja2 import Environment,FileSystemLoader,select_autoescape
from gamedev.config import Settings,ROOT
from gamedev.database import *
from gamedev.catalog import seed_catalog,CHECKED
from gamedev.security import (normalize_email,hash_password,verify_password,DUMMY_HASH,create_session,read_session,
    authorize,verify_csrf,csrf_token,digest,private_hash,rate_limit,redact)
from gamedev.services import public_data as data
from gamedev.services.campaigns import create_campaign,quote_campaign,cancel_campaign,review_run
from gamedev.core.artifacts import ArtifactStore
from gamedev.core.protocol import canonical_hash,compare_configurations
from gamedev.services.billing import verify_signature,process_event,checkout
from gamedev.adapters.providers import ProviderAdapter,ProviderError

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')
class LoginInput(Input):
    email:str=Field(max_length=254);password:str=Field(max_length=128)
class RegisterInput(LoginInput):
    name:str=Field(min_length=1,max_length=80);locale:Literal['en','fr']='en'
class LeadInput(Input):
    email:str=Field(max_length=254);name:str=Field(min_length=1,max_length=100)
    kind:Literal['enterprise','partnership','contact','pro']='contact'
    message:str=Field(min_length=20,max_length=5000);consent:bool
    website:str=Field(default='',max_length=200)
class MatchInput(Input):
    mode:Literal['fixture']='fixture'
class VoteInput(Input):
    match_id:str=Field(max_length=36);choice:Literal['a','b','tie','both_bad']
class CampaignInput(Input):
    name:str=Field(min_length=3,max_length=150);configuration_id:str=Field(max_length=36)
    suite_id:str=Field(max_length=80);task_ids:list[str]=Field(min_length=1,max_length=30)
    trials:int=Field(default=1,ge=1,le=10);authorized_microusd:int=Field(default=0,ge=0,le=1_000_000_000)
    paid_authorized:bool=False
class ReviewInput(Input):
    verdict:Literal['approve','reject'];notes:str=Field(min_length=12,max_length=5000)
    rubric:dict=Field(default_factory=dict);conflict_of_interest:bool=False
class SaveInput(Input):
    name:str=Field(min_length=1,max_length=100);model_ids:list[str]=Field(min_length=2,max_length=4)
class PasswordInput(Input):
    password:str=Field(max_length=128)
class WorkerInput(Input):
    name:str=Field(min_length=3,max_length=100);environment:Literal['roblox','web']='roblox'
class PriceInput(Input):
    model_version_id:str=Field(max_length=36);input_per_million:str=Field(pattern=r'^\d{1,4}(\.\d{1,6})?$')
    output_per_million:str=Field(pattern=r'^\d{1,4}(\.\d{1,6})?$');cached_per_million:str|None=Field(default=None,pattern=r'^\d{1,4}(\.\d{1,6})?$')
    source_url:str=Field(pattern=r'^https://[^\s]{5,480}$');checked_at:str=Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
class ConfigurationInput(Input):
    model_version_id:str=Field(max_length=36);name:str=Field(min_length=3,max_length=120)
    reasoning:str=Field(default='provider-default',max_length=30);max_output_tokens:int=Field(default=4096,ge=128,le=32768)

class BodyLimit:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in ('POST','PUT','PATCH','DELETE'):
            return await self.app(scope,receive,send)
        body=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            body.extend(message.get('body',b''))
            if len(body)>512_000:
                return await JSONResponse({'detail':'Request body exceeds 512 KB'},status_code=413)(scope,receive,send)
            if not message.get('more_body'):break
        replayed=False
        async def replay():
            nonlocal replayed
            if not replayed:
                replayed=True;return {'type':'http.request','body':bytes(body),'more_body':False}
            return await receive()
        await self.app(scope,replay,send)


def create_app(settings:Settings|None=None,database:Database|None=None):
    settings=settings or Settings.from_env();settings.validate()
    db=database or Database(settings.database_url)
    settings.data_dir.mkdir(parents=True,exist_ok=True)
    if not settings.production:
        db.migrate();seed_catalog(db)
    store=ArtifactStore(settings.data_dir/'artifacts')
    app=FastAPI(title='GameDev AI Bench API',version='0.1.0',docs_url=None,redoc_url=None,openapi_url='/api/v1/openapi.json')
    app.state.db=db;app.state.settings=settings;app.state.store=store
    templates=Environment(loader=FileSystemLoader(ROOT/'gamedev/web/templates'),autoescape=select_autoescape(['html','xml']))
    locales={language:json.loads((ROOT/f'gamedev/web/locales/{language}.json').read_text()) for language in ('en','fr')}
    templates.globals['icon']=lambda name:''  # Replaced by safe inline template macro.

    def require(request:Request,roles=()):
        user=request.state.user
        if not authorize(user,roles):raise HTTPException(403 if user else 401,'Administrator/reviewer required' if roles else 'Sign in required')
        return user
    def limit(request:Request,bucket:str,count:int=30):
        address=request.client.host if request.client else 'unknown'
        if not rate_limit(db,bucket+':'+private_hash(settings.secret,address)[:32],count):raise HTTPException(429,'Rate limit reached; try again later')
    def key(request:Request):
        value=request.headers.get('Idempotency-Key','')
        if len(value)<8 or len(value)>80 or not value.isascii() or not all(c.isalnum() or c in '-_' for c in value):
            raise HTTPException(400,'A unique Idempotency-Key (8-80 ASCII characters) is required')
        return value

    @app.middleware('http')
    async def security(request:Request,call_next):
        signed=request.cookies.get('gdb_visitor','');parts=signed.split('.')
        visitor=parts[0] if len(parts)==2 and len(parts[0])<100 and hmac.compare_digest(parts[1],private_hash(settings.secret,parts[0])) else secrets.token_urlsafe(24)
        request.state.visitor=visitor
        with db.session() as session:user,record=read_session(session,request.cookies.get('gdb_session'))
        request.state.user=user;request.state.session=record
        supplied_csrf=request.cookies.get('gdb_csrf','')
        request.state.csrf=supplied_csrf if record and verify_csrf(record,supplied_csrf) else csrf_token(settings.secret,visitor) if not record else ''
        exempt=request.url.path in ('/api/v1/billing/webhook','/api/v1/runner/evidence')
        if request.method not in ('GET','HEAD','OPTIONS') and not exempt:
            origin=request.headers.get('origin')
            token=request.headers.get('x-csrf-token','')
            valid=verify_csrf(record,token) if record else hmac.compare_digest(csrf_token(settings.secret,visitor),token)
            if origin!=settings.origin or not valid:
                return JSONResponse({'detail':'Invalid origin or CSRF token'},status_code=403)
        response=await call_next(request)
        if visitor!=parts[0] or len(parts)!=2:
            response.set_cookie('gdb_visitor',visitor+'.'+private_hash(settings.secret,visitor),httponly=True,secure=settings.production,samesite='lax',max_age=30*86400)
        response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=(), payment=()'
        response.headers['X-Frame-Options']='DENY'
        if settings.production:response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
        frame=f"'self' {settings.game_origin}" if settings.game_origin else "'self'"
        response.headers.setdefault('Content-Security-Policy',f"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src {frame}; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
        if user or request.url.path.startswith('/api/v1/admin') or '/login' in request.url.path or '/account' in request.url.path:
            response.headers['Cache-Control']='no-store'
        if request.url.path.startswith('/fixtures/'):
            del response.headers['X-Frame-Options']
            response.headers['Content-Security-Policy']="default-src 'none'; script-src 'self'; style-src 'self'; img-src data:; connect-src 'none'; frame-ancestors 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"
        return response
    app.add_middleware(BodyLimit)

    @app.exception_handler(ValueError)
    async def invalid(request,exc):return JSONResponse({'detail':str(exc)[:500]},status_code=400)
    @app.exception_handler(PermissionError)
    async def forbidden(request,exc):return JSONResponse({'detail':str(exc)},status_code=403)
    @app.exception_handler(IntegrityError)
    async def conflict(request,exc):return JSONResponse({'detail':'Conflicting or duplicate operation; refresh before retrying'},status_code=409)

    @app.get('/api/v1/health')
    def health():
        with db.session() as session:session.scalar(select(func.count()).select_from(SchemaRevision))
        return {'status':'ok','version':'0.1.0','database':db.engine.dialect.name,'paid_runs_enabled':settings.paid_runs,
                'roblox_studio_verified':False,'billing_configured':bool(os.getenv('STRIPE_SECRET_KEY') and os.getenv('STRIPE_PRICE_ID'))}
    @app.get('/api/v1/session')
    def session_info(request:Request):
        user=request.state.user
        return {'csrf':request.state.csrf,'user':{'id':user.id,'name':user.name,'role':user.role,'locale':user.locale} if user else None,
            'registration_enabled':settings.allow_registration}
    @app.post('/api/v1/auth/login')
    def login(payload:LoginInput,request:Request):
        limit(request,'login',8);email=normalize_email(payload.email)
        with db.session() as session:
            user=session.scalar(select(User).where(User.email==email))
            valid=verify_password(user.password_hash if user else DUMMY_HASH,payload.password)
            if not user or not valid or not user.active:raise HTTPException(401,'Invalid email or password')
            token,csrf=create_session(session,user)
            session.add(AuditLog(actor_id=user.id,action='auth.login',target=user.id,data={}))
        response=JSONResponse({'ok':True,'role':user.role,'csrf':csrf})
        response.set_cookie('gdb_session',token,httponly=True,secure=settings.production,samesite='lax',max_age=7*86400)
        response.set_cookie('gdb_csrf',csrf,httponly=False,secure=settings.production,samesite='strict',max_age=7*86400)
        return response
    @app.post('/api/v1/auth/register',status_code=201)
    def register(payload:RegisterInput,request:Request):
        limit(request,'register',4)
        if not settings.allow_registration:raise HTTPException(503,'Public registration is not enabled. An operator can create an account with the CLI.')
        with db.session() as session:
            user=User(email=normalize_email(payload.email),password_hash=hash_password(payload.password),name=payload.name,locale=payload.locale,role='member')
            session.add(user);session.flush()
            return {'created':True,'email_verified':False,'notice':'Sign in. Email verification and password reset delivery are not configured.'}
    @app.post('/api/v1/auth/logout')
    def logout(request:Request):
        require(request)
        with db.session() as session:session.execute(delete(UserSession).where(UserSession.token_hash==request.state.session.token_hash))
        response=JSONResponse({'ok':True});response.delete_cookie('gdb_session');response.delete_cookie('gdb_csrf');return response

    @app.get('/api/v1/models')
    def models(q:str=Query(default='',max_length=100),provider:str=Query(default='',max_length=50),offset:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):
        with db.session() as session:rows=data.models(session)
        filtered=[row for row in rows if (not provider or row['provider_id']==provider) and q.casefold() in (row['name']+' '+row['api_id']).casefold()]
        return {'items':filtered[offset:offset+limit],'total':len(filtered),'catalog_checked_at':CHECKED,'independent_results':False}
    @app.get('/api/v1/models/{model_id}')
    def model_detail(model_id:str):
        with db.session() as session:row=next((m for m in data.models(session) if m['id']==model_id),None)
        if not row:raise HTTPException(404,'Model not found')
        return row
    @app.get('/api/v1/tasks')
    def tasks(environment:Literal['web','roblox']|None=None):
        with db.session() as session:return {'items':data.tasks(session,environment)}
    @app.get('/api/v1/leaderboard')
    def board(environment:Literal['web','roblox']='web'):
        with db.session() as session:return data.leaderboard(session,environment)
    @app.get('/api/v1/export/{kind}')
    def export(kind:Literal['json','csv'],environment:Literal['web','roblox']='web'):
        with db.session() as session:result=data.leaderboard(session,environment)
        if kind=='json':return JSONResponse(result,headers={'Content-Disposition':'attachment; filename="gamedev-results.json"'})
        stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['model','configuration','cohort','trials','score','evidence'])
        def cell(value):
            text=str(value);return "'"+text if text.startswith(('=','+','-','@','\t','\r')) else text
        for row in result['rows']:writer.writerow([cell(row['name']),row['configuration_id'],row['cohort'],row['trials'],row['score'].get('mean'),row['score']['evidence']])
        return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="gamedev-results.csv"'})
    @app.get('/api/v1/compare')
    def compare(ids:str=Query(max_length=400)):
        ids=list(dict.fromkeys(ids.split(',')))
        if not 2<=len(ids)<=4:raise ValueError('Select two to four distinct models')
        with db.session() as session:
            items=[m for m in data.models(session) if m['id'] in ids]
            if len(items)!=len(ids):raise HTTPException(404,'Unknown model')
            return {'items':items,'recommendation':None,'reason':'Insufficient independently evaluated evidence. Provider metadata cannot establish a winner.'}
    @app.get('/api/v1/runs')
    def runs():
        with db.session() as session:return {'items':data.runs(session)}
    @app.get('/api/v1/runs/{run_id}')
    def run(run_id:str,request:Request):
        with db.session() as session:row=data.run_detail(session,run_id,authorize(request.state.user,('admin','reviewer')))
        if not row:raise HTTPException(404,'Run not found')
        return row
    @app.get('/api/v1/artifacts/{artifact_id}')
    def artifact(artifact_id:str,request:Request,preview:bool=False):
        with db.session() as session:
            item=session.get(Artifact,artifact_id)
            parent=session.get(Run,item.run_id) if item else None
            version=session.get(TaskVersion,parent.task_version_id) if parent else None
            if not item or (not authorize(request.state.user,('admin','reviewer')) and (not item.public or not parent.published or version.visibility!='public')):
                raise HTTPException(404,'Artifact not found')
            content=store.get(item.sha256)
            # Never serve generated HTML or script as active same-origin content.
            media='image/png' if preview and item.media_type=='image/png' and content.startswith(b'\x89PNG\r\n\x1a\n') else 'application/octet-stream'
            return Response(content,media_type=media,headers={'Content-Disposition':('inline' if media=='image/png' else 'attachment')+f'; filename="{item.name}"',
                'Content-Security-Policy':"default-src 'none'; sandbox",'ETag':'"'+item.sha256+'"'})
    @app.get('/fixtures/{fixture}/{name}')
    def fixture(fixture:Literal['orbital','meadow'],name:Literal['index.html','style.css','game.js']):
        return FileResponse(ROOT/'packages/test-fixtures/games'/fixture/name)
    @app.post('/api/v1/contact',status_code=201)
    def contact(payload:LeadInput,request:Request):
        limit(request,'contact',5)
        if not payload.consent:raise ValueError('Consent to process this request is required')
        if payload.website:raise ValueError('Submission could not be accepted')
        with db.session() as session:
            lead=Lead(email=normalize_email(payload.email),name=payload.name,kind=payload.kind,message=payload.message,consent=True)
            session.add(lead);session.flush();return {'accepted':True,'reference':lead.id,'delivery':'Saved to the operator inbox; no external email was sent'}

    @app.post('/api/v1/arena/matches',status_code=201)
    def arena_match(payload:MatchInput,request:Request):
        limit(request,'arena-match',20);fixtures=['orbital','meadow'];secrets.SystemRandom().shuffle(fixtures)
        with db.session() as session:
            match=ArenaMatch(visitor_hash=private_hash(settings.secret,request.state.visitor),left_fixture=fixtures[0],right_fixture=fixtures[1],
                fixture=True,task_id='web-orbit',expires_at=int(time.time())+3600)
            session.add(match);session.flush()
            return {'id':match.id,'fixture':True,'left':f'/fixtures/{fixtures[0]}/index.html','right':f'/fixtures/{fixtures[1]}/index.html',
                'brief':'Collect nine energy cells. Avoid the sentinels.','minimum_seconds':5,
                'notice':'Two internally authored fixtures, not creations evaluated from different AI models. Votes never enter the scientific ranking.'}
    @app.post('/api/v1/arena/votes',status_code=201)
    def arena_vote(payload:VoteInput,request:Request):
        limit(request,'arena-vote',12)
        with db.session() as session:
            match=session.scalar(select(ArenaMatch).where(ArenaMatch.id==payload.match_id).with_for_update())
            if not match or match.visitor_hash!=private_hash(settings.secret,request.state.visitor):raise HTTPException(404,'Match not found')
            if match.expires_at<int(time.time()):raise HTTPException(410,'Match expired')
            if time.time()-datetime.fromisoformat(match.created_at).timestamp()<5:raise HTTPException(400,'Play both sides before voting (at least five seconds)')
            user=request.state.user
            session.add(Vote(match_id=match.id,visitor_hash=match.visitor_hash,user_id=user.id if user else None,choice=payload.choice,fixture=match.fixture))
            session.flush()
            count=session.scalar(select(func.count()).select_from(Vote).where(Vote.fixture.is_(True)))
            return {'accepted':True,'fixture':True,'choice':payload.choice,'left':'Authored '+match.left_fixture+' fixture',
                'right':'Authored '+match.right_fixture+' fixture','demo_votes':count,'ranking_impact':'none'}

    @app.get('/api/v1/account/export')
    def account_export(request:Request):
        user=require(request)
        with db.session() as session:
            obj={'profile':{'email':user.email,'name':user.name,'locale':user.locale,'created_at':user.created_at},
                'comparisons':[{'name':x.name,'models':x.model_ids} for x in session.scalars(select(SavedComparison).where(SavedComparison.user_id==user.id))],
                'following':[x.model_id for x in session.scalars(select(Follow).where(Follow.user_id==user.id))],
                'votes':[{'match':x.match_id,'choice':x.choice,'fixture':x.fixture,'at':x.created_at} for x in session.scalars(select(Vote).where(Vote.user_id==user.id))],
                'notifications':[{'kind':x.kind,'data':x.data,'at':x.created_at} for x in session.scalars(select(Notification).where(Notification.user_id==user.id))]}
        return JSONResponse(obj,headers={'Content-Disposition':'attachment; filename="gamedev-personal-data.json"'})
    @app.post('/api/v1/account/comparisons',status_code=201)
    def save(payload:SaveInput,request:Request):
        user=require(request)
        with db.session() as session:
            if len(set(payload.model_ids))!=len(payload.model_ids) or any(not session.get(Model,i) for i in payload.model_ids):raise ValueError('Invalid model selection')
            count=session.scalar(select(func.count()).select_from(SavedComparison).where(SavedComparison.user_id==user.id))
            if count>=50:raise ValueError('Comparison limit reached')
            record=SavedComparison(user_id=user.id,name=payload.name,model_ids=payload.model_ids);session.add(record);session.flush();return {'id':record.id}
    @app.post('/api/v1/account/follow/{model_id}')
    def follow(model_id:str,request:Request):
        user=require(request)
        with db.session() as session:
            if not session.get(Model,model_id):raise HTTPException(404,'Model not found')
            existing=session.scalar(select(Follow).where(Follow.user_id==user.id,Follow.model_id==model_id))
            if existing:session.delete(existing);return {'following':False}
            session.add(Follow(user_id=user.id,model_id=model_id));return {'following':True,'delivery':'in-app only'}
    @app.post('/api/v1/account/delete')
    def account_delete(payload:PasswordInput,request:Request):
        user=require(request)
        if not verify_password(user.password_hash,payload.password):raise HTTPException(401,'Password confirmation failed')
        with db.session() as session:
            if user.role=='admin' and session.scalar(select(func.count()).select_from(User).where(User.role=='admin',User.active.is_(True)))<=1:
                raise ValueError('Create another administrator before deleting the last administrator')
            session.execute(update(Vote).where(Vote.user_id==user.id).values(user_id=None,visitor_hash='deleted'))
            session.execute(delete(Lead).where(Lead.email==user.email))
            session.delete(session.get(User,user.id))
        response=JSONResponse({'deleted':True,'notice':'Scientific records retain anonymized decisions; billing provider records need a separate legal retention review.'})
        response.delete_cookie('gdb_session');response.delete_cookie('gdb_csrf');response.delete_cookie('gdb_visitor');return response

    @app.get('/api/v1/admin/status')
    def admin_status(request:Request):
        require(request,('admin','reviewer'))
        with db.session() as session:
            return {'runs':data.runs(session,private=True),'queue':dict(session.execute(select(Run.state,func.count()).group_by(Run.state)).all()),
                'workers':[{'id':w.id,'name':w.name,'environment':w.environment,'last_seen_at':w.last_seen_at,'active':w.active} for w in session.scalars(select(Worker))],
                'providers':[{'id':p.id,'name':p.name,'configured':bool(os.getenv(p.key_env))} for p in session.scalars(select(Provider))]}
    @app.post('/api/v1/admin/campaigns/quote')
    def campaign_quote(payload:CampaignInput,request:Request):
        require(request,('admin',))
        with db.session() as session:
            result=quote_campaign(session,payload.configuration_id,payload.suite_id,payload.task_ids,payload.trials)
            return {'upper_bound_microusd':result['upper_bound_microusd'],'calls':len(result['plans'])*result['trials'],
                'fixture':result['config'].fixture,'price':result['price'],'notice':'Conservative estimate, not a billing-provider hard cap or invoice.'}
    @app.post('/api/v1/admin/campaigns',status_code=201)
    def campaign_create(payload:CampaignInput,request:Request):
        user=require(request,('admin',));limit(request,'campaign',10)
        campaign_id=create_campaign(db,settings,user,**payload.model_dump(),idempotency_key=key(request))
        return {'id':campaign_id,'state':'queued','execution':'Requires the separate worker process; this request makes no provider call'}
    @app.post('/api/v1/admin/campaigns/{campaign_id}/cancel')
    def campaign_cancel(campaign_id:str,request:Request):
        cancel_campaign(db,require(request,('admin',)),campaign_id);return {'cancelled':True,'notice':'An already issued provider request may still be billable'}
    @app.post('/api/v1/admin/runs/{run_id}/review')
    def review(run_id:str,payload:ReviewInput,request:Request):
        user=require(request,('admin','reviewer'))
        with db.session() as session:
            for item in session.scalars(select(Artifact).where(Artifact.run_id==run_id)):store.get(item.sha256)
        return review_run(db,user,run_id,**payload.model_dump())
    @app.post('/api/v1/admin/providers/{provider_id}/discover')
    def discover(provider_id:str,request:Request):
        user=require(request,('admin',));limit(request,'provider-discovery',5)
        with db.session() as session:
            provider=session.get(Provider,provider_id)
            if not provider:raise HTTPException(404,'Provider not found')
        try:
            adapter=ProviderAdapter(provider)
            try:catalog=adapter.list_models()
            finally:adapter.close()
        except (ProviderError,ValueError) as exc:raise HTTPException(503,str(exc)) from None
        inserted=0
        with db.session() as session:
            for row in catalog:
                if not session.scalar(select(ModelAnnouncement.id).where(ModelAnnouncement.provider_id==provider.id,ModelAnnouncement.api_id==row['api_id'])):
                    session.add(ModelAnnouncement(provider_id=provider.id,api_id=row['api_id'],source_url=provider.docs_url,metadata_json=row));inserted+=1
            session.add(AuditLog(actor_id=user.id,action='provider.discovered',target=provider.id,data={'announcements':inserted}))
        return {'discovered':len(catalog),'pending_review':inserted,'automatic_paid_campaigns':False}
    @app.post('/api/v1/admin/configurations',status_code=201)
    def add_configuration(payload:ConfigurationInput,request:Request):
        user=require(request,('admin',))
        with db.session() as session:
            version=session.get(ModelVersion,payload.model_version_id)
            if not version:raise ValueError('Unknown model version')
            model=session.get(Model,version.model_id)
            if payload.reasoning!='provider-default' and (model.provider_id!='openai' or payload.reasoning not in version.capabilities.get('reasoning_levels',[])):
                raise ValueError('Unsupported reasoning override for this model')
            config=AgentConfiguration(model_version_id=version.id,harness_id='gdb-standard/1.0.0',name=payload.name,
                reasoning=payload.reasoning,mode='standardized',parameters={'max_output_tokens':payload.max_output_tokens,'time_limit_seconds':90})
            session.add(config);session.flush();session.add(AuditLog(actor_id=user.id,action='configuration.created',target=config.id,data={}))
            return {'id':config.id}
    @app.post('/api/v1/admin/prices',status_code=201)
    def add_price(payload:PriceInput,request:Request):
        user=require(request,('admin',))
        with db.session() as session:
            if not session.get(ModelVersion,payload.model_version_id):raise ValueError('Unknown model version')
            row=PriceHistory(**payload.model_dump());session.add(row);session.flush()
            session.add(AuditLog(actor_id=user.id,action='price.added',target=row.id,data={'source':payload.source_url}));return {'id':row.id}
    @app.post('/api/v1/admin/workers',status_code=201)
    def add_worker(payload:WorkerInput,request:Request):
        user=require(request,('admin',));token=secrets.token_urlsafe(40)
        with db.session() as session:
            worker=Worker(name=payload.name,environment=payload.environment,token_hash=digest(token),capabilities={'private_receipt_upload':True})
            session.add(worker);session.flush();session.add(AuditLog(actor_id=user.id,action='worker.created',target=worker.id,data={}))
            return {'id':worker.id,'token':token,'notice':'Shown once. Store on the dedicated runner, never in frontend code.'}
    @app.post('/api/v1/admin/workers/{worker_id}/revoke')
    def revoke_worker(worker_id:str,request:Request):
        require(request,('admin',))
        with db.session() as session:
            worker=session.get(Worker,worker_id)
            if not worker:raise HTTPException(404,'Worker not found')
            worker.active=False;return {'revoked':True}
    @app.post('/api/v1/runner/evidence',status_code=202)
    async def runner_evidence(request:Request):
        limit(request,'runner',20);header=request.headers.get('Authorization','')
        if not header.startswith('Bearer ') or len(header)>180:raise HTTPException(401,'Runner credential required')
        payload=await request.json()
        if not isinstance(payload,dict) or payload.get('kind')!='roblox-local-runner-receipt':raise ValueError('Invalid runner receipt')
        with db.session() as session:
            worker=session.scalar(select(Worker).where(Worker.token_hash==digest(header[7:]),Worker.active.is_(True),Worker.environment=='roblox'))
            if not worker:raise HTTPException(401,'Invalid runner credential')
            receipt_hash=store.put_json(payload);receipt_id=str(uuid.uuid4());worker.last_seen_at=now()
            session.add(AuditLog(actor_id=None,action='runner.receipt',target=receipt_id,data={'worker_id':worker.id,'sha256':receipt_hash,'published':False}))
        return {'receipt_id':receipt_id,'sha256':receipt_hash,'published':False,'notice':'Private receipt saved. Studio scoring/import and independent review are separate, not automatic.'}
    @app.post('/api/v1/billing/checkout')
    def billing_checkout(request:Request):
        user=require(request);limit(request,'checkout',3)
        try:return checkout(user,settings.origin,key(request))
        except RuntimeError as exc:raise HTTPException(503,str(exc)) from None
    @app.post('/api/v1/billing/webhook')
    async def webhook(request:Request):
        secret=os.getenv('STRIPE_WEBHOOK_SECRET','')
        if not secret:raise HTTPException(503,'Billing webhook not configured')
        raw=await request.body()
        event=verify_signature(raw,request.headers.get('Stripe-Signature',''),secret)
        return process_event(db,event)

    app.mount('/static',StaticFiles(directory=ROOT/'gamedev/web/static'),name='static')
    @app.get('/')
    def root():return RedirectResponse('/en',status_code=307)
    @app.get('/robots.txt')
    def robots():return Response('User-agent: *\nDisallow: /api/\nDisallow: /*/admin\nDisallow: /*/account\nSitemap: '+settings.origin+'/sitemap.xml\n',media_type='text/plain')
    @app.get('/sitemap.xml')
    def sitemap():
        paths=['','leaderboard','roblox','web-games','arena','compare','models','methodology','lab','news','pro','enterprise','partners','contact','about','faq']
        import html
        entries=''.join('<url><loc>'+html.escape(settings.origin+'/'+lang+('/'+path if path else ''))+'</loc></url>' for lang in ('en','fr') for path in paths)
        return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+entries+'</urlset>',media_type='application/xml')

    @app.get('/{lang}',response_class=HTMLResponse)
    @app.get('/{lang}/{page:path}',response_class=HTMLResponse)
    def view(request:Request,lang:str,page:str=''):
        if lang not in locales:raise HTTPException(404,'Page not found')
        page=page.strip('/');section=page.split('/')[0] or 'home';detail=page.split('/',1)[1] if '/' in page else None
        allowed={'home','leaderboard','roblox','web-games','arena','compare','models','methodology','lab','runs','tasks','news','pro','enterprise','partners','contact','about','faq','privacy','terms','legal','login','register','account','admin','api'}
        if section not in allowed:raise HTTPException(404,'Page not found')
        user=request.state.user
        if section in ('account','admin'):
            if not user:return RedirectResponse('/'+lang+'/login',status_code=303)
            if section=='admin' and user.role not in ('admin','reviewer'):raise HTTPException(403,'Private administration')
        private=section=='admin'
        with db.session() as session:
            allmodels=data.models(session);alltasks=data.tasks(session)
            allruns=data.runs(session,private=private)
            context={'models':allmodels,'tasks':alltasks,'runs':allruns,'providers':list(session.scalars(select(Provider))),
                'suites':list(session.scalars(select(Suite))),'model':None,'task':None,'run':None,
                'result_count':session.scalar(select(func.count()).select_from(Run).where(Run.fixture.is_(False),Run.published.is_(True))),
                'fixture_count':session.scalar(select(func.count()).select_from(Run).where(Run.fixture.is_(True),Run.published.is_(True))),
                'posts':list(session.scalars(select(ResearchPost).where(ResearchPost.published.is_(True)).order_by(ResearchPost.created_at.desc())))}
            if section=='models' and detail:
                context['model']=next((m for m in allmodels if m['id']==detail),None)
                if not context['model']:raise HTTPException(404,'Model not found')
            if section=='tasks' and detail:
                context['task']=next((t for t in alltasks if t['id']==detail),None)
                if not context['task']:raise HTTPException(404,'Task not found')
            if section=='runs' and detail:
                context['run']=data.run_detail(session,detail,authorize(user,('admin','reviewer')))
                if not context['run']:raise HTTPException(404,'Run not found')
            if section=='leaderboard':context['board']=data.leaderboard(session,request.query_params.get('environment','web'))
            if private:
                context.update({'campaigns':list(session.scalars(select(Campaign).order_by(Campaign.created_at.desc()).limit(100))),
                    'configurations':list(session.scalars(select(AgentConfiguration))),
                    'leads':list(session.scalars(select(Lead).order_by(Lead.created_at.desc()).limit(50))) if user.role=='admin' else [],
                    'workers':list(session.scalars(select(Worker))),
                    'integrations':[{'name':p.name,'id':p.id,'configured':bool(os.getenv(p.key_env))} for p in session.scalars(select(Provider))],
                    'receipts':list(session.scalars(select(AuditLog).where(AuditLog.action=='runner.receipt').limit(50))),
                    'announcements':list(session.scalars(select(ModelAnnouncement).where(ModelAnnouncement.reviewed.is_(False)).limit(100)))})
            if section=='account':
                context.update({'saved':list(session.scalars(select(SavedComparison).where(SavedComparison.user_id==user.id))),
                    'follows':list(session.scalars(select(Follow).where(Follow.user_id==user.id))),
                    'notifications':list(session.scalars(select(Notification).where(Notification.user_id==user.id).limit(50)))})
        title=locales[lang].get(section,section)
        def t(name):return locales[lang].get(name,locales['en'].get(name,name))
        def loc(value):return value.get(lang,value.get('en','')) if isinstance(value,dict) else value
        def number(value):return f'{value:,}'.replace(',','\u202f') if lang=='fr' else f'{value:,}'
        def money(value,digits=2):
            rendered=f'{float(value):,.{digits}f}'
            return rendered.replace(',', '\u202f').replace('.', ',')+'\u00a0$US' if lang=='fr' else '$'+rendered
        def date(value):
            if not value:return t('not_verified')
            try:
                d=datetime.fromisoformat(value.replace('Z','+00:00'))
                return d.strftime('%d/%m/%Y' if lang=='fr' else '%b %d, %Y')
            except ValueError:return value
        rendered=templates.get_template('shell.html').render(**context,request=request,lang=lang,section=section,detail=detail,page=page,
            title=title,t=t,loc=loc,num=number,date=date,money=money,user=user,settings=settings,csrf=request.state.csrf,checked_at=CHECKED,
            site_origin=settings.origin,static_mode=False,billing_configured=bool(os.getenv('STRIPE_SECRET_KEY') and os.getenv('STRIPE_PRICE_ID')),
            language_path='/'+('fr' if lang=='en' else 'en')+('/'+page if page else ''),
            selected_ids=request.query_params.get('ids','').split(','),search_query=request.query_params.get('q',''))
        return HTMLResponse(rendered,headers={'Cache-Control':'no-store','Content-Language':lang})
    return app
