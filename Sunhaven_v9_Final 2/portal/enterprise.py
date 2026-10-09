from clock import utc_today
"""Local governance services. No cloud writes, credentials or network calls."""
from datetime import datetime, timezone, timedelta, date
import json, re
import database, governance
from security_workstream import ledger

PACKAGES = {
 'care-learning': {'name':'Care learning workspace','minutes':1440,'roles':{'CareWorker','AgencyWorker','Nurse','Manager','IAMOperator'},'description':'Read a fictional care onboarding and privacy checklist.'},
 'quality-review': {'name':'Quality review workspace','minutes':240,'roles':{'Nurse','Manager','Auditor','IAMOperator'},'description':'Read aggregate workforce quality metrics. Conflicts with incident-response.'},
 'incident-response': {'name':'Temporary incident responder','minutes':60,'roles':{'Manager','IAMOperator'},'description':'Create and transition local incident records for up to 60 minutes. Requires independent approval.'},
}
SCOPES={'metrics.read','training.read','incidents.summarize'}
SCHEMA='''
CREATE TABLE IF NOT EXISTS package_requests (
 id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 package_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('Pending','Approved','Rejected','Revoked')),
 reason TEXT NOT NULL, snapshot TEXT NOT NULL, created_at TEXT NOT NULL,
 decided_by TEXT, decision_reason TEXT, decided_at TEXT, expires_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_package_actor ON package_requests(employee_id,status,expires_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_package_pending ON package_requests(employee_id,package_id) WHERE status='Pending';
CREATE TABLE IF NOT EXISTS service_identities (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, kind TEXT NOT NULL, owner_id TEXT NOT NULL REFERENCES employees(employee_id),
 scopes TEXT NOT NULL, expires_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Active', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incident_cases (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, severity TEXT NOT NULL, status TEXT NOT NULL,
 owner_id TEXT NOT NULL REFERENCES employees(employee_id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 evidence TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS integration_runs (
 id INTEGER PRIMARY KEY, kind TEXT NOT NULL, actor_id TEXT NOT NULL, created_at TEXT NOT NULL, result_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_incident_status ON incident_cases(status,updated_at);
CREATE INDEX IF NOT EXISTS ix_integration_kind ON integration_runs(kind,id);
CREATE INDEX IF NOT EXISTS ix_audit_time ON audit_events(event_time);
CREATE INDEX IF NOT EXISTS ix_session_expiry ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS ix_employee_status ON employees(status,worker_type,end_date);
'''

def now(): return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds')
def clean(value, minimum=1, maximum=120):
    value=str(value or '').strip()
    if not minimum<=len(value)<=maximum: raise ValueError(f'Use {minimum} to {maximum} characters.')
    return value

def active(c, eid):
    e=c.execute('SELECT * FROM employees WHERE employee_id=?',(eid,)).fetchone()
    import auth
    if not auth.employment_valid(e) or c.execute('SELECT 1 FROM blocked_users WHERE employee_id=?',(eid,)).fetchone():
        raise PermissionError('Identity is inactive or blocked.')
    if e['worker_type']=='Agency' and (not e['end_date'] or e['end_date']<utc_today().isoformat()):
        raise PermissionError('Agency contract is missing or expired.')
    return dict(e)

def require(c,eid,roles):
    active(c,eid); governance.require(c,eid,roles)

def snapshot(c,eid):
    e=active(c,eid)
    roles=sorted(r[0] for r in c.execute('SELECT role FROM employee_roles WHERE employee_id=?',(eid,)))
    return json.dumps([e['approved_role'],e['facility'],e['end_date'],roles])

def eligible(c,eid,pid):
    if pid not in PACKAGES: raise ValueError('Unknown access package.')
    require(c,eid,PACKAGES[pid]['roles'])

def has_access(c,eid,pid):
    try:eligible(c,eid,pid)
    except (PermissionError,ValueError):return False
    row=c.execute("SELECT snapshot FROM package_requests WHERE employee_id=? AND package_id=? AND status='Approved' AND expires_at>? ORDER BY id DESC LIMIT 1",(eid,pid,now())).fetchone()
    return bool(row and row['snapshot']==snapshot(c,eid))

def request_package(actor,pid,reason):
    why=governance.reason(reason)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');eligible(c,actor,pid)
        import release_v10
        release_v10.expire_pending(c,actor)
        if has_access(c,actor,pid) or c.execute("SELECT 1 FROM package_requests WHERE employee_id=? AND package_id=? AND status='Pending'",(actor,pid)).fetchone():raise ValueError('An active grant or pending request already exists.')
        rid=c.execute("INSERT INTO package_requests(employee_id,package_id,status,reason,snapshot,created_at) VALUES (?,?,'Pending',?,?,?)",(actor,pid,why,snapshot(c,actor),now())).lastrowid
        governance.event(c,actor,actor,'PACKAGE_REQUESTED',{'id':rid,'package':pid})
    return rid

def decide_package(actor,rid,decision,reason):
    if decision not in ('Approved','Rejected','Revoked'):raise ValueError('Choose an allowed decision.')
    why=governance.reason(reason)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');require(c,actor,{'Manager','IAMOperator'})
        r=c.execute('SELECT * FROM package_requests WHERE id=?',(rid,)).fetchone()
        if not r:raise ValueError('Request not found.')
        if r['employee_id']==actor:raise PermissionError('A different approver is required.')
        if (decision=='Revoked' and r['status']!='Approved') or (decision!='Revoked' and r['status']!='Pending'):raise ValueError('This request already has a final decision.')
        expiry=None
        if decision=='Approved':
            eligible(c,r['employee_id'],r['package_id'])
            if r['snapshot']!=snapshot(c,r['employee_id']):raise ValueError('Worker state changed. Reject this request and submit a new one.')
            if datetime.fromisoformat(now())-datetime.fromisoformat(r['created_at'])>timedelta(days=7):raise ValueError('Request expired after seven days.')
            conflict={'quality-review':'incident-response','incident-response':'quality-review'}.get(r['package_id'])
            if conflict and has_access(c,r['employee_id'],conflict):raise ValueError('Separation of duties: revoke the conflicting package first.')
            expiry=(datetime.fromisoformat(now())+timedelta(minutes=PACKAGES[r['package_id']]['minutes'])).isoformat(timespec='seconds')
        c.execute('UPDATE package_requests SET status=?,decided_by=?,decision_reason=?,decided_at=?,expires_at=COALESCE(?,expires_at) WHERE id=?',(decision,actor,why,now(),expiry,rid))
        governance.event(c,actor,r['employee_id'],'PACKAGE_'+decision.upper(),{'id':rid,'reason':why,'expires_at':expiry})

def add_service(actor,data):
    name=clean(data.get('name'),3,80);kind=data.get('kind')
    if kind not in ('Service','Agent'):raise ValueError('Choose Service or Agent.')
    scopes={s.strip() for s in str(data.get('scopes','')).split(',') if s.strip()}
    if not scopes or not scopes<=SCOPES:raise ValueError('Only the listed local scopes are permitted.')
    try:days=int(data.get('days','7'))
    except (ValueError,TypeError):raise ValueError('Use a lifetime from 1 to 90 days.')
    if not 1<=days<=90:raise ValueError('Use a lifetime from 1 to 90 days.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');require(c,actor,{'IAMOperator'});require(c,data.get('owner_id'),{'Manager','IAMOperator'})
        if c.execute('SELECT 1 FROM service_identities WHERE name=?',(name,)).fetchone():raise ValueError('Identity name already exists.')
        sid=c.execute('INSERT INTO service_identities(name,kind,owner_id,scopes,expires_at,created_at) VALUES (?,?,?,?,?,?)',(name,kind,data['owner_id'],json.dumps(sorted(scopes)),(datetime.fromisoformat(now())+timedelta(days=days)).isoformat(timespec='seconds'),now())).lastrowid
        governance.event(c,actor,str(sid),'SERVICE_REGISTERED',{'kind':kind,'scopes':sorted(scopes)})
    return sid

def service_action(actor,sid,action,scope=''):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');require(c,actor,{'IAMOperator'})
        r=c.execute('SELECT * FROM service_identities WHERE id=?',(sid,)).fetchone()
        if not r:raise ValueError('Identity not found.')
        if action=='disable':
            c.execute("UPDATE service_identities SET status='Disabled' WHERE id=?",(sid,));result={'decision':'DISABLED'}
        elif action=='evaluate':
            if scope not in SCOPES:raise ValueError('Unknown local scope.')
            owner_ok=True
            try:require(c,r['owner_id'],{'Manager','IAMOperator'})
            except PermissionError:owner_ok=False
            allowed=r['status']=='Active' and r['expires_at']>now() and owner_ok and scope in json.loads(r['scopes'])
            result={'decision':'ALLOW' if allowed else 'DENY','scope':scope,'owner_active':owner_ok,'mode':'Local policy evaluation; no agent execution'}
        else:raise ValueError('Unknown action.')
        governance.event(c,actor,str(sid),'SERVICE_'+action.upper(),result)
    return result

TRANSITIONS={'Open':{'Investigating'},'Investigating':{'Contained'},'Contained':{'Resolved'},'Resolved':set()}
def incident(actor,data):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');require(c,actor,{'Manager','IAMOperator'})
        if not has_access(c,actor,'incident-response'):raise PermissionError('An active temporary incident-responder package is required.')
        evidence=governance.reason(data.get('evidence'))
        if data.get('action')=='create':
            title=clean(data.get('title'),5,140);sev=data.get('severity')
            if sev not in ('Low','Medium','High','Critical'):raise ValueError('Select a severity.')
            require(c,data.get('owner_id'),{'Manager','IAMOperator'})
            iid=c.execute("INSERT INTO incident_cases(title,severity,status,owner_id,created_at,updated_at,evidence) VALUES (?,?,'Open',?,?,?,?)",(title,sev,data['owner_id'],now(),now(),evidence)).lastrowid
            status='Open'
        else:
            iid=data.get('id');r=c.execute('SELECT * FROM incident_cases WHERE id=?',(iid,)).fetchone()
            status=data.get('status')
            if not r or status not in TRANSITIONS.get(r['status'],set()):raise ValueError('Move through Open, Investigating, Contained, then Resolved.')
            c.execute('UPDATE incident_cases SET status=?,updated_at=?,evidence=? WHERE id=?',(status,now(),evidence,iid))
        governance.event(c,actor,str(iid),'INCIDENT_'+status.upper(),{'evidence':evidence})
    return iid

def evaluate_policy(data):
    choices={'risk':{'Low','Medium','High'},'device':{'Managed','Unmanaged'},'auth':{'Password','Push MFA','Passkey'},'active':{'Yes','No'}}
    for k,v in choices.items():
        if data.get(k) not in v:raise ValueError('Choose a valid value for '+k)
    reasons=[]
    if data['active']=='No':reasons.append('Inactive identity')
    if data['risk']=='High':reasons.append('High sign-in risk')
    if data['device']=='Unmanaged':reasons.append('Managed device required')
    if data['auth']!='Passkey':reasons.append('Phishing-resistant authentication required')
    return {'decision':'BLOCK' if reasons else 'ALLOW','reasons':reasons or ['All simulated policy conditions passed'],'mode':'What-if only; inputs are declared, not measured. This does not authenticate users.'}

def inventory(actor):
    with database.connect() as c:
        active(c,actor)
        governor=bool(c.execute("SELECT 1 FROM employee_roles WHERE employee_id=? AND role IN ('Manager','Auditor','IAMOperator')",(actor,)).fetchone())
        where,args=('',()) if governor else (' WHERE employee_id=?',(actor,))
        req=[dict(r) for r in c.execute('SELECT * FROM package_requests'+where+' ORDER BY id DESC LIMIT 100',args)]
        for r in req:
            if r['status']=='Approved' and not has_access(c,r['employee_id'],r['package_id']):r['status']='Expired / inactive'
        return {'requests':req,'services':[dict(r) for r in c.execute('SELECT * FROM service_identities ORDER BY id DESC LIMIT 100')] if governor else [],'incidents':[dict(r) for r in c.execute('SELECT * FROM incident_cases ORDER BY id DESC LIMIT 100')] if governor else [],'grants':[p for p in PACKAGES if has_access(c,actor,p)],'governor':governor}
