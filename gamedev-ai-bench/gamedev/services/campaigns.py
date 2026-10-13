"""Budgeted, versioned campaigns and a persistent lease queue."""
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from time import time
import json
import platform
import secrets
from sqlalchemy import select, update, func
from gamedev.database import (
    Campaign, AgentConfiguration, Model, ModelVersion, Provider, PriceHistory, Suite, Task,
    TaskVersion, Run, RunEvent, AssertionResult, Artifact, HumanReview, ScoreSnapshot,
    AuditLog, IdempotencyRecord, Follow, Notification, now,
)
from gamedev.core.protocol import (
    Price, canonical_hash, validate_budget, transition, technical_score, HARNESS_VERSION,
)
from gamedev.security import digest, redact

SYSTEM_PROMPT = 'Build the requested original browser game. Return ONLY one JSON object {"files":{"index.html":"...","game.js":"...","style.css":"..."}}. Use local files only, no network, no imports from CDNs, no dependency installation, no cookies or storage. Do not identify the model or vendor. Do not include markdown fences.'
CONTRACT = '\nTest contract: render one canvas; provide visible buttons [data-testid="start"], [data-testid="pause"] and [data-testid="restart"]. Provide numeric text [data-testid="score"], a [data-testid="state"] label (ready/running/paused/finished), and a [data-testid="player"] element whose data-x attribute tracks the real player x position. A visible [data-testid="touch-right"] button must move the player. Keyboard ArrowRight must move after start. Restart resets the score. All observations must mirror actual game state; no test-only behavior.'


def quote_campaign(session, configuration_id: str, suite_id: str, task_ids: list[str], trials: int) -> dict:
    config = session.get(AgentConfiguration, configuration_id)
    suite = session.get(Suite, suite_id)
    if not config or not suite or not 1 <= trials <= 10 or not task_ids or len(task_ids) > 30 or len(set(task_ids)) != len(task_ids):
        raise ValueError('Invalid configuration, suite, tasks or trial count')
    if config.mode == 'agentic':
        raise ValueError('Agentic solutions require a separately qualified harness; direct API campaigns cannot impersonate agents')
    versions = []
    for task_id in task_ids:
        task = session.get(Task, task_id)
        if not task or task.suite_id != suite.id:
            raise ValueError('Every task must belong to the selected suite')
        version = session.scalar(select(TaskVersion).where(TaskVersion.task_id == task_id).order_by(TaskVersion.created_at.desc()))
        if not config.fixture and task_id != 'web-orbit':
            raise ValueError('This task is not qualified for paid publication. Complete its task-specific assertions before enabling it.')
        versions.append(version)
    if config.fixture and (suite.environment != 'web' or task_ids != ['web-orbit']):
        raise ValueError('The reference fixture qualifies only the web-orbit harness task')
    if not config.fixture and suite.environment != 'web':
        raise ValueError('Paid Studio campaign orchestration is not qualified yet. Use the consent-based local runner for reviewed plans.')
    model_version = session.get(ModelVersion, config.model_version_id) if config.model_version_id else None
    provider = session.get(Provider, session.get(Model, model_version.model_id).provider_id) if model_version else None
    price_row = session.scalar(select(PriceHistory).where(PriceHistory.model_version_id == model_version.id).order_by(PriceHistory.created_at.desc())) if model_version else None
    max_output = int(config.parameters.get('max_output_tokens',4096))
    if not 128 <= max_output <= 32768:
        raise ValueError('Configuration output token limit must be between 128 and 32768')
    price_data = None
    if not config.fixture:
        if not price_row:
            raise ValueError('A sourced, dated price is required before a paid campaign')
        price_data = {'input':price_row.input_per_million,'output':price_row.output_per_million,
                      'cached':price_row.cached_per_million,'source':price_row.source_url,'checked_at':price_row.checked_at}
        price = Price(Decimal(price_data['input']), Decimal(price_data['output']))
    plans = []
    for version in versions:
        prompt = version.specification['brief']['en'] + CONTRACT
        # Conservative byte-token bound plus overhead; reserve 20% headroom. No tools.
        input_upper = len((SYSTEM_PROMPT+prompt).encode('utf-8'))+4096
        bound = 0 if config.fixture else int((price.estimate_microusd(input_upper,max_output)*12+9)//10)
        plans.append({'version':version,'prompt':prompt,'bound_microusd':bound})
    return {'config':config,'suite':suite,'provider':provider,'model_version':model_version,
            'price':price_data,'plans':plans,'trials':trials,'max_output_tokens':max_output,
            'upper_bound_microusd':sum(p['bound_microusd'] for p in plans)*trials,
            'task_set_hash':canonical_hash(sorted(v.spec_hash for v in versions))}


def create_campaign(db, settings, actor, *, name: str, configuration_id: str, suite_id: str,
                    task_ids: list[str], trials: int, authorized_microusd: int,
                    paid_authorized: bool, idempotency_key: str) -> str:
    if actor.role != 'admin':
        raise PermissionError('Administrator required')
    request_hash = canonical_hash({'name':name,'configuration':configuration_id,'suite':suite_id,
                                  'tasks':task_ids,'trials':trials,'budget':authorized_microusd,'paid':paid_authorized})
    key = actor.id+':'+idempotency_key
    with db.session() as session:
        existing = session.get(IdempotencyRecord, key)
        if existing:
            if existing.request_hash != request_hash:
                raise ValueError('Idempotency key already used for a different request')
            return existing.resource_id
        quote = quote_campaign(session, configuration_id,suite_id,task_ids,trials)
        fixture = quote['config'].fixture
        if not fixture:
            if not settings.paid_runs or not paid_authorized:
                raise ValueError('Paid runs require both server enablement and explicit administrator authorization')
            import os
            if not os.getenv(quote['provider'].key_env):
                raise ValueError('Provider key is not configured')
        validate_budget(authorized_microusd,0,0,quote['upper_bound_microusd'])
        campaign = Campaign(name=name, suite_id=suite_id,configuration_id=configuration_id,created_by=actor.id,
                            fixture=fixture,authorized_microusd=authorized_microusd,
                            reserved_microusd=quote['upper_bound_microusd'],
                            approval={'explicit_paid_authorization':paid_authorized,'actor':actor.id,
                                      'approved_at':now(),'quote_microusd':quote['upper_bound_microusd']})
        session.add(campaign)
        session.flush()
        for plan in quote['plans']:
            for trial in range(1,trials+1):
                frozen = {
                    'suite_version':quote['suite'].version,'protocol_version':quote['suite'].protocol_version,
                    'environment':quote['suite'].environment,'mode':quote['config'].mode,
                    'harness_version':quote['config'].harness_id,'task_set_hash':quote['task_set_hash'],
                    'max_output_tokens':quote['max_output_tokens'],'time_limit_seconds':90,
                    'tools_hash':canonical_hash([]),'budget_policy':'one-shot-conservative-reserve/1',
                    'reasoning':quote['config'].reasoning,'parameters':quote['config'].parameters,
                    'model_api_id':quote['model_version'].api_id if quote['model_version'] else None,
                    'provider_id':quote['provider'].id if quote['provider'] else None,
                    'price':quote['price'],'budget_max_microusd':plan['bound_microusd'],
                    'system_prompt':SYSTEM_PROMPT,'user_prompt':plan['prompt'],
                    'task_version_hash':plan['version'].spec_hash,'python_version':platform.python_version(),
                    'provider_seed':None,'seed_limitation':'No seed sent; infrastructure may be nondeterministic',
                    'fixture':fixture,'trial':trial,
                }
                run = Run(campaign_id=campaign.id,task_version_id=plan['version'].id,environment=quote['suite'].environment,
                          trial=trial,fixture=fixture,frozen_config=frozen,config_hash=canonical_hash(frozen))
                session.add(run)
                session.flush()
                session.add(RunEvent(run_id=run.id,kind='queued',data={'configuration_hash':run.config_hash},public=True))
        session.add(IdempotencyRecord(key=key,actor_id=actor.id,request_hash=request_hash,resource_id=campaign.id))
        session.add(AuditLog(actor_id=actor.id,action='campaign.created',target=campaign.id,data={'fixture':fixture,'budget':authorized_microusd}))
        return campaign.id


def claim_run(db, environment: str = 'web', fixture_only: bool = False) -> tuple[str, str] | None:
    """Atomic compare-and-set + row locking, no paid automatic retry after failure."""
    with db.session() as session:
        query = select(Run).where(Run.state == 'pending',Run.environment == environment)
        if fixture_only:
            query = query.where(Run.fixture.is_(True))
        run = session.scalar(query.order_by(Run.created_at,Run.id).with_for_update(skip_locked=True).limit(1))
        if not run:
            return None
        token = secrets.token_urlsafe(32)
        changed = session.execute(update(Run).where(Run.id==run.id,Run.state=='pending').values(
            state='preparing',lease_token_hash=digest(token),lease_expires_at=int(time())+180,started_at=now()))
        if changed.rowcount != 1:
            return None
        session.add(RunEvent(run_id=run.id,kind='preparing',data={'lease_seconds':180},public=True))
        session.execute(update(Campaign).where(Campaign.id==run.campaign_id).values(state='running'))
        return run.id, token


def move_run(db, run_id: str, lease: str, target: str, data: dict | None = None) -> None:
    with db.session() as session:
        run = session.get(Run,run_id)
        if not run or run.lease_token_hash != digest(lease) or (run.lease_expires_at or 0) < time():
            raise PermissionError('Missing or expired worker lease')
        old = run.state
        new = transition(old,target)
        result = session.execute(update(Run).where(Run.id==run.id,Run.state==old,Run.lease_token_hash==digest(lease)).values(state=new))
        if result.rowcount != 1:
            raise ValueError('Run changed concurrently')
        session.add(RunEvent(run_id=run.id,kind=target,data=redact(data or {}),public=True))


def cancel_campaign(db, actor, campaign_id: str) -> None:
    if actor.role != 'admin':
        raise PermissionError('Administrator required')
    with db.session() as session:
        campaign = session.get(Campaign,campaign_id)
        if not campaign:
            raise ValueError('Campaign not found')
        for run in session.scalars(select(Run).where(Run.campaign_id==campaign.id)):
            if run.state in ('completed','failed','cancelled'):
                continue
            reserve = run.frozen_config['budget_max_microusd']
            settled = session.scalar(select(RunEvent.id).where(RunEvent.run_id==run.id,RunEvent.kind=='budget_settled'))
            if settled:
                reserve = 0
            if run.state == 'pending':
                campaign.reserved_microusd -= reserve
            else:
                # An in-flight provider request may already be billable.
                campaign.reserved_microusd -= reserve
                campaign.spent_microusd += reserve
            run.state = 'cancelled'
            run.lease_token_hash = None
            run.finished_at = now()
            session.add(RunEvent(run_id=run.id,kind='cancelled',data={'in_flight_cost_may_be_unknown':True},public=True))
        campaign.state='cancelled'
        session.add(AuditLog(actor_id=actor.id,action='campaign.cancelled',target=campaign.id,data={}))


def review_run(db, actor, run_id: str, *, verdict: str, notes: str, rubric: dict,
               conflict_of_interest: bool = False) -> dict:
    if actor.role not in ('reviewer','admin'):
        raise PermissionError('Independent reviewer required')
    with db.session() as session:
        run = session.scalar(select(Run).where(Run.id==run_id).with_for_update())
        if not run or run.state != 'awaiting-review':
            raise ValueError('Only evaluated runs can be reviewed')
        campaign = session.get(Campaign,run.campaign_id)
        if not run.fixture and actor.id == campaign.created_by:
            raise PermissionError('Campaign creator cannot independently validate their own result')
        if conflict_of_interest:
            raise ValueError('A conflicted reviewer cannot publish a result')
        if session.scalar(select(HumanReview.id).where(HumanReview.run_id==run_id,HumanReview.reviewer_id==actor.id)):
            raise ValueError('Reviewer has already submitted a decision')
        required_rubric = ('artifacts_inspected','brief_verified','controls_verified','restart_verified','score_verified')
        if verdict == 'approve' and not all(rubric.get(key) is True for key in required_rubric):
            raise ValueError('Publication requires an explicit artifact and gameplay review rubric')
        if verdict not in ('approve','reject') or len(notes.strip()) < 12:
            raise ValueError('A reasoned approve/reject decision is required')
        assertions = list(session.scalars(select(AssertionResult).where(AssertionResult.run_id==run_id)))
        computed = technical_score([{'id':a.assertion_id,'outcome':a.outcome,'weight':a.weight,'blocking':a.blocking} for a in assertions])
        version = session.get(TaskVersion,run.task_version_id)
        if set(a.assertion_id for a in assertions) != set(version.specification['checks']):
            raise ValueError('Result assertions do not match the frozen task contract')
        if not computed['complete'] and verdict=='approve':
            raise ValueError('Unexecuted checks cannot be published as a complete evaluation')
        session.add(HumanReview(run_id=run.id,reviewer_id=actor.id,verdict=verdict,notes=notes,rubric=rubric))
        session.flush()
        if verdict == 'reject':
            run.state='failed'
            run.error_code='review_rejected'
            campaign.state='needs_attention'
            return {'published':False,'state':run.state}
        approved = session.scalar(select(func.count()).select_from(HumanReview).where(HumanReview.run_id==run.id,HumanReview.verdict=='approve'))
        required = 1 if run.fixture else 2
        if approved < required:
            return {'published':False,'state':'awaiting-review','approvals':approved,'required':required}
        artifacts = list(session.scalars(select(Artifact).where(Artifact.run_id==run.id)))
        if not artifacts:
            raise ValueError('Publication requires preserved evidence')
        snapshot = {'run_id':run.id,'config_hash':run.config_hash,'task_hash':version.spec_hash,
                    'score':computed,'artifacts':{a.name:a.sha256 for a in artifacts},
                    'fixture':run.fixture,'review_count':approved,'cost_kind':'estimate_not_invoice',
                    'cost_microusd':run.estimated_cost_microusd,'published_at':now()}
        session.add(ScoreSnapshot(run_id=run.id,protocol_version=run.frozen_config['protocol_version'],
                                  snapshot=snapshot,sha256=canonical_hash(snapshot)))
        run.state='completed'; run.published=True; run.score=computed
        for artifact in artifacts:
            # Never expose private prompts or provider responses, or private tasks.
            artifact.public = version.visibility=='public' and artifact.name not in ('provider-response.json','frozen-config.json')
        session.add(AuditLog(actor_id=actor.id,action='run.published',target=run.id,data={'snapshot_hash':canonical_hash(snapshot)}))
        session.flush()
        incomplete = session.scalar(select(func.count()).select_from(Run).where(Run.campaign_id==campaign.id,Run.state!='completed'))
        if not incomplete:
            campaign.state='published'
            configuration=session.get(AgentConfiguration,campaign.configuration_id)
            mv=session.get(ModelVersion,configuration.model_version_id) if configuration.model_version_id else None
            if mv and not run.fixture:
                mv.status='evaluated'
                for follow in session.scalars(select(Follow).where(Follow.model_id==mv.model_id)):
                    session.add(Notification(user_id=follow.user_id,kind='model_evaluated',data={'model_id':mv.model_id,'campaign_id':campaign.id}))
        return {'published':True,'state':'completed','fixture':run.fixture,'campaign_state':campaign.state}
