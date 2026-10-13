"""Local syntax/template/schema/locale checks, not a full security or type audit."""
from pathlib import Path
import ast,json,subprocess,shutil,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jinja2 import Environment,FileSystemLoader,select_autoescape
from gamedev.config import ROOT,Settings
from gamedev.web.app import create_app
from gamedev.database import Base
from fastapi.testclient import TestClient
from scripts.build import source_files,PAGES

count=0
for path in source_files():
    if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path));count+=1
    if path.suffix=='.json':json.loads(path.read_text())
    if path.suffix=='.js' and shutil.which('node'):subprocess.run(['node','--check',str(path)],check=True,capture_output=True)
locales=[json.loads((ROOT/f'gamedev/web/locales/{language}.json').read_text()) for language in ('en','fr')]
assert set(locales[0])==set(locales[1]),'Locale keys do not match'
assert all(isinstance(v,str) and v.strip() for values in locales for v in values.values())
env=Environment(loader=FileSystemLoader(ROOT/'gamedev/web/templates'),autoescape=select_autoescape(['html','xml']))
for template in env.list_templates():env.get_template(template)
with tempfile.TemporaryDirectory(prefix='gdb-validate-') as directory:
    temp=Path(directory);settings=Settings(data_dir=temp/'data',database_url='sqlite:///'+str(temp/'validate.db'),secret='v'*64)
    app=create_app(settings)
    with TestClient(app) as client:
        for language in ('en','fr'):
            for page in PAGES:
                response=client.get('/'+language+('/'+page if page else ''));assert response.status_code==200,(language,page,response.status_code)
        tasks=client.get('/api/v1/tasks').json()['items'];assert len(tasks)==14
        assert client.get('/api/v1/leaderboard').json()['rows']==[]
    app.state.db.engine.dispose()
assert len(Base.metadata.tables)==40
print(json.dumps({'python_syntax_files':count,'matching_locale_keys':len(locales[0]),'sql_tables':40,'task_briefs':14,'rendered_main_routes':len(PAGES)*2,'node_syntax_check':bool(shutil.which('node')),'static_type_analysis':'not performed','vulnerability_audit':'not performed'}))
