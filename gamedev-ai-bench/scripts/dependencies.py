"""Installed dependency metadata. Not a vulnerability scan or license clearance."""
from importlib.metadata import distribution,PackageNotFoundError
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
import json,sys
root=Path(__file__).resolve().parents[1]
pending=[]
for filename in ('requirements.txt','requirements-dev.txt'):
    for line in (root/filename).read_text().splitlines():
        if line.strip() and not line.startswith(('-', '#')):pending.append(Requirement(line).name)
seen=set();records=[]
while pending:
    name=canonicalize_name(pending.pop())
    if name in seen:continue
    seen.add(name)
    try:dist=distribution(name)
    except PackageNotFoundError:
        records.append({'name':name,'installed':False});continue
    license_name=dist.metadata.get('License-Expression') or dist.metadata.get('License') or ''
    records.append({'name':name,'version':dist.version,'license_metadata':license_name[:400],'license_validation':'operator review required'})
    for raw in dist.requires or []:
        req=Requirement(raw)
        if req.marker is None or req.marker.evaluate({'extra':''}):pending.append(req.name)
result={'recorded_at':'2026-10-13','purpose':'development dependency inventory, not security clearance','packages':sorted(records,key=lambda row:row['name'])}
(root/'docs/DEPENDENCIES.json').write_text(json.dumps(result,indent=2))
print('Recorded',len(records),'dependency metadata entries')
