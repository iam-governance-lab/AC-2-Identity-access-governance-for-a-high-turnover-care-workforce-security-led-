from clock import utc_today
"""Reviewed roster reconciliation and recurring certification for synthetic workers."""
from datetime import date, datetime, timedelta
import csv, hashlib, io, json
import database, enterprise, governance
from security_workstream import ledger

SCHEMA='''
CREATE TABLE IF NOT EXISTS roster_imports (
 id INTEGER PRIMARY KEY AUTOINCREMENT, submitted_by TEXT NOT NULL, approved_by TEXT,
 status TEXT NOT NULL, fingerprint TEXT NOT NULL, snapshot TEXT NOT NULL, changes TEXT NOT NULL,
 decision_reason TEXT,
 submitted_at TEXT NOT NULL, approved_at TEXT, applied_at TEXT
);
CREATE TABLE IF NOT EXISTS review_campaigns (
 id INTEGER PRIMARY KEY AUTOINCREMENT, period TEXT NOT NULL UNIQUE, created_by TEXT NOT NULL,
 created_at TEXT NOT NULL, due_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS campaign_items (
 id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL REFERENCES review_campaigns(id),
 employee_id TEXT NOT NULL REFERENCES employees(employee_id), role_at_start TEXT NOT NULL,
 facility_at_start TEXT NOT NULL, decision TEXT NOT NULL DEFAULT 'Pending',
 reviewer_id TEXT, reason TEXT, decided_at TEXT, UNIQUE(campaign_id,employee_id)
);
CREATE INDEX IF NOT EXISTS ix_campaign_pending ON campaign_items(campaign_id,decision);
'''
FIELDS=('employee_id','email','role','facility','status','end_date')
def parse_csv(raw):
    if not isinstance(raw,str) or not 1<=len(raw.encode('utf-8'))<=32000:raise ValueError('Roster CSV must be 1 to 32 KB.')
    rd=csv.DictReader(io.StringIO(raw))
    if rd.fieldnames is None or len(set(rd.fieldnames))!=len(rd.fieldnames) or set(rd.fieldnames)!=set(FIELDS):raise ValueError('Use exactly these CSV columns: '+', '.join(FIELDS))
    rows=[];seen=set()
    for row in rd:
        if None in row:raise ValueError('CSV row has too many values.')
        values={k:(row.get(k) or '').strip() for k in FIELDS}
        if not values['employee_id'] or values['employee_id'] in seen:raise ValueError('Worker IDs must be present and unique.')
        seen.add(values['employee_id'])
        if values['status'] not in ('Active','Leaver'):raise ValueError('Roster status must be Active or Leaver.')
        if values['end_date']:
            try:date.fromisoformat(values['end_date'])
            except ValueError:raise ValueError('End date must be YYYY-MM-DD.')
        if any(len(v)>140 for v in values.values()) or not values['email'] or not values['role'] or not values['facility']:raise ValueError('A required value is missing or too long.')
        rows.append(values)
        if len(rows)>100:raise ValueError('At most 100 workers per import.')
    if not rows:raise ValueError('Roster has no workers.')
    return rows

def _plan(c,rows):
    changes=[];snapshot=[]
    for row in rows:
        e=c.execute('SELECT * FROM employees WHERE employee_id=?',(row['employee_id'],)).fetchone()
        if not e:changes.append({'employee_id':row['employee_id'],'action':'UNKNOWN_WORKER_REVIEW'});continue
        if e['email'].casefold()!=row['email'].casefold():raise ValueError('Email mismatch for '+row['employee_id']+'; no import was staged.')
        snap=[e['employee_id'],e['email'],e['approved_role'],e['facility'],e['status'],e['end_date'],e['cloud_enabled']]
        snapshot.append(snap)
        if row['status']=='Active' and e['worker_type']=='Agency' and (not row['end_date'] or row['end_date']<e['start_date']):raise ValueError('Active agency workers require an end date on or after their start date.')
        if row['role']!=e['approved_role'] or row['facility']!=e['facility']:
            changes.append({'employee_id':e['employee_id'],'action':'ROLE_OR_FACILITY_REVIEW'})
        if row['status']=='Leaver' and e['status']=='Active':changes.append({'employee_id':e['employee_id'],'action':'DISABLE_LEAVER'})
        elif row['status']=='Active' and e['status']!='Active':changes.append({'employee_id':e['employee_id'],'action':'INACTIVE_CONFLICT_REVIEW'})
        if e['worker_type']=='Agency' and row['end_date']!= (e['end_date'] or '') and row['status']=='Active' and e['status']=='Active':
            changes.append({'employee_id':e['employee_id'],'action':'AGENCY_DATE_UPDATE','from':e['end_date'] or '', 'to':row['end_date']})
    payload=json.dumps({'rows':rows,'snapshot':snapshot,'changes':changes},sort_keys=True,separators=(',',':'))
    return {'rows':rows,'snapshot':snapshot,'changes':changes,'fingerprint':hashlib.sha256(payload.encode()).hexdigest()}

def stage(actor,raw):
    rows=parse_csv(raw)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        plan=_plan(c,rows)
        rid=c.execute('INSERT INTO roster_imports(submitted_by,status,fingerprint,snapshot,changes,submitted_at) VALUES (?,?,?,?,?,?)',(actor,'Pending',plan['fingerprint'],json.dumps(plan['snapshot']),json.dumps(plan['changes']),enterprise.now())).lastrowid
        # Keep the canonical rows in the snapshot alongside the worker-state snapshot.
        c.execute('UPDATE roster_imports SET snapshot=? WHERE id=?',(json.dumps({'rows':rows,'workers':plan['snapshot']}),rid))
        governance.event(c,actor,None,'ROSTER_STAGED',{'id':rid,'changes':len(plan['changes'])})
    return rid

def decide(actor,rid,decision,reason):
    why=governance.reason(reason)
    if decision not in ('Approved','Rejected'):raise ValueError('Decision must be Approved or Rejected.')
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        imp=c.execute('SELECT * FROM roster_imports WHERE id=?',(rid,)).fetchone()
        if not imp or imp['status']!='Pending':raise ValueError('Pending import not found.')
        if imp['submitted_by']==actor:raise PermissionError('A different person must approve roster imports.')
        c.execute('UPDATE roster_imports SET approved_by=?,status=?,approved_at=?,decision_reason=? WHERE id=?',(actor,decision,enterprise.now(),why,rid))
        governance.event(c,actor,None,'ROSTER_'+decision.upper(),{'id':rid,'reason':why})

def apply(actor,rid):
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        imp=c.execute('SELECT * FROM roster_imports WHERE id=?',(rid,)).fetchone()
        if not imp or imp['status']!='Approved' or imp['applied_at']:raise ValueError('Unapplied approved import required.')
        if imp['approved_by']==actor:raise PermissionError('An approver cannot execute their own decision.')
        enterprise.require(c,imp['approved_by'],{'Manager','IAMOperator'})
        if datetime.fromisoformat(enterprise.now())-datetime.fromisoformat(imp['approved_at'])>timedelta(days=1):raise ValueError('Roster approval expired after 24 hours. Stage a fresh import.')
        stored=json.loads(imp['snapshot']);fresh=_plan(c,stored['rows'])
        if fresh['fingerprint']!=imp['fingerprint'] or fresh['snapshot']!=stored['workers']:raise ValueError('Roster or worker state changed since preview. Stage a fresh import.')
        changes=fresh['changes']
        for change in changes:
            eid=change['employee_id'];action=change['action']
            if action=='AGENCY_DATE_UPDATE':
                c.execute('UPDATE employees SET end_date=?,updated_at=? WHERE employee_id=?',(change['to'],enterprise.now(),eid))
                governance.event(c,actor,eid,'AGENCY_END_DATE_UPDATED',{'old':change['from'],'new':change['to'],'import':rid})
            elif action=='DISABLE_LEAVER':
                import assurance
                assurance.protect_operator(c,actor,eid)
                if eid==imp['approved_by']:raise PermissionError('A roster approver cannot be terminated by the same import.')
                c.execute("UPDATE employees SET status='Leaver',cloud_enabled=0,cloud_role=NULL,admin_privilege=0,updated_at=? WHERE employee_id=?",(enterprise.now(),eid))
                c.execute('DELETE FROM employee_roles WHERE employee_id=?',(eid,))
                c.execute('UPDATE assignments SET active=0 WHERE employee_id=?',(eid,))
                c.execute('DELETE FROM sessions WHERE employee_id=?',(eid,))
                c.execute('INSERT INTO blocked_users(employee_id,blocked_at,reason) VALUES (?,?,?) ON CONFLICT(employee_id) DO UPDATE SET blocked_at=excluded.blocked_at,reason=excluded.reason',(eid,enterprise.now(),'Approved synthetic roster leaver'))
                governance.event(c,actor,eid,'ROSTER_LEAVER_DISABLED',{'import':rid,'directory':'mock'})
            else:
                governance.event(c,actor,eid,'ROSTER_RECONCILIATION_FLAG',{'import':rid,'finding':action})
                if action!='UNKNOWN_WORKER_REVIEW':
                    c.execute('INSERT INTO remediation_tasks(employee_id,title,priority,owner_id,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',(eid,'Roster reconciliation: '+action,'High',actor,actor,enterprise.now(),enterprise.now()))
        c.execute("UPDATE roster_imports SET status='Applied',applied_at=? WHERE id=?",(enterprise.now(),rid))
        governance.event(c,actor,None,'ROSTER_APPLIED',{'id':rid,'changes':len(changes)})
    return changes

def quarter(on=None):
    on=on or utc_today();return f'{on.year}-Q{(on.month-1)//3+1}'

def create_campaign(actor,on=None):
    period=quarter(on)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        exists=c.execute('SELECT id FROM review_campaigns WHERE period=?',(period,)).fetchone()
        if exists:return exists['id']
        now=enterprise.now();cid=c.execute('INSERT INTO review_campaigns(period,created_by,created_at,due_at) VALUES (?,?,?,?)',(period,actor,now,(datetime.fromisoformat(now)+timedelta(days=14)).isoformat(timespec='seconds'))).lastrowid
        workers=c.execute("SELECT employee_id,approved_role,facility FROM employees WHERE status='Active' AND cloud_enabled=1 ORDER BY employee_id").fetchall()
        c.executemany('INSERT INTO campaign_items(campaign_id,employee_id,role_at_start,facility_at_start) VALUES (?,?,?,?)',[(cid,r['employee_id'],r['approved_role'],r['facility']) for r in workers])
        governance.event(c,actor,None,'REVIEW_CAMPAIGN_CREATED',{'id':cid,'period':period,'workers':len(workers)})
    return cid

def review(actor,item_id,decision,reason):
    if decision not in ('Retain','Remove'):raise ValueError('Choose Retain or Remove.')
    why=governance.reason(reason)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'Manager','IAMOperator'})
        item=c.execute('SELECT * FROM campaign_items WHERE id=?',(item_id,)).fetchone()
        if not item or item['decision']!='Pending':raise ValueError('Pending review item required.')
        if item['employee_id']==actor:raise PermissionError('Review your own access with another reviewer.')
        e=c.execute('SELECT approved_role,facility,status FROM employees WHERE employee_id=?',(item['employee_id'],)).fetchone()
        if not e or (e['approved_role'],e['facility'])!=(item['role_at_start'],item['facility_at_start']):raise ValueError('Worker role/facility changed; reconcile before deciding.')
        c.execute('UPDATE campaign_items SET decision=?,reviewer_id=?,reason=?,decided_at=? WHERE id=?',(decision,actor,why,enterprise.now(),item_id))
        if decision=='Remove':
            c.execute("UPDATE package_requests SET status='Revoked',decision_reason=?,decided_by=?,decided_at=? WHERE employee_id=? AND status='Approved'",(why,actor,enterprise.now(),item['employee_id']))
            c.execute('INSERT INTO remediation_tasks(employee_id,title,priority,owner_id,status,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',(item['employee_id'],'Investigate removal of core role and assignments','High',actor,'Open',actor,enterprise.now(),enterprise.now()))
        governance.event(c,actor,item['employee_id'],'CAMPAIGN_'+decision.upper(),{'item':item_id,'reason':why})

def summary():
    with database.connect() as c:
        return {'imports':[dict(r) for r in c.execute('SELECT id,submitted_by,approved_by,status,fingerprint,changes,submitted_at,applied_at FROM roster_imports ORDER BY id DESC LIMIT 15')],
          'campaigns':[dict(r) for r in c.execute("SELECT g.*,(SELECT COUNT(*) FROM campaign_items i WHERE i.campaign_id=g.id AND i.decision='Pending') pending_count FROM review_campaigns g ORDER BY g.id DESC LIMIT 8")],
          'items':[dict(r) for r in c.execute('SELECT * FROM campaign_items ORDER BY id DESC LIMIT 100')]}
