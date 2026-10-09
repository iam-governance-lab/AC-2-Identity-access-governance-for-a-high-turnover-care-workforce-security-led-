"""Read-only Sunhaven state adapter and explainable six-scenario control model."""
import database

SCENARIOS=[
 ('STOLEN_CREDENTIAL','Stolen credentials','MFA policy',5),
 ('SHARED_SESSION','Shared active session','Short session + logout',4),
 ('FORMER_WORKER','Former worker still enabled','Leaver block',5),
 ('EXCESS_PRIVILEGE','Excessive care access','Role + assignment checks',4),
 ('PRIVILEGED_COMPROMISE','Privileged account compromise','Operator separation',5),
 ('UNMANAGED_DEVICE','Unmanaged device','Device trust (future work)',3),
]
def state_snapshot():
    with database.connect() as conn:
        workers=conn.execute('SELECT employee_id,approved_role,status,cloud_enabled,admin_privilege FROM employees').fetchall()
        assignments=conn.execute('SELECT COUNT(*) FROM assignments WHERE active=1').fetchone()[0]
        blocked={r[0] for r in conn.execute('SELECT employee_id FROM blocked_users')}
        violations=[r[0] for r in conn.execute('''SELECT a.employee_id FROM assignments a JOIN employees e ON e.employee_id=a.employee_id JOIN residents r ON r.resident_id=a.resident_id WHERE a.active=1 AND (e.status!="Active" OR e.facility!=r.facility OR e.approved_role NOT IN ("Nurse","CareWorker","AgencyWorker"))''')]
    return {'workers':len(workers),'active_assignments':assignments,
        'enabled_former_workers':[r['employee_id'] for r in workers if r['status'] in ('Leaver','Inactive') and r['cloud_enabled'] and r['employee_id'] not in blocked],
        'unexpected_admin':[r['employee_id'] for r in workers if r['admin_privilege'] and r['approved_role']!='IAMOperator'],
        'invalid_assignments':violations}
def compare(snapshot=None):
    state=snapshot if snapshot is not None else state_snapshot()
    rows=[]
    for rule,title,control,weight in SCENARIOS:
        implemented=rule not in ('UNMANAGED_DEVICE','STOLEN_CREDENTIAL','SHARED_SESSION')
        if rule=='FORMER_WORKER':implemented=not bool(state['enabled_former_workers'])
        if rule=='PRIVILEGED_COMPROMISE':implemented=False # Role separation does not stop takeover of a privileged account.
        if rule=='EXCESS_PRIVILEGE':implemented=not bool(state['invalid_assignments'])
        rows.append({'id':rule,'scenario':title,'control':control,'baseline':'OPEN','controlled':'BLOCKED' if implemented else 'OPEN',
          'baseline_risk':weight,'controlled_risk':0 if implemented else weight,'evidence':'Sunhaven state snapshot' if rule in ('FORMER_WORKER','PRIVILEGED_COMPROMISE','EXCESS_PRIVILEGE') else 'Design simulation only'})
    return {'source':'local synthetic workforce snapshot','state':state,'scenarios':rows,
      'baseline_risk':sum(x['baseline_risk'] for x in rows),'controlled_risk':sum(x['controlled_risk'] for x in rows)}
