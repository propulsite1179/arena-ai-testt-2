"""Explicit stdio protocol double. Never claim this is Roblox Studio."""
import json,sys
for line in sys.stdin:
    request=json.loads(line)
    if 'id' not in request:continue
    method=request['method']
    if method=='initialize':result={'protocolVersion':'2025-06-18','serverInfo':{'name':'explicit-test-mock-not-roblox','version':'1'},'capabilities':{'tools':{}}}
    elif method=='tools/list':result={'tools':[
        {'name':'get_studio_state','inputSchema':{'type':'object','properties':{},'additionalProperties':False}},
        {'name':'execute_luau','inputSchema':{'type':'object','properties':{'code':{'type':'string'}},'required':['code'],'additionalProperties':False}}]}
    elif method=='tools/call':result={'content':[{'type':'text','text':'MOCK ONLY'}],'isError':False}
    else:result={}
    print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}),flush=True)
