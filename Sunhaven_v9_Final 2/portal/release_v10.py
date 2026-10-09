"""V10 review operations. Local evidence and human-approved remediation only."""
from datetime import datetime, timedelta
import json
import auth, config, database, enterprise, governance

INDEXES = '''
CREATE UNIQUE INDEX IF NOT EXISTS ix_employee_email_folded ON employees(lower(email));
CREATE INDEX IF NOT EXISTS ix_access_pending ON access_requests(status,created_at);
CREATE INDEX IF NOT EXISTS ix_cover_pending ON cover_requests(status,created_at);
CREATE INDEX IF NOT EXISTS ix_task_status ON remediation_tasks(status,created_at);
CREATE INDEX IF NOT EXISTS ix_notes_created ON work_notes(note_id DESC);
CREATE INDEX IF NOT EXISTS ix_compliance_open ON compliance_findings(status,employee_id,rule_id);
CREATE INDEX IF NOT EXISTS ix_service_owner ON service_identities(owner_id,status);
'''

def migrate(c):
    duplicate=c.execute('SELECT lower(email) FROM employees GROUP BY lower(email) HAVING COUNT(*)>1 LIMIT 1').fetchone()
    if duplicate:raise RuntimeError('V10 migration stopped: duplicate email addresses differing only in letter case. Reconcile identities in a backup copy before upgrading.')
    c.executescript(INDEXES)
    c.execute('INSERT OR IGNORE INTO schema_versions VALUES (10,?)',(enterprise.now(),))

def expire_pending(c,actor):
    """Close unusable requests, never grant access; preserve rows and decisions."""
    stamp=enterprise.now();now=datetime.fromisoformat(stamp);counts={}
    for table,pk,where,cutoff in (
        ('cover_requests','id',"status IN ('Pending manager','Pending operator')",now-timedelta(days=1)),
        ('package_requests','id',"status='Pending'",now-timedelta(days=7)),
        ('access_requests','request_id',"status='Approved'",now-timedelta(days=7))):
        col='decided_at' if table=='access_requests' else 'created_at'
        rows=c.execute(f'SELECT {pk},employee_id FROM {table} WHERE {where} AND julianday({col})<julianday(?)',(cutoff.isoformat(),)).fetchall()
        for r in rows:
            if table=='package_requests':
                c.execute("UPDATE package_requests SET status='Rejected',decided_by=?,decided_at=?,decision_reason='Expired after seven days without approval' WHERE id=?",(actor,stamp,r[0]))
            else:c.execute(f"UPDATE {table} SET status='Expired' WHERE {pk}=?",(r[0],))
            governance.event(c,actor,r['employee_id'],'STALE_REQUEST_EXPIRED',{'type':table,'id':r[0]})
        counts[table]=len(rows)
    return counts

QUEUE = """
SELECT 'Access request' kind,request_id id,employee_id,requested_role||' · '||facility||' · '||reason title,status,
 datetime(created_at,'+2 days') due_at,'/requests/'||request_id href FROM access_requests WHERE status IN ('Pending','Approved')
UNION ALL
SELECT 'Site cover',id,employee_id,facility||' · '||minutes||' minutes · '||reason,status,datetime(created_at,'+1 day'),'/coverage' FROM cover_requests WHERE status IN ('Pending manager','Pending operator')
UNION ALL
SELECT 'Access package',id,employee_id,package_id||' · '||reason,status,datetime(created_at,'+2 days'),'/catalog' FROM package_requests WHERE status='Pending'
UNION ALL
SELECT 'Remediation',task_id,employee_id,title,status,datetime(created_at,'+2 days'),'/operations' FROM remediation_tasks WHERE status!='Resolved'
UNION ALL
SELECT 'Certification',i.id,i.employee_id,c.period,i.decision,c.due_at,'/campaigns' FROM campaign_items i JOIN review_campaigns c ON c.id=i.campaign_id WHERE i.decision='Pending'
UNION ALL
SELECT 'Emergency review',id,employee_id,incident_ref,'Pending',datetime(created_at,'+1 day'),'/coverage' FROM emergency_grants WHERE reviewed_at IS NULL
"""

def work_queue(c,q='',kind='',overdue=False,page=1,size=25):
    if not 1<=page<=1000000 or not 1<=size<=100:raise ValueError('Invalid page size or number.')
    where=" WHERE (w.employee_id LIKE ? OR e.name LIKE ? OR w.title LIKE ?)"
    args=['%'+q[:100]+'%']*3
    if kind:where+=' AND w.kind=?';args.append(kind)
    if overdue:where+=' AND julianday(w.due_at)<julianday(?)';args.append(enterprise.now())
    base=' FROM ('+QUEUE+') w JOIN employees e USING(employee_id)'+where
    total=c.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
    rows=[dict(r) for r in c.execute('SELECT w.*,e.name,(julianday(w.due_at)<julianday(?)) overdue'+base+' ORDER BY julianday(w.due_at),kind,id LIMIT ? OFFSET ?',[enterprise.now(),*args,size,(page-1)*size])]
    return total,rows

def service_health(c):
    rows=[]
    for r in c.execute('''SELECT s.id,s.name service_name,s.owner_id,s.expires_at,s.status service_status,
                          e.*,b.employee_id blocked FROM service_identities s JOIN employees e ON e.employee_id=s.owner_id
                          LEFT JOIN blocked_users b ON b.employee_id=e.employee_id ORDER BY s.id'''):
        issues=[]
        if not auth.employment_valid(r) or r['blocked']:issues.append('Owner inactive or expired')
        try:
            if datetime.fromisoformat(r['expires_at'])<=datetime.fromisoformat(enterprise.now()):issues.append('Identity lifetime expired')
        except (ValueError,TypeError):issues.append('Invalid lifetime')
        rows.append({'id':r['id'],'name':r['service_name'],'owner_id':r['owner_id'],'status':r['service_status'],'expires_at':r['expires_at'],'issues':issues})
    return rows

def reassign_owner(actor,sid,owner,reason):
    why=governance.reason(reason)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        enterprise.require(c,owner,{'Manager','IAMOperator'})
        r=c.execute('SELECT * FROM service_identities WHERE id=?',(sid,)).fetchone()
        if not r:raise ValueError('Service identity not found.')
        if r['owner_id']==owner:raise ValueError('Choose a different active owner.')
        c.execute('UPDATE service_identities SET owner_id=? WHERE id=?',(owner,sid))
        governance.event(c,actor,owner,'SERVICE_OWNER_REASSIGNED',{'id':sid,'previous_owner':r['owner_id'],'new_owner':owner,'reason':why,'access_unchanged':True})

def refresh_review(actor,item_id,reason):
    why=governance.reason(reason)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,{'IAMOperator'})
        item=c.execute("SELECT * FROM campaign_items WHERE id=? AND decision='Pending'",(item_id,)).fetchone()
        if not item:raise ValueError('A pending certification item is required.')
        if item['employee_id']==actor:raise PermissionError('Another operator must reconcile your review.')
        e=c.execute('SELECT approved_role,facility FROM employees WHERE employee_id=?',(item['employee_id'],)).fetchone()
        before=[item['role_at_start'],item['facility_at_start']];after=[e['approved_role'],e['facility']]
        if before==after:raise ValueError('Review already matches the current worker record.')
        c.execute('UPDATE campaign_items SET role_at_start=?,facility_at_start=? WHERE id=?',(*after,item_id))
        governance.event(c,actor,item['employee_id'],'CAMPAIGN_SNAPSHOT_REFRESHED',{'item':item_id,'before':before,'after':after,'reason':why,'decision':'Pending'})

def cancel_request(actor,rid,reason):
    why=governance.reason(reason)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.active(c,actor)
        r=c.execute('SELECT * FROM access_requests WHERE request_id=?',(rid,)).fetchone()
        if not r or r['employee_id']!=actor:raise PermissionError('You may withdraw only your own requests.')
        if r['status']!='Pending':raise ValueError('Only a pending request can be withdrawn.')
        c.execute("UPDATE access_requests SET status='Cancelled',decision_by=?,decision_note=?,decided_at=? WHERE request_id=?",(actor,why,enterprise.now(),rid))
        governance.event(c,actor,actor,'ACCESS_REQUEST_WITHDRAWN',{'id':rid,'reason':why})

def reminders(c,actor):
    import assurance
    total,rows=work_queue(c,overdue=True,size=100)
    # Iterate every page: the batch limit never hides older pending work.
    page=1;count=0
    while rows:
        for r in rows:
            assurance.notify(c,f'work:{r["kind"]}:{r["id"]}:{enterprise.now()[:10]}','Governance action overdue',f'{r["kind"]} {r["id"]} for {r["employee_id"]} requires human review.', '/workbench')
            count+=1
        page+=1;_,rows=work_queue(c,overdue=True,size=100,page=page)
    for r in service_health(c):
        if r['status']=='Active' and r['issues']:
            assurance.notify(c,f'service-health:{r["id"]}:{enterprise.now()[:10]}','Service ownership or expiry requires review',r['name']+': '+', '.join(r['issues']),'/workbench')
    return {'overdue_items':total,'reminder_items':count}
