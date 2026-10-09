import test_web
from unittest.mock import patch
import database,governance,lifecycle

class GovernanceTests(test_web.WebTests):
    # Inherit request helpers; avoid duplicating the inherited tests in this class.
    def approved(self):
        self.login('SC1001');self.request();rid=self.latest_request()
        self.login('SC1002');self.decide(rid);return rid
    def test_execution_atomic_and_once(self):
        rid=self.approved();governance.execute_request(rid,'SC1005')
        state=lifecycle.get_employee_state('SC1001')
        self.assertEqual(state['actual_roles'],['Manager']);self.assertEqual(state['active_assignments'],[])
        with self.assertRaises(ValueError):governance.execute_request(rid,'SC1005')
    def test_stale_approval_denied(self):
        rid=self.approved()
        with database.connect() as c:c.execute("UPDATE employees SET facility='South Wing' WHERE employee_id='SC1001'")
        with self.assertRaises(ValueError):governance.execute_request(rid,'SC1005')
    def test_expired_approval_denied(self):
        rid=self.approved()
        with database.connect() as c:c.execute("UPDATE access_requests SET decided_at='2000-01-01' WHERE request_id=?",(rid,))
        with self.assertRaises(ValueError):governance.execute_request(rid,'SC1005')
    def test_assignment_facility_and_role(self):
        with self.assertRaises(ValueError):governance.operate('assign',{'employee_id':'SC1003','resident_id':'R001','reason':'Roster assignment required'},'SC1005')
        governance.operate('assign',{'employee_id':'SC1003','resident_id':'R004','reason':'Roster assignment required'},'SC1005')
        self.assertIn('R004',lifecycle.get_employee_state('SC1003')['active_assignments'])
        governance.operate('unassign',{'employee_id':'SC1003','resident_id':'R004','reason':'Roster assignment removed'},'SC1005')
        self.assertNotIn('R004',lifecycle.get_employee_state('SC1003')['active_assignments'])
    def test_sessions_revoked(self):
        self.login('SC1001');governance.operate('revoke',{'employee_id':'SC1001','reason':'Investigating a lost device'},'SC1005')
        self.assertEqual(self.call('/')['status'],303)
    def test_task_and_review_closure(self):
        governance.operate('task',{'employee_id':'SC1001','owner_id':'SC1005','title':'Verify unnecessary access','priority':'High','reason':'Investigate the access review finding'},'SC1002')
        governance.operate('task_update',{'task_id':'1','status':'Resolved','reason':'Verified account roles against current roster'},'SC1005')
        with database.connect() as c:
            self.assertEqual(c.execute('SELECT status FROM remediation_tasks').fetchone()[0],'Resolved')
            rid=c.execute("INSERT INTO access_reviews(employee_id,reviewer_id,decision,reason,review_date,remediation_status) VALUES ('SC1003','SC1002','Remove','Remove old access',date('now'),'Pending')").lastrowid
        with self.assertRaises(ValueError):governance.operate('close_review',{'review_id':rid,'reason':'Attempted closure before removal'},'SC1002')
        lifecycle.leaver('SC1003','SC1005')
        governance.operate('close_review',{'review_id':rid,'reason':'Offboarding checked and access removed'},'SC1002')
    def test_operation_permissions_and_page(self):
        self.login('SC1004');self.assertEqual(self.call('/operations')['status'],200)
        self.assertEqual(self.call('/operations','POST',{'action':'revoke','employee_id':'SC1001','reason':'Attempted auditor session change'})['status'],403)
        self.login();self.assertEqual(self.call('/employees/SC1001/move','POST',{'new_role':'Manager','new_facility':'North Wing','mode':'apply'})['status'],409)
    def test_audit_failure_rolls_back_access_change(self):
        rid=self.approved()
        with patch.object(governance,'event',side_effect=RuntimeError('audit write failed')):
            with self.assertRaises(RuntimeError):governance.execute_request(rid,'SC1005')
        self.assertEqual(lifecycle.get_employee_state('SC1001')['approved_role'],'Nurse')
        with database.connect() as c:self.assertEqual(c.execute('SELECT status FROM access_requests WHERE request_id=?',(rid,)).fetchone()[0],'Approved')

# Only new tests in this subclass; inherited helper methods remain usable.
for name in dir(test_web.WebTests):
    if name.startswith('test_') and name not in GovernanceTests.__dict__:setattr(GovernanceTests,name,None)
