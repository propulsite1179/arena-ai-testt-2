"""Build a portable, read-only public export. Never exports accounts or local data."""
from pathlib import Path
import argparse,json,re,shutil,sys,tempfile,zipfile,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from gamedev.config import ROOT,Settings
from gamedev.web.app import create_app

PAGES=['','leaderboard','models','roblox','web-games','arena','compare','lab','methodology','news','pro','enterprise','partners','contact','about','faq','privacy','terms','legal','api','login','register']
EXCLUDED={'var','dist','.git','.venv','__pycache__','.pytest_cache','node_modules'}

def source_files(root=ROOT):
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if not path.is_file() or path.is_symlink() or any(part in EXCLUDED for part in relative.parts):continue
        if path.name=='.env' or path.name.startswith('.local-session') or path.suffix in ('.db','.pyc','.log','.b64','.xz','.zip'):continue
        # Generated image evidence is provided separately, not required for reproduction.
        if relative.parts[0]=='evidence' and path.suffix in ('.png','.webm'):continue
        yield path

def build(base='',origin='https://example.invalid',output=None):
    if base and not re.fullmatch(r'/[A-Za-z0-9_.-]+',base):raise ValueError('base must be empty or one safe repository segment')
    if not re.fullmatch(r'https?://[A-Za-z0-9.:-]+',origin):raise ValueError('origin must be an HTTP(S) origin without a path')
    destination=Path(output or ROOT/'dist/site').resolve()
    # Refuse to erase anything except an existing known static-build output.
    if destination.exists():
        if not (destination/'.gdb-static-build').is_file():raise ValueError('Refusing to replace an unrecognized output folder')
        shutil.rmtree(destination)
    destination.mkdir(parents=True);(destination/'.gdb-static-build').write_text('Read-only build output\n')
    with tempfile.TemporaryDirectory(prefix='gdb-static-') as temporary:
        temp=Path(temporary)
        settings=Settings(data_dir=temp/'data',database_url='sqlite:///'+str(temp/'build.db'),secret='static-build-only-not-a-production-secret-'+'x'*32,origin='http://127.0.0.1:8000')
        app=create_app(settings)
        with TestClient(app) as client:
            models=client.get('/api/v1/models').json();tasks=client.get('/api/v1/tasks').json()['items']
            localized=PAGES+['models/'+m['id'] for m in models['items']]+['tasks/'+task['id'] for task in tasks]
            locales={language:json.loads((ROOT/f'gamedev/web/locales/{language}.json').read_text()) for language in ('en','fr')}
            pages=[]
            for language in ('en','fr'):
                for page in localized:
                    route='/'+language+('/'+page if page else '')
                    response=client.get(route);response.raise_for_status()
                    soup=BeautifulSoup(response.text,'html.parser')
                    soup.select_one('meta[name=csrf-token]')['content']=''
                    soup.select_one('meta[name=gdb-static]')['content']='true'
                    soup.select_one('meta[name=gdb-base]')['content']=base
                    warning=soup.new_tag('aside',attrs={'class':'notice static-notice','role':'note'})
                    warning.string=locales[language]['static_notice'];soup.select_one('main').insert(0,warning)
                    # Static hosting cannot provide dynamic CSP headers. Only reviewed
                    # original fixtures are published, never model-generated artifacts.
                    policy=soup.new_tag('meta',attrs={'http-equiv':'Content-Security-Policy','content':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'"})
                    soup.head.append(policy)
                    for tag in soup.find_all(True):
                        for attr in ('href','src','action'):
                            value=tag.get(attr)
                            if not isinstance(value,str):continue
                            if value.startswith(settings.origin+'/'):
                                tag[attr]=origin+base+value[len(settings.origin):]
                            elif value.startswith('/') and not value.startswith('//'):
                                if value in ('/en/account','/fr/account'):value='/'+language+'/login'
                                if value.startswith('/api/v1/export/'):
                                    value='/static/results.'+value.rsplit('/',1)[1]
                                elif value=='/api/v1/openapi.json':value='/static/openapi.json'
                                elif value.startswith('/api/'):
                                    value='/'+language+'/api'
                                tag[attr]=base+value
                        if tag.get('property')=='og:image':tag['content']=origin+base+'/static/world.svg'
                    target=destination/route.lstrip('/')/'index.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(str(soup),encoding='utf-8');pages.append(route+'/')
            shutil.copytree(ROOT/'gamedev/web/static',destination/'static',dirs_exist_ok=True)
            shutil.copytree(ROOT/'packages/test-fixtures/games',destination/'fixtures')
            (destination/'static/catalog.json').write_text(json.dumps(models,ensure_ascii=False))
            (destination/'static/openapi.json').write_text(json.dumps(client.get('/api/v1/openapi.json').json(),indent=2))
            for kind in ('json','csv'):(destination/f'static/results.{kind}').write_bytes(client.get('/api/v1/export/'+kind).content)
        app.state.db.engine.dispose()
    (destination/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url='+base+'/en/"><title>GameDev AI Bench</title></head><body><a href="'+base+'/en/">Open GameDev AI Bench</a></body></html>')
    (destination/'.nojekyll').write_text('')
    (destination/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+origin+base+'/sitemap.xml\n')
    (destination/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+origin+base+page+'</loc></url>' for page in pages if not page.endswith(('/login/','/register/')) )+'</urlset>')
    build_info={'kind':'read-only-static-preview','dynamic_backend':False,'model_results':0,'public_pages':len(pages),'base':base,'source_required_for_server':True}
    (destination/'build-info.json').write_text(json.dumps(build_info,indent=2))
    # Check local navigation and asset destinations, including nested project bases.
    broken=[]
    for page in destination.rglob('*.html'):
        soup=BeautifulSoup(page.read_text(),'html.parser')
        for node in soup.select('[href],[src],[action]'):
            for attr in ('href','src','action'):
                value=node.get(attr,'').split('?',1)[0].split('#',1)[0]
                if not value.startswith('/') or value.startswith('//'):continue
                relative=value[len(base):].lstrip('/') if base and value.startswith(base+'/') else value.lstrip('/')
                target=destination/relative
                if not target.is_file() and not (target/'index.html').is_file():broken.append((str(page.relative_to(destination)),value))
    if broken:raise ValueError('Broken static links: '+str(broken[:20]))
    print(json.dumps(build_info))
    return destination

def archive():
    destination=ROOT/'dist/gamedev-ai-bench-source.zip';destination.parent.mkdir(exist_ok=True)
    manifest={}
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as output:
        for path in source_files():
            name=path.relative_to(ROOT).as_posix();manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            output.write(path,'gamedev-ai-bench/'+name)
        output.writestr('gamedev-ai-bench/SOURCE_MANIFEST.json',json.dumps(manifest,indent=2))
    print('Source archive:',destination,'files:',len(manifest))
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',default='');parser.add_argument('--origin',default='https://example.invalid');parser.add_argument('--output',type=Path)
    args=parser.parse_args();build(args.base,args.origin,args.output);archive()
