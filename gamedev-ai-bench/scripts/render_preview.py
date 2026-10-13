"""Visual component rendering without bypassing browser network policy.

HTTP navigation is deliberately not used in this environment. Assets are loaded
from our own application via TestClient and inlined into Playwright set_content.
This is NOT a browser network end-to-end test and does not validate CSP delivery.
"""
from pathlib import Path
import base64
import re
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from gamedev.web.app import create_app
from gamedev.config import ROOT


def inline_document(client,path,include_app_script=True):
    response=client.get(path);response.raise_for_status()
    soup=BeautifulSoup(response.text,'html.parser')
    for tag in list(soup.select('link[rel=stylesheet]')):
        style=soup.new_tag('style');style.string=client.get(tag['href']).text;tag.replace_with(style)
    for tag in list(soup.select('script[src]')):
        if not include_app_script:tag.decompose();continue
        script=soup.new_tag('script');script.string=client.get(tag['src']).text;tag.decompose();soup.body.append(script)
    for img in soup.select('img[src]'):
        if img['src'].startswith('/'):
            result=client.get(img['src']);mime=result.headers.get('content-type','image/svg+xml').split(';')[0]
            img['src']='data:'+mime+';base64,'+base64.b64encode(result.content).decode()
    for frame in soup.select('iframe[src]'):
        match=re.search(r'/fixtures/(orbital|meadow)/index.html',frame['src'])
        if match:
            folder=ROOT/'packages/test-fixtures/games'/match[1]
            html=(folder/'index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(folder/'style.css').read_text()+'</style>')
            html=html.replace('<script src="game.js" defer></script>','<script>'+(folder/'game.js').read_text()+'</script>')
            frame['srcdoc']=html;del frame['src']
    # set_content runs under about:blank. Absolute URLs below stay intercepted in
    # component tests; ordinary navigation should be tested by scripts/e2e.py.
    return str(soup)


def main():
    app=create_app();output=ROOT/'evidence/ui';output.mkdir(parents=True,exist_ok=True)
    with TestClient(app) as client,sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
        for viewport,path,name in [({'width':1440,'height':1050},'/en','home-desktop'),({'width':390,'height':844},'/fr','home-mobile'),
            ({'width':1440,'height':1050},'/en/leaderboard','leaderboard-desktop'),({'width':1440,'height':1050},'/en/arena','arena-desktop')]:
            page=browser.new_page(viewport=viewport);errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_content(inline_document(client,path),wait_until='load');page.wait_for_timeout(250)
            page.screenshot(path=str(output/(name+'.png')),full_page=True)
            print(name,'overflow',page.evaluate('document.documentElement.scrollWidth>innerWidth'),'console errors',errors)
            if name=='home-desktop':
                page.locator('.theme-toggle').click();page.screenshot(path=str(output/'home-light.png'),full_page=True)
            page.close()
        browser.close()
if __name__=='__main__':main()
