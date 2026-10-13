"""Mock-only provider and MCP contract tests. These never claim live AI/Studio runs."""
from pathlib import Path
from types import SimpleNamespace
import json,sys
import httpx,pytest,jsonschema
from gamedev.adapters.providers import ProviderAdapter,ProviderError
from gamedev.adapters.mcp import MCPClient,execute_plan
from gamedev.config import ROOT,Settings
from gamedev.services.evaluator import evaluate

def provider(kind='openai_responses',host='https://api.openai.com/v1'):
    return SimpleNamespace(adapter=kind,base_url=host,key_env='GDB_TEST_ONLY_KEY')

@pytest.mark.parametrize('url', ['http://api.openai.com/v1','https://127.0.0.1/v1','https://api.openai.com.attacker.test/v1','https://secret@api.openai.com/v1','https://api.openai.com/v1?key=bad'])
def test_provider_rejects_unreviewed_endpoints(url):
    with pytest.raises(ValueError):ProviderAdapter(provider(host=url))

def test_responses_contract_and_no_hidden_retry(monkeypatch):
    monkeypatch.setenv('GDB_TEST_ONLY_KEY','mock-secret-not-a-real-key');seen=[]
    def transport(request):
        body=json.loads(request.content);seen.append(body)
        assert request.url.path=='/v1/responses' and body['store'] is False
        assert body['reasoning']=={'effort':'low'}
        return httpx.Response(200,json={'id':'mock-response','model':'mock-model','status':'completed','output':[{'content':[{'type':'output_text','text':'mock code'}]}],'usage':{'input_tokens':100,'output_tokens':20,'input_tokens_details':{'cached_tokens':30}}})
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        result=ProviderAdapter(provider(),client).generate('mock-model','system','prompt',128,'low')
    assert result.text=='mock code' and result.cached_tokens==30 and len(seen)==1
    calls=[]
    def limited(request):calls.append(request);return httpx.Response(429,headers={'Retry-After':'5'})
    with httpx.Client(transport=httpx.MockTransport(limited)) as client:
        with pytest.raises(ProviderError) as error:ProviderAdapter(provider(),client).generate('mock-model','system','prompt',128)
    assert error.value.code=='rate_limited' and error.value.retry_after=='5' and len(calls)==1

def test_provider_missing_credentials(monkeypatch):
    monkeypatch.delenv('GDB_TEST_ONLY_KEY',raising=False)
    with httpx.Client(transport=httpx.MockTransport(lambda _:pytest.fail('Network must not be reached'))) as client:
        with pytest.raises(ProviderError,match='provider_not_configured'):ProviderAdapter(provider(),client).list_models()

def test_anthropic_native_contract(monkeypatch):
    monkeypatch.setenv('GDB_TEST_ONLY_KEY','mock-key')
    def transport(request):
        assert request.headers['x-api-key']=='mock-key' and request.url.path=='/v1/messages'
        assert 'reasoning' not in json.loads(request.content)
        return httpx.Response(200,json={'content':[{'type':'text','text':'code'}],'usage':{'input_tokens':10,'cache_read_input_tokens':3,'cache_creation_input_tokens':2,'output_tokens':4},'stop_reason':'end_turn'})
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        adapter=ProviderAdapter(provider('anthropic_messages','https://api.anthropic.com/v1'),client)
        result=adapter.generate('mock-model','s','p',128)
        assert result.input_tokens==15 and result.cached_tokens==3
        with pytest.raises(ValueError):adapter.generate('mock-model','s','p',128,'high')

def test_gemini_native_contract(monkeypatch):
    monkeypatch.setenv('GDB_TEST_ONLY_KEY','mock-key')
    def transport(request):
        assert request.headers['x-goog-api-key']=='mock-key'
        assert request.url.path.endswith('/models/mock-model:generateContent')
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'thought':True,'text':'private'},{'text':'code'}]},'finishReason':'STOP'}],'usageMetadata':{'promptTokenCount':10,'candidatesTokenCount':5,'thoughtsTokenCount':7}})
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        result=ProviderAdapter(provider('gemini','https://generativelanguage.googleapis.com/v1beta'),client).generate('mock-model','s','p',128)
        assert result.text=='code' and result.output_tokens==12

def test_stdio_mcp_discovers_and_enforces_schema():
    with MCPClient([sys.executable,str(ROOT/'tests/mock_mcp.py')],timeout=5) as client:
        assert client.server['serverInfo']['name']=='explicit-test-mock-not-roblox'
        assert client.call('get_studio_state',{})['content'][0]['text']=='MOCK ONLY'
        with pytest.raises(PermissionError):client.call('execute_luau',{'code':'return true'})
        with pytest.raises(PermissionError):client.call('publish_game',{},allow_edits=True)
        with pytest.raises(jsonschema.ValidationError):client.call('execute_luau',{},allow_edits=True)
        assert client.call('execute_luau',{'code':'return true'},allow_edits=True)

def test_mcp_plan_consent_and_disposable_copy(tmp_path):
    project=tmp_path/'disposable.rbxlx';project.write_text('<roblox version="4"/>')
    plan={'project_copy':str(project.resolve()),'steps':[{'tool':'get_studio_state','arguments':{}}]}
    with MCPClient([sys.executable,str(ROOT/'tests/mock_mcp.py')],timeout=5) as client:
        with pytest.raises(PermissionError):execute_plan(client,plan,consent=False,allow_edits=False,project_copy=project)
        result=execute_plan(client,plan,consent=True,allow_edits=False,project_copy=project)
        assert result['project_before_sha256']==result['project_after_sha256'] and len(result['events'])==1
        assert 'score' not in result and result['limitations']

def test_untrusted_games_fail_closed(tmp_path,monkeypatch):
    monkeypatch.delenv('GDB_INSIDE_SANDBOX',raising=False)
    with pytest.raises(PermissionError):evaluate(tmp_path,tmp_path/'output')

@pytest.mark.parametrize('changes', [{'secret':'short'},{'origin':'http://example.test'},{'database_url':'sqlite:///unsafe.db'},{'game_origin':'https://example.test'}])
def test_production_settings_fail_closed(changes,tmp_path):
    values=dict(environment='production',secret='x'*64,origin='https://example.test',database_url='postgresql+psycopg://test@localhost/bench',data_dir=tmp_path)
    values.update(changes)
    with pytest.raises(ValueError):Settings(**values).validate()
