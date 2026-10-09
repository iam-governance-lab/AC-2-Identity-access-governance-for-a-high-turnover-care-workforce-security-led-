from clock import utc_today
from datetime import timezone
"""Deterministic fictional fixtures. Called only when seeding a NEW demo database."""
from datetime import date, datetime, timedelta
import json
import config

NAMES = ['Emma Brooks','Noah Williams','Olivia Tan','Liam Ahmed','Ava Martin','Ethan Clarke','Sophia Nguyen','Lucas Brown','Isla Davis','Leo Thomas','Amelia Scott','Henry Evans','Chloe Reed','Jack Morgan','Zoe Campbell','Oliver Hughes','Ella Mitchell','James Cooper','Lily Adams','William Turner','Ruby Collins','Mason Hill','Grace Baker','Aria Parker','Oscar Ward','Evie Wright','Samuel Green','Maya Foster','Hugo Ross','Nora Bennett','Adam King','Alice Wood','Finn Bell','Layla Young','Theo Cox']

def seed_extended(conn):
    today = utc_today()
    for i, name in enumerate(NAMES, 8):
        eid = f'SC{1000+i}'
        role = ['Nurse','CareWorker','CareWorker','AgencyWorker','Nurse','Manager','CareWorker'][i % 7]
        facility = config.FACILITIES[i % 3]
        status = 'Leaver' if i in (19,32,40) else 'Active'
        end = str(today + timedelta(days=(i % 5)*7+2)) if role == 'AgencyWorker' else None
        if status == 'Leaver': end = str(today-timedelta(days=12))
        enabled = int(status == 'Active')
        conn.execute('''INSERT INTO employees(employee_id,name,email,worker_type,approved_role,facility,status,manager_sponsor,start_date,end_date,entra_object_id,cloud_enabled,cloud_role,admin_privilege) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
          (eid,name,name.lower().replace(' ','.')+'@sunhaven.test','Agency' if role=='AgencyWorker' else ('Casual' if i%3==0 else 'Permanent'),role,facility,status,'SC1002',str(today-timedelta(days=30+i*6)),end,'mock-'+eid.lower(),enabled,role if enabled else None,0))
        if enabled:
            conn.execute('INSERT INTO employee_roles VALUES (?,?)',(eid,role))
            if i % 5 != 0:
                conn.execute('''INSERT INTO access_reviews(employee_id,reviewer_id,decision,reason,review_date,remediation_status) VALUES (?,?,?,?,?,?)''',(eid,'SC1002','Retain','DEMO: Position, facility and access verified against fictional roster.',str(today-timedelta(days=i % 60)),'Closed'))
        else:
            conn.execute('INSERT INTO blocked_users VALUES (?,?,?)',(eid,str(today),'DEMO: Contract ended; portal access removed.'))
        conn.execute('INSERT INTO work_notes(employee_id,author_id,category,body,created_at) VALUES (?,?,?,?,?)', (eid,'SC1005','Onboarding' if enabled else 'Offboarding','DEMO: '+('Induction completed. Assigned role checked against the approved workforce record. Next review due within 90 days.' if enabled else 'Access removed and handover completed. Retain the identity for audit history.'), str(today-timedelta(days=i%12))))
    for i in range(7,31):
        fac = config.FACILITIES[i%3]
        rid=f'R{i:03}'
        conn.execute('INSERT INTO residents VALUES (?,?,?,?)',(rid,f'Resident Demo {i:02}',fac,f'Room {i:02}'))
        worker=conn.execute("SELECT employee_id FROM employees WHERE facility=? AND approved_role IN ('CareWorker','Nurse') AND status='Active' ORDER BY employee_id DESC LIMIT 1",(fac,)).fetchone()
        if worker: conn.execute('INSERT INTO assignments(employee_id,resident_id,active) VALUES (?,?,1)',(worker['employee_id'],rid))
    for i,eid in enumerate(['SC1003','SC1008','SC1010','SC1014','SC1016','SC1018']):
        conn.execute('''INSERT INTO access_requests(employee_id,requested_role,facility,reason,status,decision_by,decision_note) VALUES (?,?,?,?,?,?,?)''',(eid,'Nurse' if i%2 else 'CareWorker',config.FACILITIES[i%3],'DEMO: Upcoming roster change; please review the minimum access needed.','Pending' if i<4 else 'Rejected',None if i<4 else 'SC1002',None if i<4 else 'DEMO: Training evidence required before this role change.'))
    for i in range(24):
        conn.execute('''INSERT INTO audit_events(actor_id,target_id,action,event_time,result,correlation_id,details) VALUES (?,?,?,?,?,?,?)''',('SC1005',f'SC{1008+i}','DEMO_FIXTURE', (datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(hours=3*i+1)).isoformat(timespec='seconds')+'Z','PASS',f'DEMO-{i+1:06}',json.dumps({'synthetic':True,'note':'Illustrative fixture, not evidence of an executed lifecycle action.'})))
    conn.commit()
