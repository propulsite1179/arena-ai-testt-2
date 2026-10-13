"""Independently re-authored regression coverage after archive-tail recovery."""
from decimal import Decimal
from math import comb
import pytest
from gamedev.core.statistics import pass_at_k, wilson, task_bootstrap, paired_difference, bradley_terry, summary
from gamedev.core.protocol import STATES, transition, canonical_hash, technical_score, compare_configurations, Price, validate_budget
from gamedev.core.artifacts import ArtifactStore, safe_relative, validate_project

@pytest.mark.parametrize('n,c,k', [(0,0,1),(1,0,1),(1,1,1),(5,2,1),(5,2,2),(5,2,4),(10,1,3),(10,8,2),(10,10,10)])
def test_pass_at_k_combinatorial(n,c,k):
    expected=None if n<k else 1-(comb(n-c,k) if n-c>=k else 0)/comb(n,k)
    assert pass_at_k(n,c,k)==pytest.approx(expected) if expected is not None else pass_at_k(n,c,k) is None

@pytest.mark.parametrize('args', [(2,3,1),(-1,0,1),(1,1,0),(True,1,1),(5,2,True),(1.5,1,1)])
def test_invalid_pass_counts(args):
    with pytest.raises(ValueError):pass_at_k(*args)

@pytest.mark.parametrize('successes,trials', [(0,0),(0,10),(10,10),(5,10),(1,100)])
def test_wilson_bounds(successes,trials):
    interval=wilson(successes,trials)
    if trials==0:assert interval is None
    else:
        low,high=interval
        assert 0<=low<=successes/trials<=high<=1
        assert high-low>0

def test_bootstrap_resamples_tasks_not_trials():
    data={'a':[100]*100,'b':[0]}
    result=task_bootstrap(data)
    assert result['mean']==50 and result['tasks']==2 and result['trials']==101
    assert result['interval'] is None and result['evidence']=='insufficient'
    five={str(i):[i*20] for i in range(5)}
    assert task_bootstrap(five,draws=200,seed=17)==task_bootstrap(five,draws=200,seed=17)
    assert task_bootstrap(five)['interval'] is not None

def test_paired_only_common_tasks():
    result=paired_difference({'a':[90],'extra':[100]},{'a':[60],'other':[0]})
    assert result=={'difference':30,'tasks':1,'interval':None}
    assert paired_difference({}, {})['difference'] is None

def test_bradley_terry_requires_connected_evidence():
    assert bradley_terry([('a','b','both_bad')])['strengths']=={}
    assert bradley_terry([('a','b','a'),('c','d','b')])['connected'] is False
    result=bradley_terry([('a','b','a')]*8+[('a','b','b'),('a','b','tie')])
    assert result['strengths']['a']>result['strengths']['b']
    assert result['evidence']=='descriptive_only' and result['intervals'] is None
    with pytest.raises(ValueError):bradley_terry([('a','a','a')])

def test_summary_missing_and_nonfinite():
    assert summary([])=={'n':0,'median':None,'p25':None,'p75':None}
    assert summary([0,10,20])['median']==10
    for value in (-1,float('nan'),float('inf')):
        with pytest.raises(ValueError):summary([value])

def test_state_machine_all_pairs():
    for current,permitted in STATES.items():
        for target in STATES:
            if target in permitted:assert transition(current,target)==target
            else:
                with pytest.raises(ValueError):transition(current,target)
    with pytest.raises(ValueError):transition('unknown','pending')

def test_hash_order_and_nonfinite_rejection():
    assert canonical_hash({'b':2,'a':1})==canonical_hash({'a':1,'b':2})
    assert canonical_hash({'a':1})!=canonical_hash({'a':2})
    with pytest.raises(ValueError):canonical_hash(float('nan'))

def test_missing_and_blocking_checks_never_invent_scores():
    assert technical_score([])['score'] is None
    checks=[{'id':'boot','outcome':'failed','weight':1,'blocking':True},{'id':'art','outcome':'passed','weight':99}]
    assert technical_score(checks)['score']==0
    checks[0]['outcome']='not_run'
    assert technical_score(checks)['score'] is None
    checks[0]['outcome']='passed'
    assert technical_score(checks)['score']==100 and technical_score(checks)['passed']
    with pytest.raises(ValueError):technical_score([checks[0],checks[0]])

@pytest.mark.parametrize('weight', [0,-1,float('nan'),float('inf'),True])
def test_invalid_score_weights(weight):
    with pytest.raises(ValueError):technical_score([{'id':'x','outcome':'passed','weight':weight}])

def test_comparability_requires_all_metadata():
    fields=('suite_version','protocol_version','environment','mode','harness_version','task_set_hash','max_output_tokens','time_limit_seconds','tools_hash','budget_policy')
    a={field:'same' for field in fields}
    assert compare_configurations(a,a)['comparable']
    for field in fields:
        b=a.copy();b.pop(field)
        assert field in compare_configurations(a,b)['differences']
    assert not compare_configurations({}, {})['comparable']

def test_exact_cost_and_budget():
    p=Price(Decimal('2'),Decimal('10'),Decimal('0.5'))
    assert p.estimate_microusd(100,20,40)==340
    assert Price(Decimal('.1'),Decimal('.2')).estimate_microusd(1,1)==1
    with pytest.raises(ValueError):p.estimate_microusd(10,1,11)
    with pytest.raises(ValueError):p.estimate_microusd(True,1)
    validate_budget(100,20,30,50)
    with pytest.raises(ValueError):validate_budget(100,20,30,51)
    with pytest.raises(ValueError):validate_budget(100,0,0,-1)

@pytest.mark.parametrize('name', ['../index.html','/index.html','x/../../index.html','.env','index.html/../x.js','x\\game.js','C:/x.js','x//a.js','x.exe'])
def test_artifact_path_rejections(name):
    with pytest.raises(ValueError):safe_relative(name)

def test_artifact_integrity_and_collision(tmp_path):
    store=ArtifactStore(tmp_path/'objects');digest=store.put(b'original source')
    assert store.get(digest)==b'original source' and store.put(b'original source')==digest
    (store.root/digest[:2]/digest).write_bytes(b'tampered')
    with pytest.raises(ValueError):store.get(digest)
    with pytest.raises(ValueError):store.put(b'original source')
    with pytest.raises(ValueError):validate_project({'index.html':'x','INDEX.HTML':'y'})
    with pytest.raises(ValueError):validate_project({'index.html':'x','a.js':'x','a.js/b.js':'y'})
    assert validate_project({'index.html':'<canvas></canvas>','game.js':'"use strict";'})
