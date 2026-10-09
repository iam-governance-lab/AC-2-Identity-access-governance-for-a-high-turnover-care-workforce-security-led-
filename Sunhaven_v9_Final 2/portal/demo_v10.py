"""Expanded fictional presentation dataset; never added to an existing database."""
from datetime import timedelta
from clock import utc_today
import json
import config, enterprise, assurance
from demo_data import NAMES

def seed(c,workers=180):
    today=utc_today();stamp=enterprise.now()
    for i in range(43,workers+1):
        eid=f'SC{1000+i}';name=NAMES[(i-43)%len(NAMES)]+' '+str(i)
        role=('Nurse','CareWorker','AgencyWorker','CareWorker','Manager','Nurse','CareWorker')[i%7]
        worker='Agency' if role=='AgencyWorker' else ('ThirdParty' if i%13==0 else 'Casual' if i%3==0 else 'Permanent')
        facility=config.FACILITIES[i%3];status='Leaver' if i%19==0 else 'Active'
        end=str(today+timedelta(days=(i%9)*6+1)) if worker=='Agency' else None
        if status=='Leaver':end=str(today-timedelta(days=14))
        enabled=int(status=='Active')
        c.execute('''INSERT INTO employees(employee_id,name,email,worker_type,approved_role,facility,status,manager_sponsor,start_date,end_date,entra_object_id,cloud_enabled,cloud_role,admin_privilege)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)''',(eid,name,f'demo.worker.{i}@sunhaven.test',worker,role,facility,status,'SC1002',str(today-timedelta(days=20+i)),end,'mock-'+eid.lower(),enabled,role if enabled else None))
        assurance.sync_team(c,eid,facility)
        if enabled:
            c.execute('INSERT INTO employee_roles VALUES (?,?)',(eid,role))
            for kind in (('Safeguarding','Professional registration') if role=='Nurse' else ('Safeguarding',)):
                days=-5 if i%17==0 else 12 if i%11==0 else 180
                c.execute('INSERT INTO qualifications(employee_id,kind,expires_on,evidence_ref,verified_by,verified_at) VALUES (?,?,?,?,?,?)',(eid,kind,str(today+timedelta(days=days)),'DEMO-V10: synthetic qualification','SC1005',stamp))
            if i%4!=0:c.execute('INSERT INTO login_activity VALUES (?,?)',(eid,str(today-timedelta(days=i%20))+'T08:00:00'))
        else:c.execute('INSERT INTO blocked_users VALUES (?,?,?)',(eid,stamp,'DEMO-V10: fictional contract ended'))
        for category,body in [('Onboarding','Fictional induction and approved site recorded; manager confirms minimum necessary access.'),('Handover','Synthetic shift handover: verify current roster and qualifications before the next assignment.'),('Access review','Demonstration review preparation: compare assigned permissions to current duties and document the decision.')]:
            c.execute('INSERT INTO work_notes(employee_id,author_id,category,body,created_at) VALUES (?,?,?,?,?)',(eid,'SC1005',category,'DEMO-V10: '+body,stamp))
    for i in range(31,91):
        facility=config.FACILITIES[i%3];rid=f'R{i:03}'
        c.execute('INSERT INTO residents VALUES (?,?,?,?)',(rid,f'Resident Demo {i:02}',facility,f'Room {i:02}'))
        worker=c.execute("SELECT employee_id FROM employees WHERE facility=? AND approved_role IN ('Nurse','CareWorker') AND status='Active' ORDER BY employee_id DESC LIMIT 1",(facility,)).fetchone()
        c.execute('INSERT INTO assignments(employee_id,resident_id,active) VALUES (?,?,1)',(worker[0],rid))
    for i,owner in enumerate(('SC1002','SC1005','SC1007'),1):
        c.execute('INSERT INTO service_identities(name,kind,owner_id,scopes,expires_at,status,created_at) VALUES (?,?,?,?,?,?,?)',(f'DEMO-V10 reporting service {i}','Service',owner,json.dumps(['metrics.read']),str(today+timedelta(days=20))+'T12:00:00','Active',stamp))
    for i,eid in enumerate(('SC1008','SC1010','SC1014','SC1016'),1):
        c.execute("INSERT INTO remediation_tasks(employee_id,title,priority,owner_id,status,evidence,created_by,created_at,updated_at) VALUES (?,?,?,'SC1002','Open',?,'SC1005',?,?)",(eid,'DEMO-V10: confirm access after roster change','High' if i%2 else 'Medium','Fictional scenario; investigate before taking action.',str(today-timedelta(days=4))+'T09:00:00',stamp))
