"""Permission boundaries and persistence for the v4 workspace."""
from test_web import WebTests
import database, experience

class ExperienceTests(WebTests):
    def test_workspace_pages_and_assets(self):
        self.login()
        for path in ['/notifications','/onboarding','/reports','/search?q=Sarah','/static/theme.js','/static/workspace.css']:
            with self.subTest(path=path):self.assertEqual(self.call(path)['status'],200)
        self.assertIn('Sarah',self.call('/search?q=Sarah')['body'])
        self.assertEqual(self.call('/reports?facility=invalid')['status'],400)
    def test_worker_scope(self):
        self.login('SC1003')
        for path in ['/onboarding','/reports','/reports?format=pdf']:
            self.assertEqual(self.call(path)['status'],403)
        page=self.call('/search?q=Sarah')['body']
        self.assertNotIn('/employees/SC1001',page)
        self.assertNotIn('Review overdue',self.call('/notifications')['body'])
        with database.connect() as c:
            other=c.execute("SELECT request_id FROM access_requests WHERE employee_id!='SC1003' LIMIT 1").fetchone()[0]
        self.assertEqual(self.call(f'/requests/{other}')['status'],403)
        self.assertEqual(self.call('/notifications/read','POST',{'key':f'request:{other}'})['status'],404)
    def test_checklist_save_reopen_and_no_grant(self):
        self.login()
        with database.connect() as c:before=tuple(c.execute("SELECT approved_role,facility FROM employees WHERE employee_id='SC1001'").fetchone())
        d={'employee_id':'SC1001','evidence':'Induction records verified by operator.','step_0':'1','step_1':'1'}
        self.assertEqual(self.call('/onboarding','POST',d)['status'],303)
        with database.connect() as c:
            self.assertEqual(c.execute("SELECT SUM(completed) FROM onboarding_steps WHERE employee_id='SC1001'").fetchone()[0],2)
            self.assertEqual(tuple(c.execute("SELECT approved_role,facility FROM employees WHERE employee_id='SC1001'").fetchone()),before)
        del d['step_1'];self.call('/onboarding','POST',d)
        with database.connect() as c:self.assertEqual(c.execute("SELECT SUM(completed) FROM onboarding_steps WHERE employee_id='SC1001'").fetchone()[0],1)
        self.login('SC1004');self.assertEqual(self.call('/onboarding','POST',d)['status'],403)
    def test_notification_reads_are_personal(self):
        self.login()
        with database.connect() as c:user=dict(c.execute("SELECT * FROM employees WHERE employee_id='SC1005'").fetchone())
        key=experience.alerts(user)[0]['key']
        self.assertEqual(self.call('/notifications/read','POST',{'key':key})['status'],303)
        self.assertTrue(next(a for a in experience.alerts(user) if a['key']==key)['read'])
        with database.connect() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM notification_reads WHERE employee_id='SC1002'").fetchone()[0],0)
    def test_filtered_pdf_and_search_escape(self):
        self.login()
        r=self.call('/reports?facility=North+Wing&status=Active&format=pdf')
        self.assertEqual(r['status'],200);self.assertTrue(r['body'].startswith('%PDF-1.4'))
        self.assertIn('Facility: North Wing',r['body']);self.assertIn('Status: Active',r['body'])
        self.assertIn(('Content-Type','application/pdf'),r['headers'])
        self.assertNotIn('<script>x</script>',self.call('/search?q=%3Cscript%3Ex%3C/script%3E')['body'])
        self.assertIn('No matching records',self.call('/search?q=%25%25')['body'])
    def test_own_history_and_checklist_validation(self):
        self.login('SC1001');self.request();rid=self.latest_request()
        self.assertEqual(self.call(f'/requests/{rid}')['status'],200)
        self.login();self.assertEqual(self.call('/onboarding','POST',{'employee_id':'SC1001','evidence':'short'})['status'],400)

# Reuse request/session fixtures without running the parent suite twice.
for name in dir(WebTests):
    if name.startswith('test_') and name not in ExperienceTests.__dict__:setattr(ExperienceTests,name,None)
del WebTests
