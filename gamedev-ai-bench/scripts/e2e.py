"""Actual HTTP integration and browser journey. Not set_content/component tests."""
from pathlib import Path
import argparse,json,os,secrets,shutil,socket,subprocess,sys,tempfile,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from sqlalchemy import select
from gamedev.config import ROOT,Settings
from gamedev.database import Database,User
from gamedev.catalog import seed_catalog
from gamedev.security import hash_password


def run(allow_policy_skip=False):
    from playwright.sync_api import sync_playwright,expect
    report={'kind':'actual-http-end-to-end','http_api':'not_run','browser':'not_run','checks':[],'live_provider_calls':0}
    output=ROOT/'evidence/e2e.json';output.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gdb-e2e-') as temporary:
        temp=Path(temporary)
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        origin=f'http://127.0.0.1:{port}';password=secrets.token_urlsafe(30)
        settings=Settings(origin=origin,data_dir=temp/'data',database_url='sqlite:///'+str(temp/'e2e.db'),secret=secrets.token_urlsafe(48))
        db=Database(settings.database_url);db.migrate();seed_catalog(db)
        with db.session() as session:session.add(User(email='e2e-only@example.test',name='E2E fixture operator',password_hash=hash_password(password),role='admin'))
        db.engine.dispose()
        env=os.environ.copy();env.update(APP_ENV='development',APP_ORIGIN=origin,DATA_DIR=str(settings.data_dir),DATABASE_URL=settings.database_url,APP_SECRET=settings.secret,ENABLE_PAID_RUNS='false',ALLOW_REGISTRATION='false')
        env.pop('BROWSER_COMPONENT_TESTS',None)
        for key in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','GEMINI_API_KEY','DEEPSEEK_API_KEY','QWEN_API_KEY','ZAI_API_KEY','MOONSHOT_API_KEY','STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','STRIPE_PRICE_ID'):env[key]=''
        with (temp/'server.log').open('w') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','gamedev.web.app:create_app','--factory','--host','127.0.0.1','--port',str(port),'--no-access-log','--no-proxy-headers'],cwd=ROOT,env=env,stdout=log,stderr=log)
            try:
                with httpx.Client(base_url=origin,trust_env=False,timeout=5) as client:
                    for _ in range(100):
                        try:
                            if client.get('/api/v1/health').status_code==200:break
                        except httpx.HTTPError:pass
                        if process.poll() is not None:raise RuntimeError('HTTP server exited before health check')
                        time.sleep(.1)
                    else:raise RuntimeError('HTTP server did not become ready')
                    for path in ('/en','/fr','/api/v1/models','/api/v1/tasks','/api/v1/leaderboard','/api/v1/openapi.json','/fixtures/orbital/index.html','/static/app.js','/sitemap.xml'):
                        response=client.get(path);assert response.status_code==200,(path,response.status_code)
                        assert response.headers['x-content-type-options']=='nosniff'
                    assert client.get('/api/v1/admin/status').status_code==401
                    assert client.post('/api/v1/contact',json={}).status_code==403
                    report['http_api']='passed';report['checks'].append('actual HTTP: 9 public routes, protected admin and rejected CSRF-free mutation')
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
                    try:
                        page=browser.new_page(viewport={'width':1440,'height':960});errors=[]
                        page.on('pageerror',lambda error:errors.append(str(error)))
                        try:page.goto(origin+'/en',wait_until='networkidle')
                        except Exception as error:
                            if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(error) and allow_policy_skip:
                                report['browser']='skipped_by_browser_administrator_policy'
                                report['limitation']='HTTP API tested; browser navigation blocked. No policy bypass or claim of browser network success.'
                                return report
                            raise
                        expect(page.locator('h1')).to_be_visible()
                        page.locator('.theme-toggle').click();assert page.locator('html').get_attribute('data-theme')=='light'
                        page.locator('.language-toggle').click();expect(page.locator('html')).to_have_attribute('lang','fr')
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                        report['checks'].append('actual browser home/theme/language')
                        page.goto(origin+'/en/leaderboard',wait_until='networkidle');page.locator('#model-search').fill('astra')
                        assert page.locator('.model-row:visible').count()==1
                        page.goto(origin+'/en/compare',wait_until='networkidle')
                        page.locator('[name=models]').nth(0).check();page.locator('[name=models]').nth(1).check()
                        page.locator('#compare-form button[type=submit]').click();expect(page.locator('.comparison-table')).to_be_visible()
                        report['checks'].append('actual browser filters and API metadata comparison')
                        page.goto(origin+'/en/arena',wait_until='networkidle')
                        for side in ('a','b'):
                            frame=page.frame_locator('#game-'+side);frame.get_by_test_id('start').click();expect(frame.get_by_test_id('state')).to_have_text('running')
                        page.locator('#new-match').click();expect(page.locator('[data-vote=tie]')).to_be_enabled(timeout=12000)
                        page.locator('[data-vote=tie]').click();expect(page.locator('#vote-status')).to_contain_text('Authored')
                        report['checks'].append('actual sandboxed original games, fixture pairing and persisted vote')
                        page.goto(origin+'/en/login',wait_until='networkidle')
                        page.locator('[name=email]').fill('e2e-only@example.test');page.locator('[name=password]').fill(password)
                        page.locator('#auth-form button[type=submit]').click();page.wait_for_url('**/admin',timeout=10000)
                        form=page.locator('#campaign-form');form.locator('[name=name]').fill('HTTP E2E internal fixture only')
                        form.locator('[name=configuration_id]').select_option('fixture-reference');form.locator('[name=task_id]').select_option('web-orbit')
                        form.locator('[name=budget]').fill('0');form.locator('[type=submit]').click()
                        expect(form.locator('.form-message')).to_contain_text('Campaign saved.')
                        subprocess.run([sys.executable,'-m','gamedev.cli','worker','--once','--fixture-only'],cwd=ROOT,env=env,check=True,timeout=90,capture_output=True)
                        status=page.request.get(origin+'/api/v1/admin/status').json();runs=status['runs'];assert len(runs)==1,runs
                        run_id=runs[0]['id'];detail=page.request.get(origin+'/api/v1/runs/'+run_id).json()
                        assert detail['state']=='awaiting-review' and detail['score']['passed'],detail
                        assert len(detail['assertions'])==8
                        assert page.request.get(origin+'/api/v1/leaderboard').json()['rows']==[]
                        report['checks'].append('actual login, admin enqueue and HTTP Chromium fixture worker; 8 assertions passed; no AI ranking')
                        page.set_viewport_size({'width':390,'height':844});page.goto(origin+'/fr',wait_until='networkidle')
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                        page.locator('.mobile-toggle').click();expect(page.locator('.mobile-toggle')).to_have_attribute('aria-expanded','true')
                        page.keyboard.press('Escape');assert errors==[],errors
                        report['checks'].append('actual mobile navigation and no page script errors')
                        report['browser']='passed'
                    finally:browser.close()
            finally:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
                output.write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--allow-policy-skip',action='store_true');args=parser.parse_args()
    print(json.dumps(run(args.allow_policy_skip),indent=2))
