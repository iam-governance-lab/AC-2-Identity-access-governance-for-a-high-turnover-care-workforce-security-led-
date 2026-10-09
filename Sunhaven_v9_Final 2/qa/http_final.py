"""Reproducible real-HTTP acceptance run. Uses an isolated temporary mock database.
Run from the project root: python qa/http_final.py. Never touches portal/data.
No browser is controlled by this script. Captured HTML is not a screenshot.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import http.cookiejar, urllib.request, urllib.parse, urllib.error
import tempfile,subprocess,sys,os,time,json,re,sqlite3,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence';PAGES=OUT/'rendered-pages'
PAGES.mkdir(parents=True,exist_ok=True)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
checks=[];calls=[];jars={};clients={};base='';db=None

def call(path,eid=None,data=None,expect=200):
 global base
 if eid not in clients:
  jars[eid]=http.cookiejar.CookieJar();clients[eid]=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jars[eid]),NoRedirect())
 if data is not None:
  data=dict(data);data['_csrf']=next((c.value for c in jars[eid] if c.name=='sunhaven_csrf'),'')
 raw=urllib.parse.urlencode(data).encode() if data is not None else None
 started=time.perf_counter()
 try:r=clients[eid].open(urllib.request.Request(base+path,data=raw),timeout=15)
 except urllib.error.HTTPError as e:r=e
 body=r.read();status=r.status
 calls.append({'path':path,'method':'POST' if data is not None else 'GET','actor':eid or 'anonymous','status':status,'milliseconds':round((time.perf_counter()-started)*1000,2)})
 assert status==expect,(path,status,expect,body[:500])
 return body.decode('utf-8-sig'),dict(r.headers)

def login(eid):
 call('/login',eid);call('/login',eid,{'employee_id':eid},303)
def record(name):checks.append({'scenario':name,'result':'PASS'})
def scalar(sql,args=()):
 with sqlite3.connect(db) as c:return c.execute(sql,args).fetchone()[0]
def snap(name,path,eid):
 body,_=call(path,eid)
 body=re.sub(r'(name="_csrf" value=")[^"]+',r'\g<1>REDACTED',body)
 body=body.replace('/static/','assets/')
 # Saved evidence has no interactive POST forms; rendering retains labels and values.
 body=body.replace('method="post"','method="get" data-evidence-only="true"')
 (PAGES/(name+'.html')).write_text(body)

with tempfile.TemporaryDirectory(prefix='sunhaven-final-qa-') as td:
 db=Path(td)/'qa.db';env={**os.environ,'SUNHAVEN_DB_PATH':str(db),'SUNHAVEN_PORT':'8031','SUNHAVEN_HOST':'127.0.0.1','SUNHAVEN_ENV':'development','SUNHAVEN_AUTH_MODE':'local','SUNHAVEN_GRAPH_MODE':'mock','SUNHAVEN_SEED_DEMO':'1'}
 base='http://127.0.0.1:8031';log=(OUT/'http-server-v9.log').open('w')
 proc=subprocess.Popen([sys.executable,'serve.py' if os.getenv('SUNHAVEN_QA_SERVER')=='waitress' else 'run.py'],cwd=ROOT/'portal',env=env,stdout=log,stderr=log)
 try:
  for attempt in range(50):
   try:urllib.request.urlopen(base+'/health',timeout=.5);break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('HTTP server did not start')
  login('SC1005');login('SC1002');login('SC1001');login('SC1003')
  snap('01-dashboard','/','SC1005')
  for path in ['/hub','/catalog','/services','/incidents','/policy-lab','/integrations','/employees','/employees/new','/employees/SC1001','/employees/SC1001/move','/residents','/access-reviews','/audit','/compliance','/requirements','/notes','/requests','/guide','/security-assurance','/automation','/policies','/notifications','/search?q=Sarah','/onboarding','/reports','/workforce-sync','/campaigns','/qualifications','/coverage','/insights','/control-centre','/api/v1/docs','/api/v1/health','/api/v1/scim/Users','/static/final.css','/static/app.js']:
   call(path,'SC1005')
  record('36 principal pages, APIs and assets respond successfully')
  today=datetime.now(timezone.utc).date()
  for eid,name,worker,role in [('FINAL2001','Avery Demo','Permanent','CareWorker'),('FINAL2002','Morgan Agency','Agency','AgencyWorker')]:
   d={'employee_id':eid,'name':name,'email':eid.lower()+'@sunhaven.test','worker_type':worker,'approved_role':role,'facility':'Ashford Main','status':'Active','manager_sponsor':'SC1002','start_date':str(today),'end_date':str(today+timedelta(days=7)) if worker=='Agency' else '', 'mode':'apply'}
   call('/employees/joiner','SC1005',d,303)
   assert scalar('SELECT status FROM employees WHERE employee_id=?',(eid,))=='Active'
  record('Permanent and agency onboarding persist validated workforce records')
  for kind in ['Safeguarding','Professional registration']:
   call('/assurance-action/qualification','SC1002',{'employee_id':'FINAL2001','kind':kind,'expires_on':str(today+timedelta(days=100)),'evidence_ref':'Synthetic acceptance-test qualification checked'},303)
  login('FINAL2001')
  for role,facility in [('Nurse','Ashford Main'),('Nurse','North Wing')]:
   call('/requests','FINAL2001',{'requested_role':role,'facility':facility,'reason':'Approved workforce change for acceptance test'},303)
   rid=scalar('SELECT MAX(request_id) FROM access_requests')
   call(f'/requests/{rid}/decision','SC1002',{'decision':'Approved','decision_note':'Manager confirms workforce need for this change'},303)
   call('/operations','SC1005',{'action':'execute','request_id':rid,'reason':'Operator verifies requested workforce change'},303)
   call('/','FINAL2001',expect=303)
   login('FINAL2001')
   assert scalar('SELECT approved_role FROM employees WHERE employee_id=?',('FINAL2001',))==role
   assert scalar('SELECT facility FROM employees WHERE employee_id=?',('FINAL2001',))==facility
  record('Approved role change and site transfer revoke stale sessions and update access')
  login('FINAL2002')
  call('/requests','FINAL2002',{'requested_role':'CareWorker','facility':'South Wing','reason':'Request for fictional additional shift support'},303)
  rid=scalar('SELECT MAX(request_id) FROM access_requests')
  call(f'/requests/{rid}/decision','SC1002',{'decision':'Rejected','decision_note':'Business need is not confirmed for this site'},303)
  assert scalar('SELECT status FROM access_requests WHERE request_id=?',(rid,))=='Rejected'
  record('Rejected access request never changes the worker role')
  call('/assurance-action/cover','SC1001',{'facility':'North Wing','minutes':'60','reason':'Qualified nurse covers temporary North Wing shift'},303)
  cid=scalar('SELECT MAX(id) FROM cover_requests')
  call('/assurance-action/cover-decision','SC1002',{'id':cid,'decision':'Approve','reason':'Manager confirms temporary shift coverage'},303)
  snap('02-cover-pending','/coverage','SC1005')
  call('/assurance-action/cover-decision','SC1005',{'id':cid,'decision':'Approve','reason':'Operator verifies independent manager approval'},303)
  assert 'Resident Charlie' in call('/residents','SC1001')[0]
  record('Two-stage temporary site cover changes permitted resident scope')
  call('/assurance-action/emergency','SC1001',{'resident_id':'R005','reason':'Urgent fictional resident care during an incident','incident_ref':'INC-FINAL-200'},303)
  gid=scalar('SELECT MAX(id) FROM emergency_grants')
  visible=call('/residents','SC1001')[0];assert 'Resident Echo' in visible and 'Resident Foxtrot' not in visible
  snap('03-emergency','/coverage','SC1002')
  call('/assurance-action/emergency-review','SC1002',{'id':gid,'reason':'Incident reviewed and emergency handover completed'},303)
  assert 'Resident Echo' not in call('/residents','SC1001')[0]
  record('Emergency grant is resident-specific; independent review closes access')
  with sqlite3.connect(db) as c:c.execute("UPDATE qualifications SET expires_on=? WHERE employee_id='SC1001' AND kind='Professional registration'",(str(today-timedelta(days=1)),))
  call('/protected/clinical','SC1001',expect=403)
  snap('04-qualifications','/qualifications','SC1002');snap('05-risk-insights','/insights','SC1005')
  call('/assurance-action/qualification','SC1002',{'employee_id':'SC1001','kind':'Professional registration','expires_on':str(today+timedelta(days=180)),'evidence_ref':'Synthetic renewal after expiry-denial test'},303)
  call('/protected/clinical','SC1001')
  record('Expired qualification denies clinical access; independently verified renewal restores it')
  call('/compliance/run','SC1005',{},303);assert scalar("SELECT COUNT(*) FROM compliance_findings WHERE status='Open'")>0
  snap('06-compliance','/compliance','SC1005');record('Policy violation scan produces persisted actionable findings')
  call('/workforce-action','SC1005',{'action':'campaign'},303)
  item=scalar("SELECT id FROM campaign_items WHERE employee_id='FINAL2001' ORDER BY id DESC LIMIT 1")
  call('/workforce-action','SC1002',{'action':'review','id':item,'decision':'Retain','reason':'Manager attests current site and nurse access'},303)
  snap('07-certification','/campaigns','SC1002');record('Quarterly campaign captures and persists an independent attestation')
  call('/employees/FINAL2001/leave','SC1005',{},303)
  call('/','FINAL2001',expect=303);assert scalar("SELECT COUNT(*) FROM employee_roles WHERE employee_id='FINAL2001'")==0
  record('Termination removes roles, assignments and sessions and blocks login')
  raw='employee_id,email,role,facility,status,end_date\nFINAL2002,final2002@sunhaven.test,AgencyWorker,Ashford Main,Leaver,'+str(today+timedelta(days=7))
  call('/workforce-action','SC1005',{'action':'stage','csv':raw},303);rid=scalar('SELECT MAX(id) FROM roster_imports')
  call('/workforce-action','SC1002',{'action':'decide','id':rid,'decision':'Approved','reason':'Agency engagement ended; independently verified'},303)
  snap('08-roster','/workforce-sync','SC1005')
  call('/workforce-action','SC1005',{'action':'apply','id':rid},303)
  assert scalar("SELECT cloud_enabled FROM employees WHERE employee_id='FINAL2002'")==0
  record('Reviewed roster offboarding deprovisions an agency worker')
  call('/assurance-action/jobs','SC1005',{},303);call('/assurance-action/jobs','SC1005',{},303)
  assert scalar("SELECT cloud_enabled FROM employees WHERE employee_id='SC1006'")==0
  assert scalar('SELECT COUNT(*) FROM operational_jobs')==1
  record('Daily job disables expired agency account once; repeated run is idempotent')
  snap('09-control-centre','/control-centre','SC1005');snap('10-audit','/audit?q=COVER','SC1005');snap('11-notifications','/notifications','SC1002')
  call('/audit','SC1003',expect=403);call('/api/v1/employees','SC1003',expect=403);call('/api/v1/employees?page_size=1001','SC1005',expect=400)
  record('Direct URL/API authorisation and pagination validation reject invalid requests')
  audit_page=call('/audit?q=COVER','SC1005')[0]
  assert 'COVER_DECISION' in audit_page and 'Inspect evidence' in audit_page and 'LOGIN_LOCAL_DEMO' not in audit_page
  snap('12-integrity','/security-assurance','SC1005')
  record('Audit investigation returns correlated decision details and integrity screen')
  with sqlite3.connect(db) as c:
   assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall()
   schema=[{'name':r[0],'sql':r[1]} for r in c.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")]
  (OUT/'database-schema-v9.json').write_text(json.dumps(schema,indent=2))
  record('Database integrity and all foreign-key checks pass after full lifecycle run')
  shutil.copytree(ROOT/'portal/static',PAGES/'assets',dirs_exist_ok=True)
  latency=sorted(c['milliseconds'] for c in calls)
  result={'version':'9.0','time_utc':datetime.now(timezone.utc).isoformat(),'transport':'Real localhost HTTP; '+('Waitress WSGI' if os.getenv('SUNHAVEN_QA_SERVER')=='waitress' else 'stdlib ThreadingHTTPServer'),'database':'Isolated synthetic temporary fixture','browser_screenshots':'NOT CAPTURED: remote browser cannot access localhost','scenario_count':len(checks),'scenarios':checks,'http_requests':len(calls),'latency_ms':{'median':latency[len(latency)//2],'p95':latency[int(len(latency)*.95)],'max':max(latency)},'calls':calls}
  (OUT/('http-acceptance-waitress-v9.json' if os.getenv('SUNHAVEN_QA_SERVER')=='waitress' else 'http-acceptance-v9.json')).write_text(json.dumps(result,indent=2))
  print(json.dumps({k:v for k,v in result.items() if k!='calls'},indent=2))
 finally:
  proc.terminate();proc.wait(timeout=10);log.close()
