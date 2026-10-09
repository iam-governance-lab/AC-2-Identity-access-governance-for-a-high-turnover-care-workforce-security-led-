import csv,io,unittest,tempfile
from pathlib import Path
import database,workforce_v8,enterprise,scheduler,audit_export
from test_web import WebTests
from security_workstream import ledger
class WorkforceTests(WebTests):
    def roster(self,eid='SC1001',status='Leaver',end=''):
        with database.connect() as c:e=c.execute('SELECT * FROM employees WHERE employee_id=?',(eid,)).fetchone()
        out=io.StringIO();w=csv.writer(out);w.writerow(workforce_v8.FIELDS);w.writerow([eid,e['email'],e['approved_role'],e['facility'],status,end]);return out.getvalue()
    def second_operator(self):
        with database.connect() as c:
            c.execute("UPDATE employees SET approved_role='IAMOperator' WHERE employee_id='SC1004'")
            c.execute("INSERT INTO employee_roles VALUES ('SC1004','IAMOperator')")
    def test_staged_leaver_requires_separate_people_revokes_session(self):
        self.login('SC1001');rid=workforce_v8.stage('SC1002',self.roster())
        with self.assertRaises(PermissionError):workforce_v8.decide('SC1002',rid,'Approved','Independent reviewer is required.')
        workforce_v8.decide('SC1005',rid,'Approved','Fictional staff roster independently checked.')
        with self.assertRaises(PermissionError):workforce_v8.apply('SC1005',rid)
        self.second_operator();changes=workforce_v8.apply('SC1004',rid)
        self.assertIn('DISABLE_LEAVER',[c['action'] for c in changes])
        with database.connect() as c:
            self.assertEqual(tuple(c.execute("SELECT status,cloud_enabled FROM employees WHERE employee_id='SC1001'").fetchone()),('Leaver',0))
            self.assertEqual(c.execute("SELECT count(*) FROM sessions WHERE employee_id='SC1001'").fetchone()[0],0)
        self.assertEqual(self.call('/residents')['status'],303)
        with self.assertRaises(ValueError):workforce_v8.apply('SC1004',rid)
        self.assertEqual(ledger.verify()['status'],'PASS')
    def test_stale_snapshot_bad_email_and_duplicate_rejected(self):
        rid=workforce_v8.stage('SC1002',self.roster('SC1006','Active','2099-12-31'))
        workforce_v8.decide('SC1005',rid,'Approved','Fictional staff roster independently checked.');self.second_operator()
        with database.connect() as c:c.execute("UPDATE employees SET facility='North Wing' WHERE employee_id='SC1006'")
        with self.assertRaises(ValueError):workforce_v8.apply('SC1004',rid)
        raw=self.roster()
        with self.assertRaises(ValueError):workforce_v8.stage('SC1002',raw.replace('sarah.khan@sunhaven.test','wrong@sunhaven.test'))
        with self.assertRaises(ValueError):workforce_v8.stage('SC1002',raw+raw.splitlines()[1]+'\n')
    def test_agency_end_date_requires_approval(self):
        rid=workforce_v8.stage('SC1002',self.roster('SC1006','Active','2099-12-31'))
        with database.connect() as c:self.assertNotEqual(c.execute("SELECT end_date FROM employees WHERE employee_id='SC1006'").fetchone()[0],'2099-12-31')
        workforce_v8.decide('SC1005',rid,'Approved','Fictional staff roster independently checked.');self.second_operator();workforce_v8.apply('SC1004',rid)
        with database.connect() as c:self.assertEqual(c.execute("SELECT end_date FROM employees WHERE employee_id='SC1006'").fetchone()[0],'2099-12-31')
    def test_campaign_idempotence_independent_review_and_followup(self):
        cid=workforce_v8.create_campaign('SC1005');self.assertEqual(workforce_v8.create_campaign('SC1005'),cid)
        with database.connect() as c:
            own=c.execute("SELECT id FROM campaign_items WHERE campaign_id=? AND employee_id='SC1002'",(cid,)).fetchone()[0]
            target=c.execute("SELECT id FROM campaign_items WHERE campaign_id=? AND employee_id='SC1001'",(cid,)).fetchone()[0]
        with self.assertRaises(PermissionError):workforce_v8.review('SC1002',own,'Retain','Cannot review your own access.')
        rid=enterprise.request_package('SC1001','quality-review','Require aggregate synthetic quality metrics.')
        enterprise.decide_package('SC1002',rid,'Approved','Business need confirmed by independent reviewer.')
        workforce_v8.review('SC1002',target,'Remove','Temporary package no longer needed by worker.')
        with database.connect() as c:
            self.assertEqual(c.execute('SELECT status FROM package_requests WHERE id=?',(rid,)).fetchone()[0],'Revoked')
            self.assertIsNotNone(c.execute("SELECT task_id FROM remediation_tasks WHERE employee_id='SC1001' AND status='Open'").fetchone())
        with self.assertRaises(ValueError):workforce_v8.review('SC1002',target,'Retain','Second decision must fail.')
    def test_scheduler_and_export(self):
        self.assertTrue(scheduler.preview()['campaign_due'])
        with self.assertRaises(PermissionError):scheduler.execute('SC1003')
        first=scheduler.execute('SC1005');self.assertEqual(first['campaign_id'],scheduler.execute('SC1005')['campaign_id'])
        with tempfile.TemporaryDirectory() as tmp:
            report=audit_export.export('SC1004',Path(tmp)/'audit.ndjson')
            self.assertGreater(report['events'],0);self.assertEqual(report['ledger'],'PASS')
            with self.assertRaises(ValueError):audit_export.export('SC1004',Path(tmp)/'audit.ndjson')
            with self.assertRaises(PermissionError):audit_export.export('SC1003',Path(tmp)/'other.ndjson')
    def test_web_pages_and_csrf(self):
        self.login('SC1005')
        for p in ['/workforce-sync','/campaigns']:self.assertEqual(self.call(p)['status'],200)
        self.assertEqual(self.call('/workforce-action','POST',{'action':'campaign'},csrf=False)['status'],403)
        self.login('SC1003');self.assertEqual(self.call('/workforce-sync')['status'],403)
        self.assertEqual(self.call('/workforce-action','POST',{'action':'campaign'})['status'],403)
for name in dir(WebTests):
    if name.startswith('test_') and name not in WorkforceTests.__dict__:setattr(WorkforceTests,name,None)
del WebTests
