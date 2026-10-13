"""MCP stdio transport: tool names AND schemas are discovered, never invented."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from hashlib import sha256
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
import json
import os
import platform
import subprocess
import time
import jsonschema

# No uploads, publishing, external asset generation, or HTTP tools in this runner.
READ_TOOLS={'get_studio_state','list_roblox_studios','script_read','script_search','script_grep','search_game_tree','inspect_instance','get_console_output','screen_capture'}
EDIT_TOOLS={'execute_luau','multi_edit','start_stop_play','character_navigation','user_keyboard_input','user_mouse_input'}


def native_command() -> list[str]:
    system=platform.system()
    if system=='Windows':
        local=os.environ.get('LOCALAPPDATA')
        if not local:
            raise RuntimeError('LOCALAPPDATA is missing')
        bridge=Path(local)/'Roblox'/'mcp.bat'
        if not bridge.exists():
            raise FileNotFoundError('Enable Roblox Studio MCP and verify the official bridge')
        return ['cmd.exe','/c',str(bridge)]
    if system=='Darwin':
        bridge=Path('/Applications/RobloxStudio.app/Contents/MacOS/StudioMCP')
        if not bridge.exists():
            raise FileNotFoundError('Roblox Studio native MCP bridge not found')
        return [str(bridge)]
    raise RuntimeError('Native Roblox Studio runner requires Windows or macOS. Linux tests use a clearly labelled mock only.')


class MCPClient:
    def __init__(self, command: list[str], timeout: float=30):
        if not command or timeout<=0 or timeout>120:
            raise ValueError('Invalid subprocess command or timeout')
        self.command=command;self.timeout=timeout;self.counter=0;self.process=None;self.messages=Queue();self.tools={}
        self.notifications=[];self.stderr=[]
    def __enter__(self):
        self.process=subprocess.Popen(self.command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,encoding='utf-8',bufsize=1,shell=False)
        def reader():
            for line in iter(self.process.stdout.readline,''):
                if len(line)>8_000_000:
                    self.messages.put(RuntimeError('MCP response exceeded 8 MB'));break
                try:
                    self.messages.put(json.loads(line))
                except ValueError:
                    self.messages.put(RuntimeError('MCP stdout is not newline-delimited JSON'))
            self.messages.put(RuntimeError('MCP process closed stdout'))
        def err_reader():
            for line in iter(self.process.stderr.readline,''):
                if sum(map(len,self.stderr))<8000:
                    self.stderr.append(line[:1000])
        Thread(target=reader,daemon=True).start();Thread(target=err_reader,daemon=True).start()
        try:
            self.server=self.request('initialize',{'protocolVersion':'2025-06-18','capabilities':{},
                'clientInfo':{'name':'gamedev-ai-bench','version':'0.1.0'}})
            if self.server.get('protocolVersion') not in ('2025-06-18','2024-11-05','2025-03-26'):
                raise RuntimeError('Unsupported negotiated MCP version; qualify it before execution')
            self.send({'jsonrpc':'2.0','method':'notifications/initialized'})
            self.discover()
            return self
        except Exception:
            self.close();raise
    def send(self,message):
        if not self.process or self.process.poll() is not None:
            raise RuntimeError('MCP process is not running')
        self.process.stdin.write(json.dumps(message,separators=(',',':'))+'\n');self.process.stdin.flush()
    def request(self,method,params):
        self.counter+=1;request_id=self.counter
        self.send({'jsonrpc':'2.0','id':request_id,'method':method,'params':params});deadline=time.monotonic()+self.timeout
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:
                raise TimeoutError(f'MCP request timed out: {method}')
            try:
                response=self.messages.get(timeout=remaining)
            except Empty:
                raise TimeoutError(f'MCP request timed out: {method}') from None
            if isinstance(response,Exception):
                raise response
            if 'method' in response:
                if 'id' in response:
                    # Server-initiated sampling and elicitation are deliberately not supported.
                    self.send({'jsonrpc':'2.0','id':response['id'],'error':{'code':-32601,'message':'Server-initiated requests are disabled'}})
                elif len(self.notifications)<100:
                    self.notifications.append(response)
                continue
            if response.get('id')!=request_id:
                raise RuntimeError('Unexpected MCP response identifier')
            if 'error' in response:
                raise RuntimeError(f'MCP error for {method}: {response["error"].get("code")}')
            return response.get('result',{})
    def discover(self):
        cursor=None
        for _ in range(20):
            page=self.request('tools/list',{'cursor':cursor} if cursor else {})
            for tool in page.get('tools',[]):
                if not isinstance(tool.get('name'),str) or not isinstance(tool.get('inputSchema'),dict):
                    raise RuntimeError('Invalid MCP tool descriptor')
                jsonschema.Draft202012Validator.check_schema(tool['inputSchema']);self.tools[tool['name']]=tool
            cursor=page.get('nextCursor')
            if not cursor:
                return self.tools
        raise RuntimeError('MCP tool pagination limit exceeded')
    def call(self,name: str,arguments: dict,*,allow_edits=False):
        if name not in READ_TOOLS and not (allow_edits and name in EDIT_TOOLS):
            raise PermissionError('Tool not approved for this runner')
        if name not in self.tools:
            raise ValueError('Required tool is not exposed by the installed Studio MCP')
        jsonschema.validate(arguments,self.tools[name]['inputSchema'])
        result=self.request('tools/call',{'name':name,'arguments':arguments})
        if result.get('isError'):
            raise RuntimeError('Studio tool reported an execution error')
        return result
    def close(self):
        if self.process:
            if self.process.stdin:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:self.process.kill()
            self.process=None
    def __exit__(self,*args):
        self.close()


def execute_plan(client:MCPClient,plan:dict,*,consent:bool,allow_edits:bool,project_copy:Path) -> dict:
    if not consent or not project_copy.is_file() or project_copy.suffix.lower() not in ('.rbxl','.rbxlx'):
        raise PermissionError('Explicit owner consent and a disposable Roblox project copy are required')
    if plan.get('project_copy')!=str(project_copy.resolve()):
        raise ValueError('Approved plan must identify the disposable project copy')
    steps=plan.get('steps',[])
    if not 1<=len(steps)<=40:
        raise ValueError('A plan needs between 1 and 40 explicitly reviewed steps')
    before=sha256(project_copy.read_bytes()).hexdigest();events=[]
    for step in steps:
        started=time.monotonic();name=step['tool'];arguments=step.get('arguments',{})
        result=client.call(name,arguments,allow_edits=allow_edits)
        events.append({'tool':name,'arguments_hash':sha256(json.dumps(arguments,sort_keys=True).encode()).hexdigest(),
                       'duration_ms':round((time.monotonic()-started)*1000),'result':result})
    return {'kind':'roblox-local-runner-receipt','protocol':'studio-discovery/1','server':client.server,
            'tool_schemas':client.tools,'project_before_sha256':before,
            'project_after_sha256':sha256(project_copy.read_bytes()).hexdigest(),'events':events,
            'limitations':['Tool execution is not automatically a successful benchmark. Review assertions and evidence independently.',
                          'Owner must verify active Studio is the disposable copy before approving edit steps.']}
