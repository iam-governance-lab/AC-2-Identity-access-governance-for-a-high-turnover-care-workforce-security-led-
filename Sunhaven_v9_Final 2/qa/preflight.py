"""Dependency-free release checks. No changes to the user's existing database."""
from pathlib import Path
import sys,tempfile,json,hashlib,sqlite3,platform,subprocess
ROOT=Path(__file__).resolve().parents[1]
if sys.version_info<(3,12):raise SystemExit('Python 3.12 or newer is required.')
sys.path.insert(0,str(ROOT/'portal'))
import config,database,auth,assurance

def main():
 original=json.loads((ROOT/'ORIGINAL_MANIFEST.json').read_text())['files']
 mismatches=[x['path'] for x in original if not (ROOT/'original'/x['path']).is_file() or hashlib.sha256((ROOT/'original'/x['path']).read_bytes()).hexdigest()!=x['sha256']]
 with tempfile.TemporaryDirectory(prefix='sunhaven-preflight-') as td:
  config.DB_PATH=Path(td)/'test.db';config.SEED_DEMO=True;database.init_db()
  with database.connect() as c:
   counts={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('employees','residents','work_notes','qualifications','sites','teams')}
   integrity=c.execute('PRAGMA integrity_check').fetchone()[0];fk=list(c.execute('PRAGMA foreign_key_check'))
   login=auth.employment_valid(c.execute("SELECT * FROM employees WHERE employee_id='SC1005'").fetchone())
   schema_count=c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
  checks={'python':platform.python_version(),'fresh_seed':counts,'database_tables':schema_count,'database_integrity':integrity,'foreign_key_errors':len(fk),'demo_operator_ready':login,'original_files_verified':len(original),'original_mismatches':mismatches,'status':'PASS' if integrity=='ok' and not fk and login and not mismatches else 'FAIL'}
  print(json.dumps(checks,indent=2));return int(checks['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
