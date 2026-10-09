"""Verify offline backup and a restore rehearsal in a separate temporary directory."""
from pathlib import Path
import os,sys,tempfile,subprocess,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'portal'))
import config,database,audit
from security_workstream import ledger
with tempfile.TemporaryDirectory(prefix='sunhaven-backup-qa-') as td:
 config.DB_PATH=Path(td)/'source.db';database.init_db();audit.record('SC1005',None,'BACKUP_REHEARSAL','PASS',{})
 target=Path(td)/'restored.db'
 env={**os.environ,'SUNHAVEN_DB_PATH':str(config.DB_PATH)}
 result=subprocess.run([sys.executable,'manage.py','backup',str(target)],cwd=ROOT/'portal',env=env,capture_output=True,text=True,check=True)
 config.DB_PATH=target
 with database.connect() as c:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  assert c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]==42
  assert c.execute("SELECT COUNT(*) FROM audit_events WHERE action='BACKUP_REHEARSAL'").fetchone()[0]==1
 state=ledger.verify();assert state['status']=='PASS'
 print(json.dumps({'backup_and_restore_rehearsal':'PASS','database_integrity':'ok','workers_restored':42,'audit_marker_restored':True,'ledger':state['status'],'mode':'offline; writers stopped; separate temporary restore target'},indent=2))
