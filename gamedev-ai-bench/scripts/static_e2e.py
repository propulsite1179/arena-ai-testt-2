"""Exercise the actual read-only export over HTTP with deployment CSP headers."""
from pathlib import Path
import functools,json,shutil,sys,tempfile,threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright,expect
from gamedev.config import ROOT
from scripts.build import build


def run():
    report={'kind':'static-export-http-browser','browser':'not_run','checks':[]}
    output=ROOT/'evidence/static-e2e.json';output.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gdb-static-e2e-') as temporary:
        destination=build(output=Path(temporary)/'site')
        headers=json.loads((ROOT/'vercel.json').read_text())['headers'][0]['headers']
        class Handler(SimpleHTTPRequestHandler):
            def end_headers(self):
                for header in headers:self.send_header(header['key'],header['value'])
                super().end_headers()
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(destination)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
                try:
                    page=browser.new_page(viewport={'width':1440,'height':960});errors=[];mutations=[]
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.on('request',lambda request:mutations.append(request.url) if request.method not in ('GET','HEAD') else None)
                    page.goto(origin+'/en/',wait_until='networkidle')
                    expect(page.locator('h1')).to_be_visible()
                    assert page.locator('meta[name=gdb-static]').get_attribute('content')=='true'
                    expect(page.locator('.static-notice')).to_be_visible()
                    page.locator('.theme-toggle').click();expect(page.locator('html')).to_have_attribute('data-theme','light')
                    page.locator('.language-toggle').click();expect(page.locator('html')).to_have_attribute('lang','fr')
                    report['checks'].append('Public assets, EN/FR navigation and theme loaded under deployment CSP')
                    page.goto(origin+'/en/compare/',wait_until='networkidle')
                    page.locator('[name=models]').nth(0).check();page.locator('[name=models]').nth(1).check()
                    page.locator('#compare-form button[type=submit]').click()
                    expect(page.locator('.comparison-table')).to_be_visible()
                    expect(page.locator('#save-comparison')).to_be_disabled()
                    report['checks'].append('Local catalog comparison works; account save explicitly disabled')
                    page.goto(origin+'/en/arena/',wait_until='networkidle')
                    for side in ('a','b'):
                        frame=page.frame_locator('#game-'+side)
                        frame.get_by_test_id('start').click();expect(frame.get_by_test_id('state')).to_have_text('running')
                    expect(page.locator('#new-match')).to_be_disabled()
                    for choice in ('a','b','tie','both_bad'):expect(page.locator('[data-vote='+choice+']')).to_be_disabled()
                    report['checks'].append('Both sandboxed reference games playable; server pairing/votes disabled')
                    page.goto(origin+'/en/contact/',wait_until='networkidle')
                    expect(page.locator('#contact-form button[type=submit]')).to_be_disabled()
                    page.goto(origin+'/en/login/',wait_until='networkidle')
                    expect(page.locator('#auth-form button[type=submit]')).to_be_disabled()
                    page.set_viewport_size({'width':390,'height':844});page.goto(origin+'/fr/',wait_until='networkidle')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
                    page.locator('.mobile-toggle').click();expect(page.locator('.mobile-toggle')).to_have_attribute('aria-expanded','true')
                    page.keyboard.press('Escape');expect(page.locator('.mobile-toggle')).to_have_attribute('aria-expanded','false')
                    assert not errors and not mutations,{'errors':errors,'mutations':mutations}
                    report['checks'].append('Mobile menu, no script errors, no write requests, no fictitious login/contact')
                    report['browser']='passed'
                finally:browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
            output.write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':print(json.dumps(run(),indent=2))
