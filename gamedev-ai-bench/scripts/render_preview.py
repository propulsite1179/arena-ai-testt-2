"""Real HTTP deployment screenshots; trusted in-memory helper for unit components."""
from pathlib import Path
import base64
import functools
import json
import os
import re
import shutil
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, expect
from gamedev.config import ROOT
from scripts.build import build


def inline_document(client,path,include_app_script=True):
    response=client.get(path);response.raise_for_status()
    soup=BeautifulSoup(response.text,'html.parser')
    for tag in list(soup.select('link[rel=stylesheet]')):
        result=client.get(tag['href']);result.raise_for_status()
        style=soup.new_tag('style');style.string=result.text;tag.replace_with(style)
    for tag in list(soup.select('script[src]')):
        if not include_app_script:tag.decompose();continue
        result=client.get(tag['src']);result.raise_for_status()
        script=soup.new_tag('script');script.string=result.text;tag.decompose();soup.body.append(script)
    for img in soup.select('img[src]'):
        if img['src'].startswith('/'):
            result=client.get(img['src']);result.raise_for_status()
            mime=result.headers.get('content-type','image/svg+xml').split(';')[0]
            img['src']='data:'+mime+';base64,'+base64.b64encode(result.content).decode()
    for frame in soup.select('iframe[src]'):
        match=re.search(r'/fixtures/(orbital|meadow)/index.html',frame['src'])
        if match:
            folder=ROOT/'packages/test-fixtures/games'/match[1]
            html=(folder/'index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(folder/'style.css').read_text()+'</style>')
            html=html.replace('<script src="game.js" defer></script>','<script>'+(folder/'game.js').read_text()+'</script>')
            frame['srcdoc']=html;del frame['src']
    return str(soup)


def main():
    output = ROOT / 'evidence/ui'
    output.mkdir(parents=True, exist_ok=True)
    report = {'kind': 'static-http-screenshots', 'http_or_csp_test': True,
              'source_commit': os.environ.get('GITHUB_SHA'), 'result': 'not_run', 'pages': []}
    cases = [(1440, 1050, '/en/', 'home-desktop'),
             (390, 844, '/fr/', 'home-mobile'),
             (768, 1024, '/fr/', 'home-tablet'),
             (1440, 1050, '/en/leaderboard/', 'leaderboard-desktop'),
             (1440, 1050, '/en/arena/', 'arena-desktop'),
             (390, 844, '/fr/arena/', 'arena-mobile')]
    with tempfile.TemporaryDirectory(prefix='gdb-visual-http-') as temporary:
        destination = build(output=Path(temporary) / 'site')
        headers = json.loads((ROOT / 'vercel.json').read_text())['headers'][0]['headers']
        class Handler(SimpleHTTPRequestHandler):
            def end_headers(self):
                for header in headers:
                    self.send_header(header['key'], header['value'])
                super().end_headers()
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0),
                                     functools.partial(Handler, directory=str(destination)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=shutil.which('chromium'), headless=True)
                try:
                    for width, height, route, name in cases:
                        context = browser.new_context(viewport={'width': width, 'height': height})
                        try:
                            page = context.new_page()
                            errors = []
                            page.on('pageerror', lambda error: errors.append(str(error)))
                            response = page.goto(origin + route, wait_until='networkidle')
                            assert response and response.status == 200
                            expect(page.locator('h1')).to_be_visible()
                            if 'arena' in name:
                                for side in ('a', 'b'):
                                    frame = page.frame_locator('#game-' + side)
                                    expect(frame.locator('canvas')).to_be_visible()
                                    frame.get_by_test_id('start').click()
                                    expect(frame.get_by_test_id('state')).to_have_text('running')
                            page.screenshot(path=str(output / (name + '.png')), full_page=True)
                            row = {'name': name, 'width': width,
                                   'overflow': page.evaluate('document.documentElement.scrollWidth > innerWidth'),
                                   'broken_images': page.evaluate('Array.from(document.images).filter(x => !x.complete || x.naturalWidth === 0).length'),
                                   'page_errors': errors.copy()}
                            report['pages'].append(row)
                            print(json.dumps(row), flush=True)
                            assert not row['overflow'] and not row['broken_images'] and not errors, row
                            if name == 'home-desktop':
                                page.locator('.theme-toggle').click()
                                expect(page.locator('html')).to_have_attribute('data-theme', 'light')
                                page.screenshot(path=str(output / 'home-light.png'), full_page=True)
                        finally:
                            context.close()
                    report['result'] = 'passed'
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            (output / 'visual-checks.json').write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    main()
