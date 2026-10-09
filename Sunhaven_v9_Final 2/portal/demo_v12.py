"""Fresh expanded fixture only. Application deliveries are deliberately local."""
from datetime import datetime,timedelta
import enterprise,release_v12 as v12

def seed(c):
    now=enterprise.now();start=(datetime.fromisoformat(now)-timedelta(hours=1)).isoformat(timespec='seconds');end=(datetime.fromisoformat(now)+timedelta(hours=7)).isoformat(timespec='seconds')
    workers=c.execute("SELECT * FROM employees WHERE status='Active' AND cloud_enabled=1 ORDER BY employee_id").fetchall()
    count=0
    for e in workers:
        try:snapshot=enterprise.snapshot(c,e['employee_id'])
        except PermissionError:continue
        eid=e['employee_id'];count+=1
        if count<=160:
            approver='SC1005' if eid=='SC1002' else 'SC1002'
            c.execute("INSERT INTO entitlement_requests(employee_id,entitlement,status,reason,minutes,snapshot,created_at,decided_by,decided_at,decision_reason,expires_at) VALUES (?,'learning','Approved','V12 fictional mandatory learning assignment',10080,?,?,?,?,'V12 synthetic independent approval',?)",(eid,snapshot,now,approver,now,(datetime.fromisoformat(now)+timedelta(days=7)).isoformat(timespec='seconds')))
            if count%4:c.execute('INSERT INTO observed_entitlements(employee_id,entitlement,enabled,synced_at) VALUES (?,?,1,?)',(eid,'learning',now))
        if count<=80 and e['approved_role'] in ('Nurse','CareWorker','AgencyWorker','Manager') and (not e['end_date'] or end[:10]<=e['end_date']):
            c.execute('INSERT INTO shift_assignments(employee_id,facility,starts_at,ends_at,created_by,reason,created_at) VALUES (?,?,?,?,?,?,?)',(eid,e['facility'],start,end,'SC1005','V12 fictional current care shift',now))
    # An intentionally unapproved local grant makes drift/reconciliation visible.
    c.execute("INSERT INTO observed_entitlements(employee_id,entitlement,enabled,synced_at) VALUES ('SC1003','roster-view',1,?)",(now,))
    v12.queue(c,'SC1005','SC1003','roster-view')
    for i,name in enumerate(('Alex Morgan','Priya Das','Jordan Malik','Samira Khan','Noah Reed')):
        c.execute('INSERT INTO sponsor_intakes(sponsor_id,name,email,worker_type,facility,starts_on,ends_on,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?)',('SC1002',name,f'v12.intake.{i}@sunhaven.test','Agency' if i%2 else 'ThirdParty','Ashford Main',now[:10],(datetime.fromisoformat(now)+timedelta(days=30)).date().isoformat(),'V12 fictional replacement workforce intake',now))
