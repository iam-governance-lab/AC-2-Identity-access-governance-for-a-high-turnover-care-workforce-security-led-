"""Regression tests for concrete v10 defects and review operations."""
from datetime import timedelta
from unittest.mock import patch
import json, sqlite3, unittest
import assurance, audit, auth, compliance, config, database, enterprise, lifecycle, release_v10 as v10, workforce_v8
from security_workstream import ledger
from clock import utc_today
from test_web import WebTests

class Version10Tests(WebTests):
    def test_corrupt_evidence_blocks_business_change_before_commit(self):
        audit.record('SC1005',None,'BASELINE','PASS')
        with database.connect() as c:c.execute("UPDATE security_ledger SET tag='corrupt' WHERE sequence=1")
        before=lifecycle.get_employee_state('SC1001')
        with self.assertRaises(ledger.IntegrityError):lifecycle.mover('SC1001','Manager','North Wing','SC1005')
        self.assertEqual(before,lifecycle.get_employee_state('SC1001'))

    def test_business_change_and_audit_rollback_together(self):
        audit.record('SC1005',None,'BASELINE','PASS')
        before=lifecycle.get_employee_state('SC1001')
        with patch.object(audit,'record_on',side_effect=RuntimeError('simulated evidence write failure')):
            with self.assertRaises(RuntimeError):lifecycle.mover('SC1001','Manager','North Wing','SC1005')
        self.assertEqual(before,lifecycle.get_employee_state('SC1001'))
        self.assertEqual(ledger.verify()['status'],'PASS')

    def test_final_state_is_integrity_protected(self):
        corr=audit.record('SC1005','SC1001','V2','PASS',final_state={'role':'Nurse'})
        with database.connect() as c:c.execute("UPDATE audit_events SET final_state='{}' WHERE correlation_id=?",(corr,))
        with self.assertRaises(ledger.IntegrityError):ledger.verify()

    def test_checkpoint_failure_recovers_committed_evidence(self):
        audit.record('SC1005',None,'BASELINE','PASS')
        with patch.object(ledger,'_save_head',side_effect=OSError('simulated full disk')):
            with self.assertRaises(ledger.IntegrityError):audit.record('SC1005',None,'RECOVER_ME','PASS')
        self.assertTrue(ledger.pending_path().exists())
        self.assertEqual(ledger.verify()['status'],'PASS')
        self.assertFalse(ledger.pending_path().exists())
        with database.connect() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM audit_events WHERE action='RECOVER_ME'").fetchone()[0],1)

    def test_checkpoint_journal_tampering_denied(self):
        audit.record('SC1005',None,'BASELINE','PASS')
        ledger.pending_path().write_text('{"payload":{},"tag":"forged"}')
        with self.assertRaises(ledger.IntegrityError):ledger.verify()

    def test_batched_verification_uses_constant_number_of_selects(self):
        with database.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            for i in range(200):audit.record_on(c,'SC1005',None,'BENCHMARK','PASS',{'index':i})
        statements=[]
        with database.connect() as c:
            c.set_trace_callback(statements.append);ledger._verify(c,ledger._key())
        selects=[s for s in statements if s.startswith('SELECT')]
        self.assertEqual(len(selects),2)

    def test_invalid_and_expired_employment_dates_fail_closed(self):
        with database.connect() as c:row=dict(c.execute("SELECT * FROM employees WHERE employee_id='SC1001'").fetchone())
        for update in ({'start_date':'not-a-date'},{'end_date':'zbad'},{'end_date':str(utc_today()-timedelta(days=1))},{'worker_type':'Agency','end_date':None}):
            self.assertFalse(auth.employment_valid(row|update),update)

    def test_case_insensitive_email_uniqueness(self):
        with database.connect() as c:
            with self.assertRaises(sqlite3.IntegrityError):c.execute("UPDATE employees SET email='SARAH.KHAN@SUNHAVEN.TEST' WHERE employee_id='SC1003'")

    def test_compliance_repeated_scan_preserves_finding_ids(self):
        compliance.run_checks()
        with database.connect() as c:first=[tuple(r) for r in c.execute('SELECT finding_id,employee_id,rule_id FROM compliance_findings')]
        compliance.run_checks()
        with database.connect() as c:second=[tuple(r) for r in c.execute('SELECT finding_id,employee_id,rule_id FROM compliance_findings')]
        self.assertEqual(first,second)

    def test_suspended_cloud_identity_is_a_critical_finding(self):
        with database.connect() as c:c.execute("UPDATE employees SET status='Suspended' WHERE employee_id='SC1003'")
        self.assertTrue(any(x['rule_id']=='C01' and x['employee_id']=='SC1003' for x in compliance.run_checks(False)))

    def test_stale_cover_no_longer_blocks_new_request(self):
        data={'facility':'North Wing','minutes':'60','reason':'Cover a fictional care shift.'}
        old=assurance.request_cover('SC1001',data)
        with database.connect() as c:c.execute('UPDATE cover_requests SET created_at=? WHERE id=?',(str(utc_today()-timedelta(days=2))+'T00:00:00',old))
        new=assurance.request_cover('SC1001',data)
        self.assertNotEqual(new,old)
        with database.connect() as c:self.assertEqual(c.execute('SELECT status FROM cover_requests WHERE id=?',(old,)).fetchone()[0],'Expired')

    def test_stale_package_no_longer_blocks_new_request(self):
        old=enterprise.request_package('SC1001','care-learning','Fictional training workspace.')
        with database.connect() as c:c.execute('UPDATE package_requests SET created_at=? WHERE id=?',(str(utc_today()-timedelta(days=8))+'T00:00:00',old))
        self.assertNotEqual(old,enterprise.request_package('SC1001','care-learning','Fictional training workspace.'))
        with database.connect() as c:self.assertEqual(c.execute('SELECT status FROM package_requests WHERE id=?',(old,)).fetchone()[0],'Rejected')

    def test_review_refresh_retains_pending_and_audits_old_snapshot(self):
        workforce_v8.create_campaign('SC1005')
        with database.connect() as c:item=c.execute("SELECT id FROM campaign_items WHERE employee_id='SC1001'").fetchone()[0]
        lifecycle.mover('SC1001','Nurse','North Wing','SC1005')
        with self.assertRaises(ValueError):workforce_v8.review('SC1002',item,'Retain','Current access confirmed.')
        with self.assertRaises(PermissionError):v10.refresh_review('SC1002',item,'Manager cannot refresh snapshots.')
        v10.refresh_review('SC1005',item,'Verified the approved site transfer.')
        with database.connect() as c:
            self.assertEqual(c.execute('SELECT decision FROM campaign_items WHERE id=?',(item,)).fetchone()[0],'Pending')
            e=json.loads(c.execute("SELECT details FROM audit_events WHERE action='CAMPAIGN_SNAPSHOT_REFRESHED'").fetchone()[0]);self.assertEqual(e['before'][1],'Ashford Main');self.assertEqual(e['after'][1],'North Wing')
        workforce_v8.review('SC1002',item,'Retain','Current access confirmed.')

    def test_service_owner_reassignment_requires_operator_and_valid_owner(self):
        enterprise.add_service('SC1005',{'name':'Test Reporting','kind':'Service','owner_id':'SC1002','scopes':'metrics.read','days':'30'})
        with database.connect() as c:sid=c.execute('SELECT id FROM service_identities').fetchone()[0];c.execute("UPDATE employees SET status='Leaver' WHERE employee_id='SC1002'")
        with database.connect() as c:self.assertIn('Owner inactive or expired',v10.service_health(c)[0]['issues'])
        with self.assertRaises(PermissionError):v10.reassign_owner('SC1003',sid,'SC1005','Unauthorised reassignment attempt.')
        with self.assertRaises(PermissionError):v10.reassign_owner('SC1005',sid,'SC1007','Inactive owner must be rejected.')
        v10.reassign_owner('SC1005',sid,'SC1005','Owner left; accountability transferred.')
        with database.connect() as c:self.assertEqual(v10.service_health(c)[0]['issues'],[])

    def test_withdraw_own_request_then_resubmit(self):
        self.login('SC1001');self.request();rid=self.latest_request()
        self.assertEqual(self.call('/workbench/action','POST',{'action':'cancel','id':rid,'reason':'My planned transfer was cancelled.'})['status'],303)
        self.assertEqual(self.request()['status'],303)
        self.login('SC1003')
        self.assertEqual(self.call('/workbench/action','POST',{'action':'cancel','id':self.latest_request(),'reason':'Another worker cannot withdraw this.'})['status'],403)

    def test_workbench_pagination_finds_every_certification(self):
        workforce_v8.create_campaign('SC1005')
        with database.connect() as c:
            total,first=v10.work_queue(c,kind='Certification',size=10)
            seen=[]
            for p in range(1,(total+9)//10+1):seen.extend(x['id'] for x in v10.work_queue(c,kind='Certification',size=10,page=p)[1])
        self.assertEqual(len(seen),total);self.assertEqual(len(set(seen)),total)
        self.login();self.assertEqual(self.call('/workbench')['status'],200)
        self.assertEqual(self.call('/workbench?page=0')['status'],400)
        self.login('SC1003');self.assertEqual(self.call('/workbench')['status'],403)

    def test_reminders_idempotent_for_same_day(self):
        with database.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            c.execute("UPDATE access_requests SET created_at='2020-01-01' WHERE status='Pending'")
            v10.reminders(c,'SC1005');count=c.execute('SELECT COUNT(*) FROM notification_outbox').fetchone()[0]
            self.assertGreater(count,0)
            v10.reminders(c,'SC1005');self.assertEqual(c.execute('SELECT COUNT(*) FROM notification_outbox').fetchone()[0],count)

    def test_expanded_seed_counts_idempotence_and_foreign_keys(self):
        with patch.object(config,'DEMO_PROFILE','expanded'):database.init_db(reset=True)
        with database.connect() as c:
            for table,n in [('employees',320),('residents',90),('work_notes',869),('service_identities',3)]:self.assertEqual(c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],n)
            self.assertEqual(list(c.execute('PRAGMA foreign_key_check')),[])
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        with patch.object(config,'DEMO_PROFILE','expanded'):database.init_db()
        with database.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM employees').fetchone()[0],320)
        self.login();self.assertIn('320 results',self.call('/employees')['body']);self.assertIn('SC1180',self.call('/employees?q=SC1180')['body'])
        self.assertIn('DEMO-V10',self.call('/notes?employee=SC1180')['body'])
        data=json.loads(self.call('/api/v1/employees?page=2&page_size=25')['body']);self.assertEqual(data['total'],320);self.assertEqual(len(data['data']),25)

    def test_existing_database_never_receives_expanded_fixtures(self):
        with patch.object(config,'DEMO_PROFILE','expanded'):database.init_db()
        with database.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM employees').fetchone()[0],42)

    def test_full_history_notes_search_and_directory_filters(self):
        with database.connect() as c:
            c.executemany('INSERT INTO work_notes(employee_id,author_id,category,body) VALUES (?, ?, ?, ?)',[('SC1003','SC1005','General','Newer filler notes for pagination')]*110)
        self.login();self.assertIn('Induction completed',self.call('/notes?employee=SC1008')['body'])
        page=self.call('/employees?status=Leaver&facility=North+Wing');self.assertEqual(page['status'],200);self.assertNotIn('Sarah Khan</span>',page['body'])

for name in dir(WebTests):
    if name.startswith('test_') and name not in Version10Tests.__dict__:setattr(Version10Tests,name,None)
del WebTests
