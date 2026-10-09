from clock import utc_today
"""Idempotent, reviewed local agency-expiry enforcement in mock directory mode."""
from datetime import date,timedelta
import hashlib,json
import config,database,governance
from security_workstream import ledger

SCHEMA='''
CREATE TABLE IF NOT EXISTS automation_runs (
 run_id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_at TEXT NOT NULL, actor_id TEXT NOT NULL, action TEXT NOT NULL,
 target_count INTEGER NOT NULL, target_ids TEXT NOT NULL, reason TEXT NOT NULL
);
'''

def _targets(conn,today):
    return conn.execute("""SELECT employee_id,name,facility,end_date FROM employees
      WHERE status='Active' AND worker_type='Agency' AND end_date IS NOT NULL
        AND end_date < ? ORDER BY employee_id""",(today,)).fetchall()

def _fingerprint(rows):
    return hashlib.sha256(json.dumps([(r['employee_id'],r['end_date']) for r in rows],separators=(',',':')).encode()).hexdigest()

def preview(today=None):
    today=today or utc_today()
    if not isinstance(today,date):raise ValueError('today must be a date')
    with database.connect() as conn:
        candidates=[dict(r) for r in _targets(conn,today.isoformat())]
        upcoming=[dict(r) for r in conn.execute("""SELECT employee_id,name,facility,end_date FROM employees
          WHERE worker_type='Agency' AND status='Active' AND end_date BETWEEN ? AND ? ORDER BY end_date""",
          (today.isoformat(),(today+timedelta(days=14)).isoformat())).fetchall()]
        history=[dict(r) for r in conn.execute('SELECT * FROM automation_runs ORDER BY run_id DESC LIMIT 10').fetchall()]
    return {'as_of':today.isoformat(),'expired':candidates,'upcoming':upcoming,
      'fingerprint':_fingerprint(candidates),'history':history}

def execute(actor,expected_fingerprint,reason,today=None):
    """Only mock directory: disable expired agency access, record all changes atomically."""
    if config.GRAPH_MODE!='mock':raise RuntimeError('Automation requires the simulated directory.')
    today=today or utc_today()
    why=governance.reason(reason)
    if not isinstance(expected_fingerprint,str) or len(expected_fingerprint)!=64:raise ValueError('Open the current preview before running automation.')
    with database.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        governance.require(conn,actor,{'IAMOperator'})
        targets=_targets(conn,today.isoformat())
        if _fingerprint(targets)!=expected_fingerprint:raise ValueError('The expiry preview changed; review the current list and try again.')
        ids=[r['employee_id'] for r in targets]
        for eid in ids:
            conn.execute("""UPDATE employees SET status='Suspended',cloud_enabled=0,cloud_role=NULL,admin_privilege=0,updated_at=? WHERE employee_id=?""",(governance.now(),eid))
            conn.execute('DELETE FROM employee_roles WHERE employee_id=?',(eid,))
            conn.execute('UPDATE assignments SET active=0 WHERE employee_id=?',(eid,))
            conn.execute('DELETE FROM sessions WHERE employee_id=?',(eid,))
            conn.execute('INSERT INTO blocked_users(employee_id,blocked_at,reason) VALUES (?,?,?) ON CONFLICT(employee_id) DO UPDATE SET blocked_at=excluded.blocked_at,reason=excluded.reason',(eid,governance.now(),'Agency contract expired; automated local disable'))
            governance.event(conn,actor,eid,'AGENCY_EXPIRY_ENFORCED',{'end_date':next(r['end_date'] for r in targets if r['employee_id']==eid),'reason':why,'directory':'mock'})
        conn.execute('INSERT INTO automation_runs(run_at,actor_id,action,target_count,target_ids,reason) VALUES (?,?,?,?,?,?)',
            (governance.now(),actor,'AGENCY_EXPIRY',len(ids),json.dumps(ids),why))
        if not ids:governance.event(conn,actor,None,'AGENCY_EXPIRY_NOOP',{'reason':why})
    return ids
