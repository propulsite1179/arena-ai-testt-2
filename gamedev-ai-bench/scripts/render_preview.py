"""Trusted component screenshots. Real HTTP/CSP checks live in e2e.py."""
from pathlib import Path
import base64
import json
import re
import shutil
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from gamedev.web.app import create_app
from gamedev.config import ROOT, Settings


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
    output=ROOT/'evidence/ui';output.mkdir(parents=True,exist_ok=True)
    report={'kind':'trusted-component-screenshots','http_or_csp_test':False,'pages':[]}
    cases=[(1440,1050,'/en','home-desktop'),(390,844,'/fr','home-mobile'),
           (768,1024,'/fr','home-tablet'),(1440,1050,'/en/leaderboard','leaderboard-desktop'),
           (1440,1050,'/en/arena','arena-desktop')]
    with tempfile.TemporaryDirectory(prefix='gdb-visual-') as temporary:
        temp=Path(temporary)
        settings=Settings(data_dir=temp/'data',database_url='sqlite:///'+str(temp/'visual.db'),secret='trusted-local-visual-test-only-'+'x'*48)
        app=create_app(settings)
        try:
            with TestClient(app) as client,sync_playwright() as pw:
                for width,height,path,name in cases:
                    # Isolate renderer lifetimes: animated Canvas fixtures must not
                    # inherit resources from previous screenshot pages.
                    browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
                    try:
                        page=browser.new_page(viewport={'width':width,'height':height});errors=[]
                        page.on('pageerror',lambda error:errors.append(str(error)))
                        page.set_content(inline_document(client,path),wait_until='load')
                        page.wait_for_timeout(250)
                        overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')
                        page.screenshot(path=str(output/(name+'.png')),full_page=True)
                        row={'name':name,'width':width,'overflow':overflow,'page_errors':errors.copy()}
                        report['pages'].append(row);print(json.dumps(row))
                        assert not overflow and not errors,row
                        if name=='home-desktop':
                            page.locator('.theme-toggle').click()
                            assert page.locator('html').get_attribute('data-theme')=='light'
                            page.screenshot(path=str(output/'home-light.png'),full_page=True)
                    finally:browser.close()
        finally:
            app.state.db.engine.dispose()
            (output/'visual-checks.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
