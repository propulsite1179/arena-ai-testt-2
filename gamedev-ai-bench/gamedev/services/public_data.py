"""Public projections exclude private tasks, raw prompts, fixtures from AI rankings."""
from collections import defaultdict
from sqlalchemy import select,func
from gamedev.database import Model,ModelVersion,Provider,PriceHistory,AgentConfiguration,Suite,Task,TaskVersion,Run,Campaign,Artifact,AssertionResult,RunEvent,ScoreSnapshot
from gamedev.core.statistics import task_bootstrap,pass_at_k,wilson,summary
from gamedev.core.protocol import canonical_hash


def models(session):
    result=[]
    for model in session.scalars(select(Model).order_by(Model.provider_id,Model.name)):
        provider=session.get(Provider,model.provider_id)
        version=session.scalar(select(ModelVersion).where(ModelVersion.model_id==model.id).order_by(ModelVersion.created_at.desc()))
        price=session.scalar(select(PriceHistory).where(PriceHistory.model_version_id==version.id).order_by(PriceHistory.created_at.desc()))
        configurations=list(session.scalars(select(AgentConfiguration).where(AgentConfiguration.model_version_id==version.id)))
        result.append({'id':model.id,'name':model.name,'provider':provider.name,'provider_id':provider.id,'description':model.description,
            'api_id':version.api_id,'version_id':version.id,'status':version.status,'availability':version.availability,
            'capabilities':version.capabilities,'source':version.source_url,'checked_at':version.source_checked_at,'release_date':version.release_date,
            'alias':version.alias,'price':{'input':price.input_per_million,'output':price.output_per_million,'cached':price.cached_per_million,
                'source':price.source_url,'checked_at':price.checked_at,'kind':'provider_list_price_not_invoice'} if price else None,
            'configurations':[{'id':c.id,'name':c.name,'mode':c.mode,'reasoning':c.reasoning,'harness':c.harness_id,'parameters':c.parameters} for c in configurations]})
    return result


def tasks(session,environment=None):
    result=[]
    for task in session.scalars(select(Task).order_by(Task.id)):
        suite=session.get(Suite,task.suite_id)
        if environment and suite.environment!=environment:continue
        version=session.scalar(select(TaskVersion).where(TaskVersion.task_id==task.id,TaskVersion.visibility=='public').order_by(TaskVersion.created_at.desc()))
        if not version:continue
        result.append({'id':task.id,'title':task.title,'suite_id':suite.id,'environment':suite.environment,'category':task.category,
            'difficulty':task.difficulty,'version':version.version,'version_id':version.id,'sha256':version.spec_hash,
            'protocol':suite.protocol_version,'specification':version.specification,
            'automation':'smoke_qualified' if task.id=='web-orbit' else 'draft_requires_qualification'})
    return result


def runs(session,*,private=False,fixture=None,limit=100):
    query=select(Run).order_by(Run.created_at.desc()).limit(min(limit,200))
    if not private:query=query.where(Run.published.is_(True))
    if fixture is not None:query=query.where(Run.fixture==fixture)
    result=[]
    for run in session.scalars(query):
        version=session.get(TaskVersion,run.task_version_id)
        if not private and version.visibility!='public':continue
        task=session.get(Task,version.task_id);campaign=session.get(Campaign,run.campaign_id)
        config=session.get(AgentConfiguration,campaign.configuration_id)
        result.append({'id':run.id,'task_id':task.id,'title':task.title,'campaign_id':campaign.id,'campaign':campaign.name,
            'configuration':config.name,'state':run.state,'fixture':run.fixture,'environment':run.environment,'created_at':run.created_at,
            'duration_ms':run.duration_ms,'cost_microusd':run.estimated_cost_microusd,'cost_kind':'estimate_not_invoice',
            'score':run.score,'config_hash':run.config_hash,'published':run.published})
    return result


def run_detail(session,run_id,private=False):
    run=session.get(Run,run_id)
    if not run or (not private and not run.published):return None
    version=session.get(TaskVersion,run.task_version_id)
    if not private and version.visibility!='public':return None
    task=session.get(Task,version.task_id)
    artifacts=list(session.scalars(select(Artifact).where(Artifact.run_id==run.id)))
    events=list(session.scalars(select(RunEvent).where(RunEvent.run_id==run.id).order_by(RunEvent.created_at,RunEvent.id)))
    assertions=list(session.scalars(select(AssertionResult).where(AssertionResult.run_id==run.id)))
    snapshots=list(session.scalars(select(ScoreSnapshot).where(ScoreSnapshot.run_id==run.id)))
    frozen=run.frozen_config if private else {k:v for k,v in run.frozen_config.items() if k not in ('system_prompt','user_prompt')}
    return {'id':run.id,'title':task.title,'task_id':task.id,'task_hash':version.spec_hash,'config_hash':run.config_hash,
        'state':run.state,'fixture':run.fixture,'environment':run.environment,'created_at':run.created_at,'finished_at':run.finished_at,
        'duration_ms':run.duration_ms,'input_tokens':run.input_tokens,'output_tokens':run.output_tokens,'cached_tokens':run.cached_tokens,
        'estimated_cost_microusd':run.estimated_cost_microusd,'observed_cost_microusd':run.observed_cost_microusd,
        'score':run.score,'configuration':frozen,'error_code':run.error_code if private else None,
        'artifacts':[{'id':a.id,'name':a.name,'sha256':a.sha256,'bytes':a.size_bytes,'type':a.media_type} for a in artifacts if private or a.public],
        'events':[{'kind':e.kind,'at':e.created_at,'data':e.data} for e in events if private or e.public],
        'assertions':[{'id':a.assertion_id,'outcome':a.outcome,'blocking':a.blocking,'weight':a.weight,'observed':a.observed} for a in assertions],
        'snapshots':[{'id':s.id,'sha256':s.sha256,'data':s.snapshot} for s in snapshots]}


COHORT_FIELDS=('suite_version','protocol_version','environment','mode','harness_version','task_set_hash','max_output_tokens','time_limit_seconds','tools_hash','budget_policy')

def leaderboard(session,environment='web'):
    grouped=defaultdict(list)
    query=select(Run).join(Campaign).where(Run.fixture.is_(False),Run.published.is_(True),Run.environment==environment,Campaign.state=='published')
    for run in session.scalars(query):
        version=session.get(TaskVersion,run.task_version_id)
        if version.visibility!='public':continue
        campaign=session.get(Campaign,run.campaign_id)
        cohort=canonical_hash({k:run.frozen_config.get(k) for k in COHORT_FIELDS})[:16]
        grouped[(cohort,campaign.configuration_id)].append((run,version.task_id))
    rows=[]
    for (cohort,configuration_id),items in grouped.items():
        configuration=session.get(AgentConfiguration,configuration_id)
        version=session.get(ModelVersion,configuration.model_version_id)
        model=session.get(Model,version.model_id)
        per_task=defaultdict(list);passed=0;estimates=[];latencies=[]
        for run,task_id in items:
            if run.score.get('score') is None:continue
            per_task[task_id].append(run.score['score']);passed+=int(run.score.get('passed',False))
            if run.estimated_cost_microusd is not None:estimates.append(run.estimated_cost_microusd)
            if run.duration_ms is not None:latencies.append(run.duration_ms)
        stats=task_bootstrap(dict(per_task))
        rows.append({'cohort':cohort,'configuration_id':configuration_id,'model_id':model.id,'name':model.name,'mode':configuration.mode,
            'reasoning':configuration.reasoning,'harness':configuration.harness_id,'api_id':version.api_id,
            'score':stats,'successes':passed,'trials':len(items),'pass_at_1':passed/len(items) if items else None,
            'cost_per_success_microusd':sum(estimates)/passed if passed and len(estimates)==len(items) else None,
            'latency_ms':summary(latencies),'published_run_ids':[r.id for r,_ in items]})
    rows.sort(key=lambda r:(r['cohort'],-(r['score'].get('mean') or 0)))
    return {'environment':environment,'rows':rows,'ranked':False,'reason':'Scores are descriptive within identical cohorts; rank uncertainty is not implemented.',
            'fixtures_excluded':True,'minimum_distinct_tasks_for_interval':5}
