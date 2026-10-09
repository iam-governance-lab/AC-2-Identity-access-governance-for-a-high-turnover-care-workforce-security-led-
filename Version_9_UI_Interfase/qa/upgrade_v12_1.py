"""Run with --baseline /path/to/v11 to verify an isolated database upgrade."""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as d:
 env={**os.environ,'SUNHAVEN_DB_PATH':str(Path(d)/'upgrade.db'),'SUNHAVEN_SEED_DEMO':'1','SUNHAVEN_DEMO_PROFILE':'standard'}
 def run(where,code):
  r=subprocess.run([sys.executable,'-c',code],cwd=where/'portal',env=env,text=True,capture_output=True,check=True);return json.loads(r.stdout)
 code="import database,json;database.init_db();c=database.connect();print(json.dumps([list(r) for r in c.execute('SELECT employee_id,name,email FROM employees ORDER BY employee_id')]))"
 before=run(a.baseline.resolve(),code);after=run(root,code)
 assert before==after and len(after)==42
 again=run(root,code);assert again==after
 verified=run(root,"import json,sqlite3,config;from security_workstream import ledger;ledger.sync();c=sqlite3.connect(config.DB_PATH);assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall();print(json.dumps(ledger.verify()))")
 assert verified['status']=='PASS'
 result={'status':'PASS','baseline':'v11','target':'12.1','workers_preserved':len(after),'repeat_migration':'PASS','integrity':'ok','foreign_key_errors':0,'ledger':verified}
 out=root/'evidence/v12_1/upgrade.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2));print(json.dumps(result))
