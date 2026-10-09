"""Agency expiry is atomic, permission gated, stale safe and idempotent."""
from pathlib import Path
import tempfile,unittest
import config,database,automation
from test_web import WebTests
from security_workstream import ledger

class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=config.DB_PATH
        config.DB_PATH=Path(self.tmp.name)/'test.db';database.init_db()
    def tearDown(self):config.DB_PATH=self.old;self.tmp.cleanup()
    def test_run_revokes_expired_access_and_is_idempotent(self):
        plan=automation.preview();self.assertIn('SC1006',[x['employee_id'] for x in plan['expired']])
        with database.connect() as c:
            before=c.execute("SELECT COUNT(*) FROM sessions WHERE employee_id='SC1006'").fetchone()[0]
            c.execute("INSERT INTO sessions VALUES ('temporary', 'SC1006','2099-01-01T00:00:00','2026-01-01T00:00:00')")
        targets=automation.execute('SC1005',plan['fingerprint'],'Contract expiry validated against workforce dates.')
        self.assertIn('SC1006',targets)
        with database.connect() as c:
            person=c.execute("SELECT status,cloud_enabled,cloud_role FROM employees WHERE employee_id='SC1006'").fetchone()
            self.assertEqual(tuple(person),('Suspended',0,None))
            self.assertEqual(c.execute("SELECT COUNT(*) FROM employee_roles WHERE employee_id='SC1006'").fetchone()[0],0)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM sessions WHERE employee_id='SC1006'").fetchone()[0],0)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM assignments WHERE employee_id='SC1006' AND active=1").fetchone()[0],0)
            self.assertIsNotNone(c.execute("SELECT 1 FROM blocked_users WHERE employee_id='SC1006'").fetchone())
        self.assertEqual(ledger.verify()['status'],'PASS')
        plan=automation.preview();self.assertEqual(plan['expired'],[])
        self.assertEqual(automation.execute('SC1005',plan['fingerprint'],'Daily review completed with no overdue contracts.'),[])
    def test_stale_plan_and_unprivileged_actor_change_nothing(self):
        plan=automation.preview()
        with self.assertRaises(ValueError):automation.execute('SC1005','0'*64,'Reason long enough for run.')
        with self.assertRaises(PermissionError):automation.execute('SC1003',plan['fingerprint'],'Reason long enough for run.')
        with database.connect() as c:
            self.assertEqual(c.execute("SELECT cloud_enabled FROM employees WHERE employee_id='SC1006'").fetchone()[0],1)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM automation_runs').fetchone()[0],0)

class AutomationWebTests(WebTests):
    def test_access_and_csrf(self):
        self.login('SC1005')
        self.assertEqual(self.call('/automation')['status'],200)
        self.assertEqual(self.call('/policies')['status'],200)
        token=automation.preview()['fingerprint']
        self.assertEqual(self.call('/automation','POST',{'fingerprint':token,'reason':'Approved scheduled contract expiry.'},csrf=False)['status'],403)
        self.assertEqual(self.call('/automation','POST',{'fingerprint':token,'reason':'Approved scheduled contract expiry.'})['status'],303)
        self.login('SC1004');self.assertEqual(self.call('/automation')['status'],200)
        self.assertEqual(self.call('/automation','POST',{'fingerprint':token,'reason':'Reason with enough detail.'})['status'],403)
        self.login('SC1003')
        self.assertEqual(self.call('/automation')['status'],403)
        self.assertEqual(self.call('/policies')['status'],403)
for name in dir(WebTests):
    if name.startswith('test_') and name not in AutomationWebTests.__dict__:setattr(AutomationWebTests,name,None)
del WebTests
