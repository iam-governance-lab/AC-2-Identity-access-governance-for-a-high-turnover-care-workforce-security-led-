"""Application entitlements and durable LOCAL connector execution.
No cloud credential or remote write is implied by local delivery success.
"""
from datetime import datetime,timedelta,date
import json

def number(value,label):
    try:return int(value)
    except (ValueError,TypeError):raise ValueError(label+' must be a whole number.')
import auth,assurance,config,database,enterprise,governance,lifecycle

GOV={'Manager','IAMOperator','Auditor'}
SCHEMA='''
CREATE TABLE IF NOT EXISTS app_entitlements (
 key TEXT PRIMARY KEY, application TEXT NOT NULL, name TEXT NOT NULL, roles TEXT NOT NULL,
 privileged INTEGER NOT NULL DEFAULT 0, shift_required INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS entitlement_requests (
 id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 entitlement TEXT NOT NULL REFERENCES app_entitlements(key), status TEXT NOT NULL DEFAULT 'Pending',
 reason TEXT NOT NULL, minutes INTEGER NOT NULL, snapshot TEXT NOT NULL, created_at TEXT NOT NULL,
 decided_by TEXT REFERENCES employees(employee_id), decided_at TEXT, decision_reason TEXT, expires_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS ix_entitlement_pending ON entitlement_requests(employee_id,entitlement) WHERE status='Pending';
CREATE INDEX IF NOT EXISTS ix_entitlement_effective ON entitlement_requests(employee_id,entitlement,status,expires_at);
CREATE TABLE IF NOT EXISTS shift_assignments (
 id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id), facility TEXT NOT NULL,
 starts_at TEXT NOT NULL, ends_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Scheduled', created_by TEXT NOT NULL,
 reason TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_shift_window ON shift_assignments(employee_id,status,starts_at,ends_at);
CREATE TABLE IF NOT EXISTS connector_state (key TEXT PRIMARY KEY, fail_next INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS observed_entitlements (
 employee_id TEXT NOT NULL REFERENCES employees(employee_id), entitlement TEXT NOT NULL REFERENCES app_entitlements(key),
 enabled INTEGER NOT NULL, synced_at TEXT NOT NULL, last_used_at TEXT, PRIMARY KEY(employee_id,entitlement));
CREATE TABLE IF NOT EXISTS provisioning_jobs (
 id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id), entitlement TEXT NOT NULL REFERENCES app_entitlements(key),
 status TEXT NOT NULL DEFAULT 'Queued', attempts INTEGER NOT NULL DEFAULT 0, available_at TEXT NOT NULL,
 created_by TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT, last_error TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS ix_one_pending_job ON provisioning_jobs(employee_id,entitlement) WHERE status IN ('Queued','Retry');
CREATE INDEX IF NOT EXISTS ix_jobs_due ON provisioning_jobs(status,available_at,id);
CREATE TABLE IF NOT EXISTS provisioning_attempts (
 id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES provisioning_jobs(id), attempted_at TEXT NOT NULL,
 outcome TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sponsor_intakes (
 id INTEGER PRIMARY KEY, sponsor_id TEXT NOT NULL REFERENCES employees(employee_id), name TEXT NOT NULL,
 email TEXT NOT NULL, worker_type TEXT NOT NULL, facility TEXT NOT NULL, starts_on TEXT NOT NULL, ends_on TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Pending', reason TEXT NOT NULL, created_at TEXT NOT NULL,
 decided_by TEXT, decision_reason TEXT, employee_id TEXT UNIQUE);
CREATE UNIQUE INDEX IF NOT EXISTS ix_intake_email ON sponsor_intakes(lower(email)) WHERE status='Pending';
'''
CATALOG=[
 ('care-records','Care records (local demo)','Assigned resident workspace',['Nurse','CareWorker','AgencyWorker','Manager'],0,1),
 ('roster-view','Rostering (local demo)','View own shift allocation',config.ALLOWED_ROLES,0,0),
 ('quality-export','Quality reporting (local demo)','Privileged diagnostic summary',['Manager','IAMOperator','Auditor'],1,0),
 ('learning','Learning (local demo)','Mandatory care-learning access',config.ALLOWED_ROLES,0,0)]

def migrate(c):
    c.executescript(SCHEMA)
    c.executemany('INSERT OR IGNORE INTO app_entitlements VALUES (?,?,?,?,?,?)',[(k,a,n,json.dumps(r),p,s) for k,a,n,r,p,s in CATALOG])
    c.execute("INSERT OR IGNORE INTO connector_state VALUES ('local-demo',0)")
    c.execute('INSERT OR IGNORE INTO schema_versions VALUES (12,?)',(enterprise.now(),))

def timestamp(value):
    try:
        d=datetime.fromisoformat(str(value))
        if d.tzinfo is not None:raise ValueError()
        return d.isoformat(timespec='seconds')
    except (ValueError,TypeError):raise ValueError('Use a valid UTC date/time without an offset.')

def request_access(actor,key,minutes,reason):
    why=governance.reason(reason);minutes=number(minutes,'Duration')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');e=enterprise.active(c,actor)
        ent=c.execute('SELECT * FROM app_entitlements WHERE key=?',(key,)).fetchone()
        if not ent:raise ValueError('Unknown application permission.')
        if e['approved_role'] not in json.loads(ent['roles']):raise PermissionError('This permission is not eligible for your workforce role.')
        limit=60 if ent['privileged'] else 10080
        if not 5<=minutes<=limit:raise ValueError(f'Request 5 to {limit} minutes.')
        if c.execute("SELECT 1 FROM entitlement_requests WHERE employee_id=? AND entitlement=? AND status='Approved' AND expires_at>?",(actor,key,enterprise.now())).fetchone():raise ValueError('Revoke or let the current grant expire before requesting again.')
        rid=c.execute('INSERT INTO entitlement_requests(employee_id,entitlement,reason,minutes,snapshot,created_at) VALUES (?,?,?,?,?,?)',(actor,key,why,minutes,enterprise.snapshot(c,actor),enterprise.now())).lastrowid
        governance.event(c,actor,actor,'ENTITLEMENT_REQUESTED',{'id':rid,'permission':key})
    return rid

def decide_access(actor,rid,decision,reason):
    why=governance.reason(reason)
    if decision not in ('Approved','Rejected','Revoked'):raise ValueError('Choose Approved, Rejected or Revoked.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        r=c.execute('SELECT r.*,e.privileged FROM entitlement_requests r JOIN app_entitlements e ON e.key=r.entitlement WHERE r.id=?',(rid,)).fetchone()
        if not r or r['status']!=('Approved' if decision=='Revoked' else 'Pending'):raise ValueError('Request state changed; reload before deciding.')
        if actor==r['employee_id']:raise PermissionError('An independent approver is required.')
        if r['privileged']:enterprise.require(c,actor,{'IAMOperator'})
        expires=None
        if decision=='Approved':
            if datetime.fromisoformat(enterprise.now())-datetime.fromisoformat(r['created_at'])>timedelta(days=7):raise ValueError('Request expired. Reject it and request again.')
            if enterprise.snapshot(c,r['employee_id'])!=r['snapshot']:raise ValueError('Worker state changed; request access again.')
            expires=(datetime.fromisoformat(enterprise.now())+timedelta(minutes=r['minutes'])).isoformat(timespec='seconds')
        c.execute('UPDATE entitlement_requests SET status=?,decided_by=?,decided_at=?,decision_reason=?,expires_at=COALESCE(?,expires_at) WHERE id=?',(decision,actor,enterprise.now(),why,expires,rid))
        queue(c,actor,r['employee_id'],r['entitlement'])
        governance.event(c,actor,r['employee_id'],'ENTITLEMENT_'+decision.upper(),{'request':rid,'permission':r['entitlement'],'expires_at':expires})

def desired(c,eid,key):
    """Re-evaluated at delivery and use: old queued work cannot regrant stale access."""
    try:e=enterprise.active(c,eid)
    except PermissionError:return False,'Employment is inactive, expired or blocked.'
    ent=c.execute('SELECT * FROM app_entitlements WHERE key=?',(key,)).fetchone()
    if not ent or e['approved_role'] not in json.loads(ent['roles']):return False,'Current role is not eligible.'
    grants=c.execute("SELECT * FROM entitlement_requests WHERE employee_id=? AND entitlement=? AND status='Approved' AND expires_at>? ORDER BY id DESC",(eid,key,enterprise.now())).fetchall()
    snapshot=enterprise.snapshot(c,eid)
    grant=next((r for r in grants if r['snapshot']==snapshot),None)
    if not grant:return False,'No current approval matching workforce state.'
    try:enterprise.require(c,grant['decided_by'],{'IAMOperator'} if ent['privileged'] else {'Manager','IAMOperator'})
    except PermissionError:return False,'Approval owner is no longer eligible; review required.'
    if ent['shift_required']:
        if not assurance.qualified(c,eid,e['approved_role']=='Nurse'):return False,'Required qualification missing or expired.'
        if not c.execute("SELECT 1 FROM shift_assignments WHERE employee_id=? AND facility=? AND status='Scheduled' AND starts_at<=? AND ends_at>?",(eid,e['facility'],enterprise.now(),enterprise.now())).fetchone():return False,'No current shift at the approved site.'
    return True,'Current independent approval and all context checks pass.'

def queue(c,actor,eid,key):
    row=c.execute("SELECT id FROM provisioning_jobs WHERE employee_id=? AND entitlement=? AND status IN ('Queued','Retry')",(eid,key)).fetchone()
    if row:return row[0]
    return c.execute('INSERT INTO provisioning_jobs(employee_id,entitlement,available_at,created_by,created_at) VALUES (?,?,?,?,?)',(eid,key,enterprise.now(),actor,enterprise.now())).lastrowid

def reconcile(actor):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        pairs=c.execute('SELECT employee_id,entitlement FROM entitlement_requests UNION SELECT employee_id,entitlement FROM observed_entitlements').fetchall();count=0
        for eid,key in pairs:
            wanted,_=desired(c,eid,key);observed=c.execute('SELECT enabled FROM observed_entitlements WHERE employee_id=? AND entitlement=?',(eid,key)).fetchone()
            last=c.execute('SELECT status FROM provisioning_jobs WHERE employee_id=? AND entitlement=? ORDER BY id DESC LIMIT 1',(eid,key)).fetchone()
            if bool(observed and observed[0])!=wanted and not (last and last[0]=='Dead'):
                queue(c,actor,eid,key);count+=1
        governance.event(c,actor,None,'CONNECTOR_RECONCILED',{'differences':count,'mode':'local-demo'})
    return count

def process_jobs(actor,limit=20):
    limit=number(limit,'Batch size')
    if not 1<=limit<=50:raise ValueError('Process 1 to 50 jobs per batch.')
    result={'succeeded':0,'retry':0,'dead':0}
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        jobs=c.execute("SELECT * FROM provisioning_jobs WHERE status IN ('Queued','Retry') AND available_at<=? ORDER BY id LIMIT ?",(enterprise.now(),limit)).fetchall()
        for job in jobs:
            attempts=job['attempts']+1
            fails=c.execute("SELECT fail_next FROM connector_state WHERE key='local-demo'").fetchone()[0]
            if fails:
                c.execute("UPDATE connector_state SET fail_next=fail_next-1 WHERE key='local-demo'")
                status='Dead' if attempts>=3 else 'Retry';detail='Simulated local connector unavailable. No target update applied.'
                due=(datetime.fromisoformat(enterprise.now())+timedelta(seconds=30*2**(attempts-1))).isoformat(timespec='seconds')
                c.execute('UPDATE provisioning_jobs SET status=?,attempts=?,available_at=?,last_error=? WHERE id=?',(status,attempts,due,detail,job['id']));result[status.lower()]+=1
                if status=='Dead':assurance.notify(c,'delivery-dead:'+str(job['id']),'Provisioning needs attention','Local connector job '+str(job['id'])+' exhausted retries. Investigate before retrying.','/connectors')
            else:
                enabled,why=desired(c,job['employee_id'],job['entitlement']);status='Succeeded';detail=('Enabled' if enabled else 'Disabled')+' in LOCAL demo: '+why
                c.execute('INSERT INTO observed_entitlements(employee_id,entitlement,enabled,synced_at) VALUES (?,?,?,?) ON CONFLICT(employee_id,entitlement) DO UPDATE SET enabled=excluded.enabled,synced_at=excluded.synced_at',(job['employee_id'],job['entitlement'],int(enabled),enterprise.now()))
                c.execute("UPDATE provisioning_jobs SET status='Succeeded',attempts=?,completed_at=?,last_error=NULL WHERE id=?",(attempts,enterprise.now(),job['id']));result['succeeded']+=1
            c.execute('INSERT INTO provisioning_attempts(job_id,attempted_at,outcome,detail) VALUES (?,?,?,?)',(job['id'],enterprise.now(),status,detail))
            governance.event(c,actor,job['employee_id'],'PROVISIONING_'+status.upper(),{'job':job['id'],'attempt':attempts,'detail':detail})
    return result

def retry_job(actor,jid):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        row=c.execute("SELECT * FROM provisioning_jobs WHERE id=? AND status='Dead'",(jid,)).fetchone()
        if not row:raise ValueError('Only a failed job in the dead-letter list can be retried.')
        if c.execute("SELECT 1 FROM provisioning_jobs WHERE employee_id=? AND entitlement=? AND status IN ('Queued','Retry')",(row['employee_id'],row['entitlement'])).fetchone():raise ValueError('A newer job is already pending for this permission.')
        c.execute("UPDATE provisioning_jobs SET status='Queued',attempts=0,available_at=?,last_error=NULL WHERE id=?",(enterprise.now(),jid))
        governance.event(c,actor,row['employee_id'],'PROVISIONING_RETRIED',{'job':jid,'attempt_history_preserved':True})

def fail_demo(actor,count):
    if config.ENVIRONMENT!='development' or config.GRAPH_MODE!='mock':raise PermissionError('Fault simulation is only available in the local development demo.')
    count=number(count,'Failure count')
    if not 0<=count<=3:raise ValueError('Choose 0 to 3 simulated failures.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        c.execute("UPDATE connector_state SET fail_next=? WHERE key='local-demo'",(count,));governance.event(c,actor,None,'DEMO_CONNECTOR_FAULT_CONFIGURED',{'count':count})

def add_shift(actor,data):
    why=governance.reason(data.get('reason'));start=timestamp(data.get('starts_at'));end=timestamp(data.get('ends_at'))
    if not datetime.fromisoformat(start)<datetime.fromisoformat(end)<=datetime.fromisoformat(start)+timedelta(hours=16):raise ValueError('A shift must last more than zero and no more than 16 hours.')
    if end<=enterprise.now():raise ValueError('Shift end must be in the future.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'});e=enterprise.active(c,data.get('employee_id'))
        if data.get('facility')!=e['facility']:raise ValueError('Shift site must match the worker site. Use the reviewed transfer/cover workflow for another site.')
        if e['end_date'] and end[:10]>e['end_date']:raise ValueError('Shift cannot extend beyond the employment contract.')
        if c.execute("SELECT 1 FROM shift_assignments WHERE employee_id=? AND status='Scheduled' AND starts_at<? AND ends_at>?",(e['employee_id'],end,start)).fetchone():raise ValueError('An overlapping shift already exists.')
        sid=c.execute('INSERT INTO shift_assignments(employee_id,facility,starts_at,ends_at,created_by,reason,created_at) VALUES (?,?,?,?,?,?,?)',(e['employee_id'],e['facility'],start,end,actor,why,enterprise.now())).lastrowid
        queue(c,actor,e['employee_id'],'care-records');governance.event(c,actor,e['employee_id'],'SHIFT_CREATED',{'id':sid,'start':start,'end':end})
    return sid

def cancel_shift(actor,sid):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        r=c.execute("SELECT * FROM shift_assignments WHERE id=? AND status='Scheduled'",(sid,)).fetchone()
        if not r:raise ValueError('Scheduled shift not found.')
        c.execute("UPDATE shift_assignments SET status='Cancelled' WHERE id=?",(sid,));queue(c,actor,r['employee_id'],'care-records')
        governance.event(c,actor,r['employee_id'],'SHIFT_CANCELLED',{'id':sid})

def use_resource(actor,key):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.active(c,actor);allowed,why=desired(c,actor,key)
        observed=c.execute('SELECT enabled FROM observed_entitlements WHERE employee_id=? AND entitlement=?',(actor,key)).fetchone()
        allowed=allowed and bool(observed and observed[0])
        if not observed or not observed[0]:why='Provisioning has not enabled this permission in the local connector.'
        if allowed:c.execute('UPDATE observed_entitlements SET last_used_at=? WHERE employee_id=? AND entitlement=?',(enterprise.now(),actor,key))
        governance.event(c,actor,actor,'APP_RESOURCE_CHECK',{'permission':key,'allowed':allowed,'explanation':why})
    return {'allowed':allowed,'explanation':why,'mode':'Local connector demonstration; no external care records accessed.'}

def submit_intake(actor,data):
    name=enterprise.clean(data.get('name'),2,100);email=enterprise.clean(data.get('email'),5,254).lower()
    worker=data.get('worker_type');facility=data.get('facility');starts=data.get('starts_on');ends=data.get('ends_on');why=governance.reason(data.get('reason'))
    if worker not in ('Agency','ThirdParty') or facility not in config.FACILITIES:raise ValueError('Choose an agency/contractor type and a known site.')
    try:
        first=date.fromisoformat(starts);last=date.fromisoformat(ends)
        if last<max(first,date.fromisoformat(enterprise.now()[:10])) or (last-first).days>90:raise ValueError()
    except (TypeError,ValueError):raise ValueError('Use valid start/end dates with a current end date and at most 90 days between them.')
    import re
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Enter a valid email.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        if c.execute('SELECT 1 FROM employees WHERE lower(email)=?',(email,)).fetchone():raise ValueError('This email already belongs to a worker.')
        iid=c.execute('INSERT INTO sponsor_intakes(sponsor_id,name,email,worker_type,facility,starts_on,ends_on,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?)',(actor,name,email,worker,facility,starts,ends,why,enterprise.now())).lastrowid
        governance.event(c,actor,None,'SPONSOR_INTAKE_SUBMITTED',{'id':iid,'worker_type':worker})
    return iid

def decide_intake(actor,iid,decision,reason):
    why=governance.reason(reason)
    if decision not in ('Approved','Rejected'):raise ValueError('Choose Approved or Rejected.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        r=c.execute("SELECT * FROM sponsor_intakes WHERE id=? AND status='Pending'",(iid,)).fetchone()
        if not r:raise ValueError('Pending intake not found.')
        if r['sponsor_id']==actor:raise PermissionError('A different operator must decide the sponsor intake.')
        enterprise.require(c,r['sponsor_id'],{'Manager','IAMOperator'});eid=None
        if decision=='Approved':
            eid='EXT'+str(r['id']).zfill(6);role='AgencyWorker' if r['worker_type']=='Agency' else 'CareWorker'
            data={'employee_id':eid,'name':r['name'],'email':r['email'],'worker_type':r['worker_type'],'approved_role':role,'facility':r['facility'],'status':'Active','manager_sponsor':r['sponsor_id'],'start_date':r['starts_on'],'end_date':r['ends_on']}
            lifecycle.validate_employee(data)
            if r['ends_on']<enterprise.now()[:10]:raise ValueError('The intake contract expired; submit a new intake.')
            c.execute('INSERT INTO employees(employee_id,name,email,worker_type,approved_role,facility,status,manager_sponsor,start_date,end_date,entra_object_id,cloud_enabled,cloud_role,admin_privilege) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)',(eid,r['name'],r['email'],r['worker_type'],role,r['facility'],'Active',r['sponsor_id'],r['starts_on'],r['ends_on'],'mock-'+eid.lower(),1,role))
            c.execute('INSERT INTO employee_roles VALUES (?,?)',(eid,role));assurance.sync_team(c,eid,r['facility'])
        c.execute('UPDATE sponsor_intakes SET status=?,decided_by=?,decision_reason=?,employee_id=? WHERE id=?',(decision,actor,why,eid,iid))
        governance.event(c,actor,eid,'SPONSOR_INTAKE_'+decision.upper(),{'id':iid,'mode':'mock','qualifications':'Not yet verified'})
    return eid
