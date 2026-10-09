from pathlib import Path
import json,re,subprocess,sys
import database,enterprise,governance
from security_workstream import ledger
ROOT=Path(__file__).resolve().parents[1]/'original'
def run(actor,kind,data=None):
    data=data or {}
    with database.connect() as c:
        enterprise.require(c,actor,{'Manager','IAMOperator'})
        if kind=='sitas':payload={'workers':[dict(r) for r in c.execute('SELECT * FROM employees ORDER BY employee_id')]}
        elif kind=='saif':
            payload={k:enterprise.clean(data.get(k),1,120) for k in ('workerId','displayName','email','agencyId')}
            if not re.fullmatch(r'[A-Za-z0-9._-]{1,40}',payload['workerId']):raise ValueError('Worker ID must use letters, numbers, dots, dashes or underscores.')
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',payload['email']):raise ValueError('Enter a valid synthetic email.')
            payload['email']=payload['email'].lower()
        else:raise ValueError('Unknown integration.')
    proc=subprocess.run([sys.executable,str(Path(__file__).with_name('integration_worker.py')),kind],input=json.dumps(payload),capture_output=True,text=True,timeout=20)
    if proc.returncode:raise ValueError('Original module could not complete. Check local configuration and module tests.')
    result=json.loads(proc.stdout)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        c.execute('INSERT INTO integration_runs(kind,actor_id,created_at,result_json) VALUES (?,?,?,?)',(kind,actor,enterprise.now(),json.dumps(result)))
        governance.event(c,actor,None,'ORIGINAL_MODULE_RUN',{'module':kind,'mode':'read-only'})
    return result

def latest():
    with database.connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM integration_runs ORDER BY id DESC LIMIT 5')]
