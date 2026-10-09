"""Optional browser smoke test: pip install playwright==1.51.0; playwright install chromium."""
from pathlib import Path
import os,sys,time,json,tempfile,subprocess,urllib.request
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];OUT=R/'evidence/final9';checks=[];errors=[]
with tempfile.TemporaryDirectory() as d:
 env={**os.environ,'SUNHAVEN_DB_PATH':str(Path(d)/'demo.db'),'SUNHAVEN_PORT':'8044','SUNHAVEN_DEMO_PROFILE':'expanded','SUNHAVEN_AUTH_MODE':'local','SUNHAVEN_GRAPH_MODE':'mock','SUNHAVEN_SEED_DEMO':'1'}
 with (OUT/'browser-server.log').open('w') as log:
  proc=subprocess.Popen([sys.executable,'run.py'],cwd=R/'portal',env=env,stdout=log,stderr=log)
  try:
   for i in range(50):
    try:urllib.request.urlopen('http://127.0.0.1:8044/health');break
    except OSError:time.sleep(.1)
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8044/login');page.select_option('select[name=employee_id]','SC1005');page.get_by_role('button',name='Enter demo workspace').click();page.wait_for_url('http://127.0.0.1:8044/')
    for name,path in [('dashboard','/'),('ai-workspace','/ai-workspace'),('team-services','/team-services'),('employees','/employees'),('application-access','/application-access'),('connectors','/connectors')]:
     response=page.goto('http://127.0.0.1:8044'+path);assert response.status==200
     page.screenshot(path=str(OUT/(name+'.png')),full_page=False);checks.append(name+' renders')
    page.goto('http://127.0.0.1:8044/team-services');page.get_by_role('button',name='Analyze synthetic demo').click();page.wait_for_load_state('networkidle');assert 'PROMPT_BURST' in page.locator('main').inner_text();checks.append('MFA demo button and findings');page.screenshot(path=str(OUT/'mfa-findings.png'))
    page.locator('#assistantLauncher').click();page.locator('#assistantQuestion').fill('How do I check security risks?');page.locator('#assistantForm button[type=submit]').click();page.wait_for_function("document.querySelector('#assistantMessages').textContent.includes('Risk') || document.querySelector('#assistantMessages').textContent.includes('risk')")
    page.wait_for_function("!document.querySelector('#assistantForm').hasAttribute('aria-busy')");assert page.locator('#assistantMessages a[href="/insights"]').count()>0;checks.append('Chatbot security-risk routing');page.screenshot(path=str(OUT/'chatbot.png'));page.keyboard.press('Escape')
    for width,height in [(1024,768),(768,1024),(390,844)]:
     page.set_viewport_size({'width':width,'height':height});page.goto('http://127.0.0.1:8044/');page.locator('.menu-toggle').click();page.wait_for_timeout(250)
     box=page.locator('.sidebar').bounding_box();assert box and box['x']>=-1 and box['width']>=250,(width,box)
     assert page.locator('.sidebar').evaluate('(e)=>!e.inert');assert page.locator('main').evaluate('(e)=>e.inert')
     page.screenshot(path=str(OUT/f'navigation-{width}.png'));page.keyboard.press('Escape');assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='false'
     assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),width
     checks.append(f'{width}px drawer, Escape, no page overflow')
    assert not errors,errors
    result={'status':'PASS','browser':browser.version,'checks':checks,'page_errors':errors};(OUT/'browser-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));browser.close()
  finally:proc.terminate();proc.wait(timeout=5)
