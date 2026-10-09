from clock import utc_today
"""Care-workforce assurance. All decisions are server-side; integrations stay local.

Qualified access is fail closed. Scoring is an explainable rules engine, not AI.
The only automatic access changes remove expired access under configured policy.
"""
from datetime import date, datetime, timedelta
import hashlib, json, sqlite3
import config, database, enterprise, governance
from security_workstream import ledger

SCHEMA = '''
CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assurance_policy(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL,
 dormant_days INTEGER NOT NULL CHECK(dormant_days BETWEEN 30 AND 180), renewal_days INTEGER NOT NULL CHECK(renewal_days BETWEEN 7 AND 90),
 emergency_minutes INTEGER NOT NULL CHECK(emergency_minutes BETWEEN 5 AND 30), cover_minutes INTEGER NOT NULL CHECK(cover_minutes BETWEEN 30 AND 480),
 auto_expiry INTEGER NOT NULL CHECK(auto_expiry IN (0,1)), updated_by TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS qualifications(id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 kind TEXT NOT NULL CHECK(kind IN ('Safeguarding','Professional registration','Medication competency','Moving and handling')),
 expires_on TEXT NOT NULL, evidence_ref TEXT NOT NULL, verified_by TEXT NOT NULL REFERENCES employees(employee_id), verified_at TEXT NOT NULL,
 UNIQUE(employee_id,kind));
CREATE INDEX IF NOT EXISTS ix_qualification_expiry ON qualifications(expires_on,employee_id);
CREATE TABLE IF NOT EXISTS login_activity(employee_id TEXT PRIMARY KEY REFERENCES employees(employee_id), last_login TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sites(site_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS teams(team_id TEXT PRIMARY KEY, site_id TEXT NOT NULL REFERENCES sites(site_id), name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS team_members(employee_id TEXT PRIMARY KEY REFERENCES employees(employee_id), team_id TEXT NOT NULL REFERENCES teams(team_id));
CREATE TABLE IF NOT EXISTS admin_delegations(employee_id TEXT NOT NULL REFERENCES employees(employee_id), facility TEXT NOT NULL REFERENCES sites(name),
 granted_by TEXT NOT NULL, expires_on TEXT NOT NULL, PRIMARY KEY(employee_id,facility));
CREATE TABLE IF NOT EXISTS cover_requests(id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id), facility TEXT NOT NULL,
 minutes INTEGER NOT NULL CHECK(minutes BETWEEN 1 AND 480), reason TEXT NOT NULL, snapshot TEXT NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, manager_id TEXT, operator_id TEXT, expires_at TEXT);
CREATE TABLE IF NOT EXISTS cover_decisions(id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL REFERENCES cover_requests(id), actor_id TEXT NOT NULL,
 decision TEXT NOT NULL, reason TEXT NOT NULL, decided_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS emergency_grants(id INTEGER PRIMARY KEY, employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 resident_id TEXT NOT NULL REFERENCES residents(resident_id), reason TEXT NOT NULL, incident_ref TEXT NOT NULL,
 snapshot TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL, reviewed_by TEXT, reviewed_at TEXT, review_evidence TEXT);
CREATE INDEX IF NOT EXISTS ix_emergency_active ON emergency_grants(employee_id,expires_at);
CREATE TABLE IF NOT EXISTS operational_jobs(id INTEGER PRIMARY KEY, job_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
 started_at TEXT NOT NULL, finished_at TEXT, actor_id TEXT NOT NULL, result_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notification_outbox(id INTEGER PRIMARY KEY, dedupe_key TEXT NOT NULL, recipient_id TEXT NOT NULL REFERENCES employees(employee_id),
 title TEXT NOT NULL, message TEXT NOT NULL, href TEXT NOT NULL, created_at TEXT NOT NULL, email_state TEXT NOT NULL DEFAULT 'Not configured',
 UNIQUE(dedupe_key,recipient_id));
CREATE TABLE IF NOT EXISTS http_rate_limits(bucket TEXT PRIMARY KEY, hits INTEGER NOT NULL, expires_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ix_rate_expiry ON http_rate_limits(expires_at);
CREATE INDEX IF NOT EXISTS ix_employee_facility ON employees(facility,status);
CREATE INDEX IF NOT EXISTS ix_audit_actor_action ON audit_events(actor_id,action,event_time);
'''
KINDS=('Safeguarding','Professional registration','Medication competency','Moving and handling')

def migrate(c):
    """Idempotent additive migration. Never creates demo attestations on live data."""
    c.executescript(SCHEMA)
    if c.execute('SELECT 1 FROM schema_versions WHERE version=9').fetchone(): return
    c.execute('INSERT OR IGNORE INTO assurance_policy VALUES (1,1,90,30,15,240,1,?,?)',('SYSTEM',enterprise.now()))
    for i,facility in enumerate(config.FACILITIES,1):
        sid=f'SITE-{i}';c.execute('INSERT OR IGNORE INTO sites VALUES (?,?)',(sid,facility))
        c.execute('INSERT OR IGNORE INTO teams VALUES (?,?,?)',(f'TEAM-{i}',sid,'Care and operations'))
        c.execute('INSERT OR IGNORE INTO team_members SELECT employee_id,? FROM employees WHERE facility=?',(f'TEAM-{i}',facility))
    if config.SEED_DEMO:
        for r in c.execute("SELECT employee_id,approved_role FROM employees WHERE employee_id LIKE 'SC10%' AND status='Active'").fetchall():
            if r['approved_role'] in ('Nurse','Manager','CareWorker','AgencyWorker'):
                for kind in (('Safeguarding','Professional registration') if r['approved_role']=='Nurse' else ('Safeguarding',)):
                    expiry=utc_today()+timedelta(days=150)
                    if r['employee_id']=='SC1010': expiry=utc_today()-timedelta(days=1)
                    c.execute('INSERT OR IGNORE INTO qualifications(employee_id,kind,expires_on,evidence_ref,verified_by,verified_at) VALUES (?,?,?,?,?,?)',
                              (r['employee_id'],kind,str(expiry),'DEMO-FIXTURE: synthetic verification','SC1005',enterprise.now()))
    # V9 no longer stores bearer session secrets in the database; force reauthentication on upgrade.
    c.execute('DELETE FROM sessions')
    c.execute('INSERT INTO schema_versions VALUES (9,?)',(enterprise.now(),))

def policy(c): return dict(c.execute('SELECT * FROM assurance_policy WHERE id=1').fetchone())

def save_policy(actor,data):
    bounds={'dormant_days':(30,180),'renewal_days':(7,90),'emergency_minutes':(5,30),'cover_minutes':(30,480),'auto_expiry':(0,1)}
    values={}
    for key,(lo,hi) in bounds.items():
        try: values[key]=int(data.get(key,''))
        except (TypeError,ValueError): raise ValueError('Enter a whole number for '+key)
        if not lo<=values[key]<=hi: raise ValueError(f'{key} must be {lo} to {hi}.')
    why=governance.reason(data.get('reason'))
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        if str(policy(c)['version'])!=str(data.get('version')):raise ValueError('Policy was changed by another administrator. Reload before saving.')
        c.execute('UPDATE assurance_policy SET dormant_days=?,renewal_days=?,emergency_minutes=?,cover_minutes=?,auto_expiry=?,version=version+1,updated_by=?,updated_at=? WHERE id=1',(*values.values(),actor,enterprise.now()))
        governance.event(c,actor,None,'ASSURANCE_POLICY_CHANGED',{'values':values,'reason':why})

def qualified(c,eid,clinical=False):
    kinds=('Safeguarding','Professional registration') if clinical else ('Safeguarding',)
    present={r[0] for r in c.execute('SELECT kind FROM qualifications WHERE employee_id=? AND expires_on>=?',(eid,str(utc_today())))}
    return all(k in present for k in kinds)

def scopes(c,actor):
    enterprise.active(c,actor)
    roles={r[0] for r in c.execute('SELECT role FROM employee_roles WHERE employee_id=?',(actor,))}
    if roles & {'Manager','IAMOperator','Auditor'}:return set(config.FACILITIES)
    if 'SiteDelegate' in roles:
        return {r[0] for r in c.execute('SELECT facility FROM admin_delegations WHERE employee_id=? AND expires_on>=?',(actor,str(utc_today())))}
    return set()

def require_scope(c,actor,eid):
    target=c.execute('SELECT facility FROM employees WHERE employee_id=?',(eid,)).fetchone()
    if not target:raise ValueError('Worker not found.')
    if target['facility'] not in scopes(c,actor):raise PermissionError('This worker is outside your delegated site scope.')

def verify_qualification(actor,data):
    eid=data.get('employee_id');kind=data.get('kind');why=governance.reason(data.get('evidence_ref'))
    if kind not in KINDS:raise ValueError('Choose a supported qualification.')
    try: expiry=date.fromisoformat(data.get('expires_on',''))
    except (TypeError,ValueError):raise ValueError('Enter a valid expiry date.')
    if not utc_today()<=expiry<=utc_today()+timedelta(days=1826):raise ValueError('Expiry must be today through five years from today.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator','SiteDelegate'});require_scope(c,actor,eid)
        if actor==eid:raise PermissionError('Another authorised person must verify your qualification.')
        c.execute('INSERT INTO qualifications(employee_id,kind,expires_on,evidence_ref,verified_by,verified_at) VALUES (?,?,?,?,?,?) ON CONFLICT(employee_id,kind) DO UPDATE SET expires_on=excluded.expires_on,evidence_ref=excluded.evidence_ref,verified_by=excluded.verified_by,verified_at=excluded.verified_at',(eid,kind,str(expiry),why,actor,enterprise.now()))
        governance.event(c,actor,eid,'QUALIFICATION_VERIFIED',{'kind':kind,'expires_on':str(expiry),'evidence_ref':why})

def delegate(actor,data):
    eid=data.get('employee_id');facility=data.get('facility')
    try:expiry=date.fromisoformat(data.get('expires_on',''))
    except (TypeError,ValueError):raise ValueError('Use a valid expiry date.')
    if facility not in config.FACILITIES or not utc_today()<=expiry<=utc_today()+timedelta(days=90):raise ValueError('Choose a known site and expiry within 90 days.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'});enterprise.require(c,eid,{'SiteDelegate'})
        c.execute('INSERT INTO admin_delegations VALUES (?,?,?,?) ON CONFLICT(employee_id,facility) DO UPDATE SET expires_on=excluded.expires_on,granted_by=excluded.granted_by',(eid,facility,actor,str(expiry)))
        governance.event(c,actor,eid,'SITE_DELEGATED',{'facility':facility,'expires_on':str(expiry)})

def notify(c,key,title,message,href,recipients=None):
    if recipients is None:recipients=[r[0] for r in c.execute("SELECT DISTINCT r.employee_id FROM employee_roles r JOIN employees e USING(employee_id) WHERE r.role IN ('Manager','IAMOperator') AND e.status='Active' AND e.cloud_enabled=1")]
    for eid in recipients:
        c.execute('INSERT OR IGNORE INTO notification_outbox(dedupe_key,recipient_id,title,message,href,created_at) VALUES (?,?,?,?,?,?)',(key,eid,title,message,href,enterprise.now()))

def request_cover(actor,data):
    why=governance.reason(data.get('reason'));facility=data.get('facility')
    try:minutes=int(data.get('minutes',''))
    except (ValueError,TypeError):raise ValueError('Enter a whole number of minutes.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Nurse'})
        if not qualified(c,actor,True):raise PermissionError('Current safeguarding and professional registration are required.')
        if facility not in config.FACILITIES or not 1<=minutes<=policy(c)['cover_minutes']:raise ValueError('Use a known site and duration within the policy limit.')
        import release_v10
        release_v10.expire_pending(c,actor)
        if c.execute("SELECT 1 FROM cover_requests WHERE employee_id=? AND status IN ('Pending manager','Pending operator')",(actor,)).fetchone():raise ValueError('A site-cover request is already pending.')
        rid=c.execute("INSERT INTO cover_requests(employee_id,facility,minutes,reason,snapshot,status,created_at) VALUES (?,?,?,?,?,'Pending manager',?)",(actor,facility,minutes,why,enterprise.snapshot(c,actor),enterprise.now())).lastrowid
        notify(c,f'cover:{rid}','Site cover requested',f'{actor} requests {minutes} minutes at {facility}.','/coverage')
        governance.event(c,actor,actor,'COVER_REQUESTED',{'id':rid,'facility':facility,'minutes':minutes})
    return rid

def decide_cover(actor,data):
    decision=data.get('decision');why=governance.reason(data.get('reason'))
    if decision not in ('Approve','Reject','Revoke'):raise ValueError('Select Approve, Reject or Revoke.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        r=c.execute('SELECT * FROM cover_requests WHERE id=?',(data.get('id'),)).fetchone()
        if not r:raise ValueError('Request not found.')
        if actor==r['employee_id']:raise PermissionError('You cannot decide your own request.')
        if r['status'] not in ('Pending manager','Pending operator','Active'):raise ValueError('Request already closed.')
        if decision=='Revoke' and r['status']!='Active':raise ValueError('Only an active grant can be revoked.')
        if decision!='Revoke' and r['status']=='Active':raise ValueError('Use Revoke for an active grant.')
        status='Rejected' if decision=='Reject' else 'Revoked' if decision=='Revoke' else ''
        expiry=None;manager=r['manager_id'];operator=r['operator_id']
        if decision=='Approve':
            enterprise.require(c,actor,{'Manager'} if r['status']=='Pending manager' else {'IAMOperator'})
            if actor==manager:raise PermissionError('The manager and operator must be different people.')
            if datetime.fromisoformat(enterprise.now())-datetime.fromisoformat(r['created_at'])>timedelta(days=1):raise ValueError('Request expired. Submit a new request.')
            if r['snapshot']!=enterprise.snapshot(c,r['employee_id']) or not qualified(c,r['employee_id'],True):raise ValueError('Worker state or qualifications changed. Reject and resubmit.')
            if r['status']=='Pending manager':status='Pending operator';manager=actor
            else:
                enterprise.require(c,manager,{'Manager'})
                status='Active';operator=actor
                expiry=(datetime.fromisoformat(enterprise.now())+timedelta(minutes=min(r['minutes'],policy(c)['cover_minutes']))).isoformat(timespec='seconds')
        c.execute('UPDATE cover_requests SET status=?,manager_id=?,operator_id=?,expires_at=COALESCE(?,expires_at) WHERE id=?',(status,manager,operator,expiry,r['id']))
        # More than one decision by the same person is permitted for later revocation, with a separate event.
        c.execute('INSERT INTO cover_decisions(request_id,actor_id,decision,reason,decided_at) VALUES (?,?,?,?,?)',(r['id'],actor,decision,why,enterprise.now()))
        notify(c,f'cover:{r["id"]}:{status}','Site cover '+status,f'Request {r["id"]}: {status}','/coverage',[r['employee_id']])
        governance.event(c,actor,r['employee_id'],'COVER_DECISION',{'id':r['id'],'decision':decision,'status':status,'reason':why})
    return status

def emergency(actor,data):
    why=governance.reason(data.get('reason'));ref=enterprise.clean(data.get('incident_ref'),8,100)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Nurse'})
        if not qualified(c,actor,True):raise PermissionError('Emergency access cannot bypass expired qualifications.')
        resident=c.execute('SELECT * FROM residents WHERE resident_id=?',(data.get('resident_id'),)).fetchone()
        if not resident:raise ValueError('Resident identifier not found.')
        if c.execute('SELECT 1 FROM emergency_grants WHERE employee_id=? AND resident_id=? AND expires_at>?',(actor,resident['resident_id'],enterprise.now())).fetchone():raise ValueError('An emergency grant is already active for this resident.')
        expiry=(datetime.fromisoformat(enterprise.now())+timedelta(minutes=policy(c)['emergency_minutes'])).isoformat(timespec='seconds')
        gid=c.execute('INSERT INTO emergency_grants(employee_id,resident_id,reason,incident_ref,snapshot,created_at,expires_at) VALUES (?,?,?,?,?,?,?)',(actor,resident['resident_id'],why,ref,enterprise.snapshot(c,actor),enterprise.now(),expiry)).lastrowid
        notify(c,f'emergency:{gid}','Emergency access activated',f'{actor} opened a time-limited grant for {resident["resident_id"]}. Independent review required.','/coverage')
        governance.event(c,actor,resident['resident_id'],'EMERGENCY_ACCESS_ACTIVATED',{'id':gid,'expires_at':expiry,'reason':why,'incident_ref':ref})
    return gid

def review_emergency(actor,data):
    why=governance.reason(data.get('reason'))
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        r=c.execute('SELECT * FROM emergency_grants WHERE id=?',(data.get('id'),)).fetchone()
        if not r or r['reviewed_at']:raise ValueError('An unreviewed emergency event is required.')
        if r['employee_id']==actor:raise PermissionError('Emergency access requires independent review.')
        c.execute('UPDATE emergency_grants SET reviewed_by=?,reviewed_at=?,review_evidence=?,expires_at=MIN(expires_at,?) WHERE id=?',(actor,enterprise.now(),why,enterprise.now(),r['id']))
        governance.event(c,actor,r['employee_id'],'EMERGENCY_REVIEWED_AND_CLOSED',{'id':r['id'],'reason':why})

def permitted_residents(c,user):
    eid=user['employee_id'];enterprise.active(c,eid)
    role=user['approved_role'];clinical=role=='Nurse'
    if role not in ('Nurse','Manager','CareWorker','AgencyWorker') or not qualified(c,eid,clinical):return []
    sites={user['facility']} if role in ('Nurse','Manager') else set()
    ids={r[0] for r in c.execute('SELECT resident_id FROM assignments WHERE employee_id=? AND active=1',(eid,))} if role in ('CareWorker','AgencyWorker') else set()
    snap=enterprise.snapshot(c,eid)
    if role=='Nurse':
        sites.update(r['facility'] for r in c.execute("SELECT * FROM cover_requests WHERE employee_id=? AND status='Active' AND expires_at>?",(eid,enterprise.now())) if r['snapshot']==snap)
        ids.update(r['resident_id'] for r in c.execute('SELECT * FROM emergency_grants WHERE employee_id=? AND expires_at>?',(eid,enterprise.now())) if r['snapshot']==snap)
    return [dict(r) for r in c.execute('SELECT * FROM residents ORDER BY resident_id') if r['facility'] in sites or (r['resident_id'] in ids and (role=='Nurse' or r['facility']==user['facility']))]

def risk_inventory(c,actor):
    allowed=scopes(c,actor);pol=policy(c);out=[]
    workers=c.execute('SELECT e.*,l.last_login FROM employees e LEFT JOIN login_activity l USING(employee_id) ORDER BY employee_id').fetchall()
    valid_qualifications={}
    for q in c.execute('SELECT employee_id,kind FROM qualifications WHERE expires_on>=?',(str(utc_today()),)):
        valid_qualifications.setdefault(q['employee_id'],set()).add(q['kind'])
    denied={r[0]:r[1] for r in c.execute("SELECT actor_id,COUNT(*) FROM audit_events WHERE action='ACCESS_DENIED' AND event_time>=? GROUP BY actor_id",((datetime.fromisoformat(enterprise.now())-timedelta(hours=24)).isoformat(),))}
    for r in workers:
        if r['facility'] not in allowed:continue
        reasons=[];score=0
        if r['status']!='Active' and r['cloud_enabled']:score+=70;reasons.append('Inactive workforce record still enabled')
        if r['status']=='Active':
            if r['worker_type']=='Agency' and (not r['end_date'] or r['end_date']<str(utc_today())):score+=50;reasons.append('Agency contract missing or expired')
            if r['approved_role'] in ('Nurse','Manager','CareWorker','AgencyWorker') and not ({'Safeguarding','Professional registration'} if r['approved_role']=='Nurse' else {'Safeguarding'})<=valid_qualifications.get(r['employee_id'],set()):score+=35;reasons.append('Required qualification missing or expired; care access denied')
            baseline=(r['last_login'] or r['start_date'])[:10]
            if baseline<str(utc_today()-timedelta(days=pol['dormant_days'])):score+=20;reasons.append('No observed portal sign-in within dormancy window; confirm with manager')
            if r['admin_privilege'] and r['approved_role']!='IAMOperator':score+=60;reasons.append('Unexpected administrative privilege')
            if denied.get(r['employee_id'],0)>=5:score+=25;reasons.append('At least five denied portal accesses in 24 hours')
        out.append({'employee_id':r['employee_id'],'name':r['name'],'facility':r['facility'],'score':min(score,100),'reasons':reasons or ['No configured risk signals detected'],'recommendation':'Human review required; no automatic risk-based removal' if score else 'Continue scheduled review','last_login':r['last_login'] or 'Not observed'})
    return sorted(out,key=lambda x:(-x['score'],x['employee_id']))

def run_jobs(actor):
    if config.GRAPH_MODE!='mock':raise RuntimeError('Only the local mock connector is available.')
    key='daily:'+str(utc_today())
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        old=c.execute('SELECT * FROM operational_jobs WHERE job_key=?',(key,)).fetchone()
        if old:return {'replayed':True,**json.loads(old['result_json'])}
        pol=policy(c);disabled=[]
        if pol['auto_expiry']:
            targets=c.execute("SELECT employee_id FROM employees WHERE status='Active' AND worker_type='Agency' AND (end_date IS NULL OR end_date='' OR end_date<?)",(str(utc_today()),)).fetchall()
            for r in targets:
                eid=r['employee_id'];protect_operator(c,actor,eid)
                c.execute("UPDATE employees SET status='Suspended',cloud_enabled=0,cloud_role=NULL,admin_privilege=0,updated_at=? WHERE employee_id=?",(enterprise.now(),eid))
                c.execute('DELETE FROM sessions WHERE employee_id=?',(eid,));c.execute('DELETE FROM employee_roles WHERE employee_id=?',(eid,))
                c.execute('UPDATE assignments SET active=0 WHERE employee_id=?',(eid,))
                c.execute('INSERT OR REPLACE INTO blocked_users VALUES (?,?,?)',(eid,enterprise.now(),'Configured daily agency expiry'))
                governance.event(c,actor,eid,'SCHEDULED_AGENCY_DISABLED',{'job':key,'directory':'mock'});disabled.append(eid)
        c.execute("UPDATE cover_requests SET status='Expired' WHERE status='Active' AND expires_at<=?",(enterprise.now(),))
        c.execute('DELETE FROM sessions WHERE expires_at<=?',(enterprise.now(),))
        count=0
        for r in c.execute('SELECT * FROM qualifications WHERE expires_on<=?',(str(utc_today()+timedelta(days=pol['renewal_days'])),)).fetchall():
            notify(c,'qualification:'+str(r['id'])+':'+r['expires_on'],'Qualification deadline',f'{r["employee_id"]}: {r["kind"]} expires {r["expires_on"]}.','/qualifications');count+=1
        for r in c.execute('SELECT * FROM emergency_grants WHERE reviewed_at IS NULL AND created_at<?',((datetime.fromisoformat(enterprise.now())-timedelta(hours=24)).isoformat(),)).fetchall():
            notify(c,f'emergency-overdue:{r["id"]}','Emergency review overdue',f'Grant {r["id"]} awaits independent review.','/coverage')
        import release_v10
        expired_requests=release_v10.expire_pending(c,actor)
        reminders=release_v10.reminders(c,actor)
        result={'expired_requests':expired_requests,**reminders,'disabled':disabled,'qualification_alerts':count,'directory':'mock','policy_version':pol['version']}
        c.execute("INSERT INTO operational_jobs(job_key,status,started_at,finished_at,actor_id,result_json) VALUES (?,'Succeeded',?,?,?,?)",(key,enterprise.now(),enterprise.now(),actor,json.dumps(result)))
        governance.event(c,actor,None,'DAILY_JOB_COMPLETED',result)
    return result

def protect_operator(c,actor,target):
    if actor==target:raise PermissionError('Use another authorised operator to remove your own access.')
    isop=c.execute("SELECT 1 FROM employee_roles WHERE employee_id=? AND role='IAMOperator'",(target,)).fetchone()
    if isop:
        others=c.execute("SELECT e.employee_id FROM employees e JOIN employee_roles r USING(employee_id) WHERE r.role='IAMOperator' AND e.status='Active' AND e.cloud_enabled=1 AND e.employee_id<>?",(target,)).fetchall()
        valid=[]
        for r in others:
            try:enterprise.active(c,r[0]);valid.append(r[0])
            except PermissionError:pass
        if not valid:raise PermissionError('The last active IAM operator cannot be removed.')

def report_query(actor,question):
    q=' '.join(str(question or '').lower().split())
    with database.connect() as c:
        enterprise.require(c,actor,{'Manager','Auditor','IAMOperator','SiteDelegate'})
        rows=risk_inventory(c,actor)
    if 'dormant' in q:rows=[r for r in rows if any('dormancy' in x for x in r['reasons'])];intent='Dormant accounts'
    elif 'qualification' in q or 'credential' in q:rows=[r for r in rows if any('qualification' in x for x in r['reasons'])];intent='Qualification gaps'
    elif 'agency' in q:rows=[r for r in rows if any('Agency' in x for x in r['reasons'])];intent='Agency contract risks'
    elif q in ('risk','show risk','show high risk workers','high risk'):rows=[r for r in rows if r['score']>=35];intent='High risk workers'
    else:raise ValueError('Supported questions: show high risk workers; dormant accounts; expired qualifications; agency risks.')
    return {'intent':intent,'count':len(rows),'rows':rows,'method':'Allowlisted deterministic report; no LLM, no arbitrary SQL, no access decisions.'}


def sync_team(c,eid,facility):
    team=c.execute('SELECT t.team_id FROM teams t JOIN sites s USING(site_id) WHERE s.name=? ORDER BY t.team_id LIMIT 1',(facility,)).fetchone()
    if team:c.execute('INSERT INTO team_members VALUES (?,?) ON CONFLICT(employee_id) DO UPDATE SET team_id=excluded.team_id',(eid,team[0]))
