"""Real in-process worker timing test on a disposable database, one writer process."""
from pathlib import Path
import tempfile,os,sys,subprocess,time,sqlite3,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'portal'))
import config,database,release_v12 as v
from security_workstream import ledger
with tempfile.TemporaryDirectory(prefix='sunhaven-v12-scheduler-') as td:
 config.DB_PATH=Path(td)/'test.db';config.DEMO_PROFILE='standard';database.init_db()
 rid=v.request_access('SC1001','learning',60,'Real scheduler acceptance test learning access');v.decide_access('SC1002',rid,'Approved','Independent scheduler acceptance approval')
 env={**os.environ,'SUNHAVEN_DB_PATH':str(config.DB_PATH),'SUNHAVEN_PORT':'8032','SUNHAVEN_HOST':'127.0.0.1','SUNHAVEN_DEMO_PROFILE':'standard','SUNHAVEN_QUEUE_INTERVAL':'15','SUNHAVEN_QUEUE_ACTOR':'SC1005','SUNHAVEN_AUTH_MODE':'local','SUNHAVEN_GRAPH_MODE':'mock','SUNHAVEN_ENV':'development'}
 proc=subprocess.Popen([sys.executable,'run.py'],cwd=ROOT/'portal',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 started=time.monotonic();observed=0
 try:
  while time.monotonic()-started<23:
   if proc.poll() is not None:raise RuntimeError('Scheduler test server stopped unexpectedly.')
   with sqlite3.connect(config.DB_PATH) as c:
    row=c.execute("SELECT enabled FROM observed_entitlements WHERE employee_id='SC1001' AND entitlement='learning'").fetchone()
   if row and row[0]:observed=1;break
   time.sleep(.2)
 finally:proc.terminate();proc.wait(timeout=5)
 assert observed,'Background delivery did not run'
 verification=ledger.verify();assert verification['status']=='PASS'
 result={'scenario':'Opt-in scheduler delivers approved permission without HTTP process action','result':'PASS','configured_interval_seconds':15,'observed_delivery_seconds':round(time.monotonic()-started,2),'ledger':'PASS','database':'Disposable fixture; one active writer process'}
 (ROOT/'evidence/v12/scheduler.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
