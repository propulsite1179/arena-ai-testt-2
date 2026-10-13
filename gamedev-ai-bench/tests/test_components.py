"""Trusted local component rendering only; real HTTP journeys live in scripts/e2e.py."""
import os,shutil
import pytest
from playwright.sync_api import sync_playwright,expect
from scripts.render_preview import inline_document
from gamedev.config import ROOT
from gamedev.services.evaluator import evaluate

pytestmark=pytest.mark.skipif(os.getenv('BROWSER_COMPONENT_TESTS')!='true',reason='Opt-in trusted component rendering; not an HTTP E2E test')

@pytest.mark.parametrize('width,height,language', [(1440,960,'en'),(768,1024,'fr'),(390,844,'fr')])
def test_responsive_theme_and_menu(client,width,height,language):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
        page=browser.new_page(viewport={'width':width,'height':height});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_content(inline_document(client,'/'+language),wait_until='load')
        expect(page.locator('h1')).to_be_visible()
        assert page.locator('html').get_attribute('lang')==language
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        page.locator('.theme-toggle').click();expect(page.locator('html')).to_have_attribute('data-theme','light')
        if page.locator('.mobile-toggle').is_visible():
            page.locator('.mobile-toggle').click();expect(page.locator('.mobile-toggle')).to_have_attribute('aria-expanded','true')
            page.keyboard.press('Escape');expect(page.locator('.mobile-toggle')).to_have_attribute('aria-expanded','false')
        assert not errors
        browser.close()

def test_model_filters_are_real(client):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
        page=browser.new_page();page.set_content(inline_document(client,'/en/leaderboard'),wait_until='load')
        page.locator('#model-search').fill('astra');assert page.locator('.model-row:visible').count()==1
        page.locator('#model-search').fill('no-such-catalog-entry');assert page.locator('.model-row:visible').count()==0
        expect(page.locator('#model-empty')).to_be_visible()
        page.locator('#reset-filters').click();assert page.locator('.model-row:visible').count()==8
        browser.close()

def test_internal_fixture_browser_observations(tmp_path):
    result=evaluate(ROOT/'packages/test-fixtures/games/orbital',tmp_path/'evidence',trusted_fixture=True)
    assert len(result['assertions'])==8
    assert all(row['outcome']=='passed' for row in result['assertions']),result
    assert 'in-memory' in result['metrics']['transport']
