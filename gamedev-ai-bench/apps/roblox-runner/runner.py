"""Run from repository root: python apps/roblox-runner/runner.py --help."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from gamedev.adapters.mcp import MCPClient,native_command,execute_plan

def main():
    parser=argparse.ArgumentParser(description='Explicitly consented Roblox Studio MCP runner. No model calls or automatic score claims.')
    parser.add_argument('action',choices=['discover','execute']);parser.add_argument('--plan',type=Path)
    parser.add_argument('--project-copy',type=Path);parser.add_argument('--owner-consent',action='store_true')
    parser.add_argument('--allow-edits',action='store_true');parser.add_argument('--output',type=Path,default=Path('var/roblox-receipt.json'))
    parser.add_argument('--upload',action='store_true',help='Upload private receipt to configured authenticated backend; never publishes a score')
    args=parser.parse_args()
    if not args.owner_consent:
        parser.error('Pass --owner-consent only on a machine you own or are explicitly authorized to operate')
    with MCPClient(native_command()) as client:
        if args.action=='discover':result={'server':client.server,'tools':client.tools}
        else:
            if not args.plan or not args.project_copy:parser.error('--plan and --project-copy are required')
            result=execute_plan(client,json.loads(args.plan.read_text()),consent=True,allow_edits=args.allow_edits,project_copy=args.project_copy)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    if args.upload:
        import httpx
        origin=os.environ['GDB_BACKEND_ORIGIN'].rstrip('/')
        if not origin.startswith('https://'):raise ValueError('Receipt uploads require HTTPS')
        response=httpx.post(origin+'/api/v1/runner/evidence',json=result,headers={'Authorization':'Bearer '+os.environ['GDB_RUNNER_TOKEN']},timeout=30,follow_redirects=False)
        response.raise_for_status();print('Private receipt accepted:',response.json()['receipt_id'])
    print('Saved',args.output,'- this is not an automatically verified benchmark result')
if __name__=='__main__':main()
