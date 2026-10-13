"""Browser observations; only an externally sandboxed process may open untrusted games."""
from contextlib import contextmanager
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
import json
import os
import shutil
import time


@contextmanager
def local_server(project: Path):
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def end_headers(self):
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'")
            self.send_header('X-Content-Type-Options','nosniff')
            super().end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(project)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown();server.server_close();thread.join(2)


def evaluate(project: Path, output: Path, *, trusted_fixture: bool=False) -> dict:
    if not trusted_fixture and os.getenv('GDB_INSIDE_SANDBOX')!='1':
        raise PermissionError('Untrusted games require the isolated container; never run on the application host')
    from playwright.sync_api import sync_playwright
    output.mkdir(parents=True,exist_ok=True)
    results=[];errors=[];metrics={};started=time.monotonic()
    def check(name, action, blocking=False):
        try:
            observed=action()
            results.append({'id':name,'outcome':'passed','weight':1,'blocking':blocking,'observed':observed or {}})
        except Exception as exc:
            results.append({'id':name,'outcome':'failed','weight':1,'blocking':blocking,'observed':{'error':str(exc)[:700]}})
    with local_server(project) as origin, sync_playwright() as pw:
        executable=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium')
        browser=pw.chromium.launch(executable_path=executable,headless=True)
        context=browser.new_context(viewport={'width':960,'height':640},accept_downloads=False,service_workers='block')
        context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
        page=context.new_page();page.set_default_timeout(3500)
        page.on('pageerror',lambda error:errors.append(str(error)[:500]))
        page.on('dialog',lambda dialog:dialog.dismiss())
        def boot():
            if trusted_fixture and os.getenv('BROWSER_COMPONENT_TESTS')=='true':
                html=(project/'index.html').read_text()
                html=html.replace('<link rel="stylesheet" href="style.css">','<style>'+(project/'style.css').read_text()+'</style>')
                html=html.replace('<script src="game.js" defer></script>','<script>'+(project/'game.js').read_text()+'</script>')
                page.set_content(html,wait_until='load')
                page.wait_for_timeout(250)
                metrics['transport']='in-memory component rendering; HTTP navigation not exercised'
                return {'component_loaded':True,'http_status':None}
            response=page.goto(origin+'/index.html',wait_until='load',timeout=10000)
            assert response and response.status==200,'Game did not load'
            page.wait_for_timeout(250)
            metrics['load_ms']=round((time.monotonic()-started)*1000)
            return {'http_status':response.status}
        check('boot',boot,True)
        def canvas():
            node=page.locator('canvas').first;assert node.is_visible(),'Canvas not visible'
            box=node.bounding_box();assert box and box['width']>=150 and box['height']>=100,'Canvas too small'
            # Real pixel diversity, not just the presence of an element.
            pixels=node.evaluate('(c)=>{const a=c.getContext("2d");if(!a)return null;const d=a.getImageData(0,0,c.width,c.height).data;let n=new Set();for(let i=0;i<d.length;i+=400)n.add(`${d[i]},${d[i+1]},${d[i+2]}`);return n.size;}')
            assert pixels is None or pixels>2,'Canvas is blank'
            return {'width':box['width'],'height':box['height'],'sample_colors':pixels}
        check('canvas',canvas)
        def start():
            page.get_by_test_id('start').click();assert page.get_by_test_id('state').text_content()=='running','Start does not change game state'
        check('start',start,True)
        def keyboard():
            player=page.get_by_test_id('player');before=float(player.get_attribute('data-x'))
            page.keyboard.down('ArrowRight');page.wait_for_timeout(180);page.keyboard.up('ArrowRight')
            after=float(player.get_attribute('data-x'));assert after>before+2,'Keyboard did not move player'
            return {'before_x':before,'after_x':after,'limitation':'Game-reported position, accompanied by screenshot; not an independent semantic gameplay oracle'}
        check('keyboard',keyboard)
        def restart():
            page.get_by_test_id('restart').click();assert int(page.get_by_test_id('score').inner_text())==0,'Score not reset'
            assert page.get_by_test_id('state').text_content() in ('ready','running'),'Restart did not reset state'
        check('restart',restart)
        page.screenshot(path=str(output/'desktop.png'))
        def mobile():
            page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Horizontal overflow on mobile'
            assert page.get_by_test_id('start').is_visible(),'Mobile start not visible'
            return {'viewport':'390x844'}
        check('mobile',mobile)
        def touch():
            page.get_by_test_id('start').click();before=float(page.get_by_test_id('player').get_attribute('data-x'))
            page.get_by_test_id('touch-right').click();page.wait_for_timeout(70)
            after=float(page.get_by_test_id('player').get_attribute('data-x'));assert after>before,'Touch control did not move player'
            return {'before_x':before,'after_x':after,'input':'pointer click; native touch tested separately in E2E'}
        check('touch',touch)
        def runtime():
            assert not errors,'; '.join(errors)
            return {'page_errors':0,'observation_window':'This test only; not long-run stability'}
        check('runtime',runtime,True)
        page.screenshot(path=str(output/'mobile.png'))
        metrics['duration_ms']=round((time.monotonic()-started)*1000)
        browser.close()
    report={'harness':'gdb-web-smoke/1.0.0','assertions':results,'metrics':metrics,'runtime_errors':errors,
            'fixture':trusted_fixture,'limitations':['Contract-based smoke checks, not a complete game-quality score.','No FPS or human creativity metric is inferred.']}
    (output/'evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
