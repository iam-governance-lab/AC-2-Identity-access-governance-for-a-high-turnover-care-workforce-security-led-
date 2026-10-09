from clock import utc_today
"""Transactional governance controls for the local/mock directory."""
from datetime import datetime, timezone, timedelta, date
import json
import secrets
import database

SCHEMA = '''
CREATE TABLE IF NOT EXISTS request_snapshots (
 request_id INTEGER PRIMARY KEY REFERENCES access_requests(request_id),
 role_before TEXT NOT NULL, facility_before TEXT NOT NULL,
 executed_by TEXT, executed_at TEXT
);
CREATE TABLE IF NOT EXISTS review_closures (
 review_id INTEGER PRIMARY KEY REFERENCES access_reviews(review_id),
 closed_by TEXT NOT NULL, evidence TEXT NOT NULL, closed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS remediation_tasks (
 task_id INTEGER PRIMARY KEY AUTOINCREMENT,
 employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 title TEXT NOT NULL, priority TEXT NOT NULL, owner_id TEXT NOT NULL REFERENCES employees(employee_id),
 status TEXT NOT NULL DEFAULT 'Open', evidence TEXT,
 created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
'''

def now():return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds')

def require(conn, actor, roles):
    row=conn.execute("SELECT * FROM employees WHERE employee_id=? AND status='Active' AND cloud_enabled=1",(actor,)).fetchone()
    actual={r[0] for r in conn.execute('SELECT role FROM employee_roles WHERE employee_id=?',(actor,))}
    import auth
    if not auth.employment_valid(row) or not actual.intersection(roles) or conn.execute('SELECT 1 FROM blocked_users WHERE employee_id=?',(actor,)).fetchone():
        raise PermissionError('Your current role cannot perform this operation.')

def event(conn,actor,target,action,details):
    import audit
    return audit.record_on(conn,actor,target,action,'PASS',details,correlation_id='GOV-'+secrets.token_hex(8).upper())

def reason(value):
    value=(value or '').strip()
    if not 10<=len(value)<=2000:raise ValueError('Provide a reason or evidence of 10 to 2,000 characters.')
    return value

def execute_request(rid,actor):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');require(c,actor,{'IAMOperator'})
        r=c.execute('SELECT * FROM access_requests WHERE request_id=?',(rid,)).fetchone()
        s=c.execute('SELECT * FROM request_snapshots WHERE request_id=?',(rid,)).fetchone()
        if not r or r['status']!='Approved' or not s or s['executed_at']:raise ValueError('An unexecuted approval from version 3 is required.')
        if r['employee_id']==actor or r['decision_by']==r['employee_id']:raise PermissionError('An operator cannot execute their own access request.')
        approved=datetime.fromisoformat(r['decided_at'])
        if datetime.now(timezone.utc).replace(tzinfo=None)-approved>timedelta(days=7):raise ValueError('Approval expired after seven days. Submit a new request.')
        require(c,r['decision_by'],{'IAMOperator'} if r['requested_role']=='IAMOperator' else {'Manager','IAMOperator'})
        e=c.execute('SELECT * FROM employees WHERE employee_id=?',(r['employee_id'],)).fetchone()
        if e['status']!='Active' or not e['cloud_enabled'] or c.execute('SELECT 1 FROM blocked_users WHERE employee_id=?',(e['employee_id'],)).fetchone():raise ValueError('Target worker is no longer active.')
        if e['worker_type']=='Agency' and (not e['end_date'] or e['end_date']<utc_today().isoformat()):raise ValueError('Agency contract is expired or incomplete.')
        if e['approved_role']!=s['role_before'] or e['facility']!=s['facility_before']:raise ValueError('Worker role or facility changed since approval. Obtain a new approval.')
        import assurance
        if r['requested_role']!='IAMOperator':assurance.protect_operator(c,actor,e['employee_id'])
        c.execute('DELETE FROM employee_roles WHERE employee_id=?',(e['employee_id'],))
        c.execute('UPDATE assignments SET active=0 WHERE employee_id=?',(e['employee_id'],))
        c.execute('DELETE FROM sessions WHERE employee_id=?',(e['employee_id'],))
        c.execute('INSERT INTO employee_roles VALUES (?,?)',(e['employee_id'],r['requested_role']))
        c.execute('UPDATE employees SET approved_role=?,cloud_role=?,facility=?,admin_privilege=?,updated_at=? WHERE employee_id=?',(r['requested_role'],r['requested_role'],r['facility'],int(r['requested_role']=='IAMOperator'),now(),e['employee_id']))
        assurance.sync_team(c,e['employee_id'],r['facility'])
        c.execute("UPDATE access_requests SET status='Implemented' WHERE request_id=?",(rid,))
        c.execute('UPDATE request_snapshots SET executed_by=?,executed_at=? WHERE request_id=?',(actor,now(),rid))
        return event(c,actor,e['employee_id'],'APPROVED_MOVER_EXECUTED',{'request_id':rid,'role':r['requested_role'],'facility':r['facility']})

def operate(action,d,actor):
    if action=='execute':return execute_request(d.get('request_id'),actor)
    why=reason(d.get('reason'))
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        require(c,actor,{'IAMOperator'} if action in ('assign','unassign','revoke') else {'Manager','IAMOperator'})
        eid=d.get('employee_id')
        if action in ('assign','unassign','revoke','task'):
            e=c.execute('SELECT * FROM employees WHERE employee_id=?',(eid,)).fetchone()
            if not e:raise ValueError('Worker was not found.')
        if action in ('assign','unassign'):
            r=c.execute('SELECT * FROM residents WHERE resident_id=?',(d.get('resident_id'),)).fetchone()
            if not r:raise ValueError('Resident was not found.')
            if action=='assign':
                if e['status']!='Active' or not e['cloud_enabled'] or e['approved_role'] not in ('Nurse','CareWorker','AgencyWorker') or not c.execute('SELECT 1 FROM employee_roles WHERE employee_id=? AND role=?',(eid,e['approved_role'])).fetchone() or e['facility']!=r['facility']:raise ValueError('Assignment requires an active care role in the same facility.')
                if c.execute('SELECT 1 FROM blocked_users WHERE employee_id=?',(eid,)).fetchone() or (e['worker_type']=='Agency' and (not e['end_date'] or e['end_date']<utc_today().isoformat())):raise ValueError('Worker access is blocked or expired.')
                c.execute('INSERT INTO assignments(employee_id,resident_id,active) VALUES (?,?,1) ON CONFLICT(employee_id,resident_id) DO UPDATE SET active=1',(eid,r['resident_id']))
            else:c.execute('UPDATE assignments SET active=0 WHERE employee_id=? AND resident_id=?',(eid,r['resident_id']))
        elif action=='revoke':c.execute('DELETE FROM sessions WHERE employee_id=?',(eid,))
        elif action=='task':
            if d.get('priority') not in ('Low','Medium','High','Critical'):raise ValueError('Select a valid priority.')
            require(c,d.get('owner_id'),{'Manager','IAMOperator'})
            title=(d.get('title') or '').strip()
            if not 5<=len(title)<=120:raise ValueError('Task title must contain 5 to 120 characters.')
            c.execute('INSERT INTO remediation_tasks(employee_id,title,priority,owner_id,evidence,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',(eid,title,d['priority'],d['owner_id'],why,actor,now(),now()))
        elif action=='task_update':
            t=c.execute('SELECT * FROM remediation_tasks WHERE task_id=?',(d.get('task_id'),)).fetchone()
            if not t:raise ValueError('Task was not found.')
            if d.get('status') not in ('Open','In progress','Resolved'):raise ValueError('Invalid task status.')
            eid=t['employee_id']
            c.execute('UPDATE remediation_tasks SET status=?,evidence=?,updated_at=? WHERE task_id=?',(d['status'],why,now(),t['task_id']))
        elif action=='close_review':
            r=c.execute('SELECT * FROM access_reviews WHERE review_id=?',(d.get('review_id'),)).fetchone()
            if not r or r['remediation_status']!='Pending':raise ValueError('A pending review is required.')
            eid=r['employee_id']
            if r['decision']=='Remove':
                e=c.execute('SELECT * FROM employees WHERE employee_id=?',(eid,)).fetchone()
                if e['cloud_enabled'] or c.execute('SELECT 1 FROM employee_roles WHERE employee_id=?',(eid,)).fetchone() or c.execute('SELECT 1 FROM assignments WHERE employee_id=? AND active=1',(eid,)).fetchone():raise ValueError('Remove access before closing this review.')
            c.execute("UPDATE access_reviews SET remediation_status='Closed' WHERE review_id=?",(r['review_id'],))
            c.execute('INSERT INTO review_closures VALUES (?,?,?,?)',(r['review_id'],actor,why,now()))
        else:raise ValueError('Unknown operation.')
        return event(c,actor,eid,'GOV_'+action.upper(),{'reason':why,'resident_id':d.get('resident_id'),'task_id':d.get('task_id'),'review_id':d.get('review_id'),'status':d.get('status')})
