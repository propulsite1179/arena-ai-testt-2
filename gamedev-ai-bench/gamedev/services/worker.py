"""Single-attempt execution, immutable evidence, and explicit cost uncertainty."""
from decimal import Decimal
from pathlib import Path
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
import time
from sqlalchemy import select, update
from gamedev.config import ROOT
from gamedev.database import Run, RunEvent, Campaign, Provider, TaskVersion, AssertionResult, Artifact, now
from gamedev.core.artifacts import ArtifactStore, validate_project
from gamedev.core.protocol import Price, canonical_hash, technical_score
from gamedev.adapters.providers import ProviderAdapter, ProviderError
from gamedev.security import digest, redact
from gamedev.services.campaigns import claim_run, move_run
from gamedev.services.evaluator import evaluate


def sandbox_command(project: Path, output: Path) -> list[str]:
    image=os.getenv('SANDBOX_IMAGE','gamedev-web-sandbox:0.1.0')
    if not image or any(c.isspace() for c in image) or image.startswith('-'):
        raise ValueError('Invalid sandbox image')
    return ['docker','run','--rm','--network=none','--read-only','--cap-drop=ALL',
            '--security-opt=no-new-privileges','--pids-limit=128','--memory=768m','--cpus=1',
            '--user=1000:1000','--tmpfs=/tmp:rw,noexec,nosuid,size=256m',
            '--mount',f'type=bind,src={project.resolve()},dst=/project,readonly',
            '--mount',f'type=bind,src={output.resolve()},dst=/output',image]


def require_sandbox() -> None:
    if not shutil.which('docker'):
        raise RuntimeError('sandbox_unavailable: paid generation disabled without Docker isolation')
    subprocess.run(['docker','image','inspect',os.getenv('SANDBOX_IMAGE','gamedev-web-sandbox:0.1.0')],
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=10)


def settle(session, run, estimate: int | None, known_no_charge: bool=False) -> None:
    if session.scalar(select(RunEvent.id).where(RunEvent.run_id==run.id,RunEvent.kind=='budget_settled')):
        return
    campaign=session.scalar(select(Campaign).where(Campaign.id==run.campaign_id).with_for_update())
    bound=run.frozen_config['budget_max_microusd']
    charge=0 if known_no_charge else bound if estimate is None else min(bound,estimate)
    campaign.reserved_microusd-=bound;campaign.spent_microusd+=charge
    session.add(RunEvent(run_id=run.id,kind='budget_settled',data={
        'accounted_microusd':charge,'estimate_microusd':estimate,'kind':'estimate' if estimate is not None else 'reserved_upper_bound_not_invoice'},public=True))
    if estimate is not None and estimate>bound:
        campaign.state='budget_anomaly'
        for pending in session.scalars(select(Run).where(Run.campaign_id==campaign.id,Run.state=='pending')):
            campaign.reserved_microusd-=pending.frozen_config['budget_max_microusd']
            pending.state='cancelled';pending.error_code='budget_anomaly';pending.finished_at=now()


def persist_artifacts(session,store,run,files):
    for name,data in files.items():
        value=data if isinstance(data,bytes) else data.encode('utf-8')
        session.add(Artifact(run_id=run.id,name=name,sha256=store.put(value),size_bytes=len(value),
                             media_type=mimetypes.guess_type(name)[0] or 'application/octet-stream'))


def execute_one(db,settings,fixture_only=False) -> str | None:
    claimed=claim_run(db,fixture_only=fixture_only)
    if not claimed:
        return None
    run_id,lease=claimed;started=time.monotonic();generation=None;estimate=None;api_started=False
    store=ArtifactStore(settings.data_dir/'artifacts')
    try:
        with db.session() as session:
            run=session.get(Run,run_id);frozen=dict(run.frozen_config);fixture=run.fixture
            spec=session.get(TaskVersion,run.task_version_id).specification
            assert canonical_hash(frozen)==run.config_hash,'Frozen configuration tampered'
            provider=session.get(Provider,frozen['provider_id']) if frozen['provider_id'] else None
        if not fixture:
            if not settings.paid_runs:
                raise RuntimeError('paid_runs_disabled')
            require_sandbox()  # Before making any paid call.
        move_run(db,run_id,lease,'running')
        invalid_output=None;raw_response=None
        if fixture:
            folder=ROOT/'packages/test-fixtures/games/orbital'
            generated={p.name:p.read_text() for p in folder.iterdir() if p.is_file()}
            estimate=0
        else:
            api_started=True
            adapter=ProviderAdapter(provider)
            try:
                generation=adapter.generate(model=frozen['model_api_id'],system=frozen['system_prompt'],prompt=frozen['user_prompt'],
                                            max_output_tokens=frozen['max_output_tokens'],reasoning=frozen['reasoning'])
            finally:
                adapter.close()
            raw_response={'text':generation.text,'model_reported':generation.model_reported,'response_id':generation.response_id,
                          'usage':generation.usage,'finish_reason':generation.stop_reason}
            p=frozen['price'];price=Price(Decimal(p['input']),Decimal(p['output']),Decimal(p['cached']) if p['cached'] else None)
            if generation.input_tokens is not None and generation.output_tokens is not None:
                estimate=price.estimate_microusd(generation.input_tokens,generation.output_tokens,generation.cached_tokens or 0)
            try:
                generated=validate_project(json.loads(generation.text)['files'])
            except (ValueError,TypeError,KeyError):
                generated={};invalid_output='Model did not produce a valid bounded project JSON'
        move_run(db,run_id,lease,'evaluating')
        with tempfile.TemporaryDirectory(prefix='gdb-run-',dir=settings.data_dir) as temporary:
            temp=Path(temporary);project=temp/'project';output=temp/'output';project.mkdir();output.mkdir()
            for name,content in generated.items():
                target=project/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content,encoding='utf-8')
            if invalid_output:
                report={'assertions':[{'id':check,'outcome':'failed','weight':1,'blocking':check in ('boot','start','runtime'),
                                      'observed':{'reason':invalid_output}} for check in spec['checks']],
                        'metrics':{},'limitations':['No browser run possible: invalid model output.']}
                (output/'evaluation.json').write_text(json.dumps(report))
            elif fixture:
                report=evaluate(project,output,trusted_fixture=True)
            else:
                # UID 1000 is permitted only on this temporary output; source is read-only.
                output.chmod(0o777);temp.chmod(0o755);project.chmod(0o755)
                subprocess.run(sandbox_command(project,output),check=True,timeout=60,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                evidence=output/'evaluation.json'
                if evidence.is_symlink() or evidence.stat().st_size>500_000:
                    raise ValueError('Invalid sandbox evidence')
                report=json.loads(evidence.read_text())
            evidence_files={'frozen-config.json':json.dumps(frozen,indent=2),'project.json':json.dumps({'files':generated},ensure_ascii=False)}
            if raw_response:
                evidence_files['provider-response.json']=json.dumps(raw_response,ensure_ascii=False)
            for path in output.iterdir():
                if path.name in ('evaluation.json','desktop.png','mobile.png') and path.is_file() and not path.is_symlink() and path.stat().st_size<=8_000_000:
                    evidence_files[path.name]=path.read_bytes()
            with db.session() as session:
                run=session.scalar(select(Run).where(Run.id==run_id).with_for_update())
                if run.state!='evaluating' or run.lease_token_hash!=digest(lease):
                    raise PermissionError('Run cancelled or lease replaced; late result rejected')
                assertions=report['assertions']
                if set(a['id'] for a in assertions)!=set(spec['checks']) or len(assertions)!=len(spec['checks']):
                    raise ValueError('Evaluator returned mismatching assertion identifiers')
                run.score=technical_score(assertions)
                for a in assertions:
                    session.add(AssertionResult(run_id=run.id,assertion_id=a['id'],outcome=a['outcome'],weight=a['weight'],blocking=a['blocking'],observed=a.get('observed',{})))
                if generation:
                    run.input_tokens=generation.input_tokens;run.output_tokens=generation.output_tokens;run.cached_tokens=generation.cached_tokens
                run.estimated_cost_microusd=estimate;run.duration_ms=round((time.monotonic()-started)*1000)
                persist_artifacts(session,store,run,evidence_files)
                settle(session,run,estimate)
                run.state='awaiting-review';run.finished_at=now();run.lease_token_hash=None;run.lease_expires_at=None
                session.add(RunEvent(run_id=run.id,kind='awaiting-review',data={'fixture':fixture,'assertion_count':len(assertions)},public=True))
                campaign=session.get(Campaign,run.campaign_id)
                if campaign.state!='budget_anomaly':
                    campaign.state='awaiting-review'
    except Exception as exc:
        with db.session() as session:
            run=session.scalar(select(Run).where(Run.id==run_id).with_for_update())
            if run.state not in ('cancelled','completed','failed'):
                settle(session,run,estimate,known_no_charge=not api_started)
                run.state='failed';run.finished_at=now();run.lease_token_hash=None;run.error_code=(exc.code if isinstance(exc,ProviderError) else type(exc).__name__)[:100]
                run.duration_ms=round((time.monotonic()-started)*1000)
                session.add(RunEvent(run_id=run_id,kind='failed',data={'error_code':run.error_code,'message':redact(str(exc)),
                    'automatic_retry':False,'provider_outcome_may_be_unknown':api_started and generation is None},public=False))
                session.get(Campaign,run.campaign_id).state='needs-attention'
    return run_id


def expire_leases(db) -> int:
    count=0
    with db.session() as session:
        for run in session.scalars(select(Run).where(Run.state.in_(['preparing','running','evaluating']),Run.lease_expires_at<int(time.time())).with_for_update(skip_locked=True)):
            settle(session,run,None);run.state='failed';run.error_code='lease_expired_unknown_outcome';run.finished_at=now();run.lease_token_hash=None
            session.add(RunEvent(run_id=run.id,kind='failed',data={'reason':'Lease expired; no automatic paid retry'},public=True));count+=1
    return count
