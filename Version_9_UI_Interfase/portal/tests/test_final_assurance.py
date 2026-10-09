from clock import utc_today
"""Security and end-to-end regression for final care-workforce controls."""
from datetime import date,timedelta
import hashlib, json, sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_web import WebTests
import assurance as a
import auth, config, database, enterprise, governance, lifecycle, security, workforce_v8, connectors

class FinalAssuranceTests(WebTests):
    # Reuse HTTP helpers; base WebTests are discovered separately.
    def test_audit_search_and_expanded_evidence(self):
        self.login()
        page=self.call('/audit?q=LOGIN_LOCAL_DEMO')['body']
        self.assertIn('Inspect evidence',page)
        self.assertNotIn('LOGIN_LOCAL_DEMO',self.call('/audit?q=NOT-A-REAL-ACTION')['body'].split('<tbody>')[1])
    def test_v9_pages_and_api(self):
        self.login()
        for path in ['/qualifications','/coverage','/insights','/control-centre','/api/v1/docs','/api/v1/employees','/api/v1/risks','/api/v1/qualifications','/api/v1/scim/Users','/api/v1/health','/static/final.css']:
            with self.subTest(path=path):self.assertEqual(self.call(path)['status'],200)
        data=json.loads(self.call('/api/v1/employees?page_size=2&page=2')['body'])
        self.assertEqual(len(data['data']),2);self.assertEqual(data['total'],42)
        self.assertEqual(self.call('/api/v1/employees?page_size=1000')['status'],400)
        self.assertEqual(self.call('/api/v1/unknown')['status'],404)
    def test_api_requires_login_and_role(self):
        self.assertEqual(self.call('/api/v1/employees')['status'],401)
        self.login('SC1003');self.assertEqual(self.call('/api/v1/employees')['status'],403)
    def test_hashed_session_storage_and_revocation(self):
        self.login('SC1001');token=self.cookies[auth.COOKIE_NAME]
        with database.connect() as c:
            stored=c.execute('SELECT token FROM sessions').fetchone()[0]
        self.assertNotEqual(stored,token);self.assertEqual(stored,hashlib.sha256(token.encode()).hexdigest())
        self.call('/logout','POST');self.assertEqual(self.call('/')['status'],303)
    def test_missing_agency_date_and_future_start_denied(self):
        with database.connect() as c:
            c.execute("UPDATE employees SET end_date=NULL WHERE employee_id='SC1006'")
            c.execute("UPDATE employees SET start_date=? WHERE employee_id='SC1001'",(str(utc_today()+timedelta(days=1)),))
        self.call('/login')
        for eid in ['SC1001','SC1006']:
            self.assertEqual(self.call('/login','POST',{'employee_id':eid})['status'],403)
            with database.connect() as c:
                with self.assertRaises(PermissionError):enterprise.active(c,eid)
    def test_qualification_expiry_is_enforced(self):
        self.login('SC1001');self.assertEqual(self.call('/protected/clinical')['status'],200)
        with database.connect() as c:c.execute("UPDATE qualifications SET expires_on=? WHERE employee_id='SC1001'",(str(utc_today()-timedelta(days=1)),))
        self.assertEqual(self.call('/protected/clinical')['status'],403)
        self.assertNotIn('Resident Alpha',self.call('/residents')['body'])
        with self.assertRaises(PermissionError):a.emergency('SC1001',{'resident_id':'R003','reason':'Urgent fictional resident care','incident_ref':'INC-DEMO-1'})
    def test_qualification_renewal_and_self_verification(self):
        d={'employee_id':'SC1001','kind':'Professional registration','expires_on':str(utc_today()+timedelta(days=200)),'evidence_ref':'Checked synthetic credential reference 123'}
        a.verify_qualification('SC1002',d)
        d['employee_id']='SC1002';d['kind']='Safeguarding'
        with self.assertRaises(PermissionError):a.verify_qualification('SC1002',d)
    def test_two_stage_cover_and_dynamic_expiry(self):
        rid=a.request_cover('SC1001',{'facility':'North Wing','minutes':'60','reason':'Cover the North Wing clinical shift'})
        with self.assertRaises(PermissionError):a.decide_cover('SC1005',{'id':rid,'decision':'Approve','reason':'Operator cannot act before manager'})
        self.assertEqual(a.decide_cover('SC1002',{'id':rid,'decision':'Approve','reason':'Manager confirms cover is required'}),'Pending operator')
        self.assertEqual(a.decide_cover('SC1005',{'id':rid,'decision':'Approve','reason':'Operator verifies least privilege'}),'Active')
        self.login('SC1001');self.assertIn('Resident Charlie',self.call('/residents')['body'])
        with database.connect() as c:c.execute("UPDATE cover_requests SET expires_at='2000-01-01T00:00:00' WHERE id=?",(rid,))
        self.assertNotIn('Resident Charlie',self.call('/residents')['body'])
    def test_cover_stale_approval_rejection_and_sod(self):
        rid=a.request_cover('SC1001',{'facility':'North Wing','minutes':30,'reason':'Temporary site coverage required'})
        a.decide_cover('SC1002',{'id':rid,'decision':'Approve','reason':'Manager confirms workforce need'})
        with database.connect() as c:c.execute("UPDATE employees SET facility='South Wing' WHERE employee_id='SC1001'")
        with self.assertRaises(ValueError):a.decide_cover('SC1005',{'id':rid,'decision':'Approve','reason':'Must reject changed workforce state'})
        self.assertEqual(a.decide_cover('SC1005',{'id':rid,'decision':'Reject','reason':'Reject changed workforce state'}),'Rejected')
    def test_emergency_named_resident_and_review(self):
        gid=a.emergency('SC1001',{'resident_id':'R003','reason':'Emergency fictional resident support','incident_ref':'INC-DEMO-100'})
        self.login('SC1001');page=self.call('/residents')['body']
        self.assertIn('Resident Charlie',page);self.assertNotIn('Resident Delta',page)
        a.review_emergency('SC1002',{'id':gid,'reason':'Incident investigated; care handover complete'})
        self.assertNotIn('Resident Charlie',self.call('/residents')['body'])
        self.login('SC1002');self.assertIn('Emergency access activated',self.call('/notifications')['body'])
    def test_emergency_rejects_worker_and_duplicate(self):
        d={'resident_id':'R003','reason':'Emergency fictional resident support','incident_ref':'INC-DEMO-100'}
        with self.assertRaises(PermissionError):a.emergency('SC1003',d)
        a.emergency('SC1001',d)
        with self.assertRaises(ValueError):a.emergency('SC1001',d)
    def test_policy_validation_optimistic_lock(self):
        with database.connect() as c:d=a.policy(c)
        d['reason']='Documented policy adjustment';a.save_policy('SC1005',d)
        with self.assertRaises(ValueError):a.save_policy('SC1005',d)
        d['version']=2;d['emergency_minutes']=31
        with self.assertRaises(ValueError):a.save_policy('SC1005',d)
    def test_daily_job_idempotent_and_deprovisioning(self):
        first=a.run_jobs('SC1005');second=a.run_jobs('SC1005')
        self.assertIn('SC1006',first['disabled']);self.assertTrue(second['replayed'])
        s=lifecycle.get_employee_state('SC1006');self.assertFalse(s['cloud_enabled']);self.assertFalse(s['actual_roles']);self.assertTrue(s['blocked'])
        with database.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM operational_jobs').fetchone()[0],1)
    def test_self_termination_and_unauthorised_lifecycle(self):
        with self.assertRaises(PermissionError):lifecycle.leaver('SC1005','SC1005')
        with self.assertRaises(PermissionError):lifecycle.leaver('SC1001','SC1003')
        self.assertEqual(lifecycle.get_employee_state('SC1001')['status'],'Active')
    def test_last_operator_guard(self):
        with database.connect() as c:
            with self.assertRaises(PermissionError):a.protect_operator(c,'SC1002','SC1005')
    def test_roster_rejects_blank_agency_expiry(self):
        with database.connect() as c:e=dict(c.execute("SELECT * FROM employees WHERE employee_id='SC1006'").fetchone())
        raw='employee_id,email,role,facility,status,end_date\n'+','.join([e['employee_id'],e['email'],e['approved_role'],e['facility'],'Active',''])
        with self.assertRaises(ValueError):workforce_v8.stage('SC1005',raw)
    def test_roster_approval_expires(self):
        raw='employee_id,email,role,facility,status,end_date\nSC1003,mia.patel@sunhaven.test,CareWorker,North Wing,Leaver,'
        rid=workforce_v8.stage('SC1005',raw);workforce_v8.decide('SC1002',rid,'Approved','Confirmed worker departure with HR')
        with database.connect() as c:c.execute("UPDATE roster_imports SET approved_at='2000-01-01T00:00:00' WHERE id=?",(rid,))
        with self.assertRaises(ValueError):workforce_v8.apply('SC1005',rid)
    def test_site_delegate_scope(self):
        with database.connect() as c:
            c.execute("UPDATE employees SET approved_role='SiteDelegate' WHERE employee_id='SC1003'")
            c.execute("UPDATE employee_roles SET role='SiteDelegate' WHERE employee_id='SC1003'")
        a.delegate('SC1005',{'employee_id':'SC1003','facility':'North Wing','expires_on':str(utc_today()+timedelta(days=7))})
        self.login('SC1003');self.assertEqual(self.call('/qualifications')['status'],200)
        self.assertNotIn('Sarah Khan',self.call('/qualifications')['body']);self.assertEqual(self.call('/employees')['status'],403)
        with self.assertRaises(PermissionError):a.verify_qualification('SC1003',{'employee_id':'SC1001','kind':'Safeguarding','expires_on':str(utc_today()+timedelta(days=7)),'evidence_ref':'Outside the delegated facility'})
    def test_rate_limits_and_security_headers(self):
        for i in range(30):self.assertTrue(security.rate_allowed('test-address','login'))
        self.assertFalse(security.rate_allowed('test-address','login'))
        r=self.call('/login');h=dict(r['headers']);self.assertIn('X-Request-ID',h)
        self.assertIn("script-src 'self';",h['Content-Security-Policy'])
    def test_reporting_allowlist_and_connector_fail_closed(self):
        result=a.report_query('SC1002','show high risk workers');self.assertIn('rows',result)
        with self.assertRaises(ValueError):a.report_query('SC1002','drop table employees;')
        for provider in connectors.PROVIDERS:
            with self.assertRaises(connectors.IntegrationUnavailable):connectors.connector(provider).apply(connectors.ProvisioningChange('id1','SC1001','disable'))
    def test_migration_idempotent_foreign_keys(self):
        database.init_db();database.init_db()
        with database.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM schema_versions WHERE version=9').fetchone()[0],1)
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(list(c.execute('PRAGMA foreign_key_check')),[])
    def test_independent_access_attestation(self):
        self.login('SC1002')
        self.assertEqual(self.call('/access-reviews','POST',{'employee_id':'SC1002','decision':'Retain','reason':'Self attestation should be rejected','remediation_status':'Closed'})['status'],403)

# Do not rerun inherited baseline test methods in this new suite.
for name in list(WebTests.__dict__):
    if name.startswith('test_'):setattr(FinalAssuranceTests,name,None)
# Avoid discovery of imported base class under a second module.
del WebTests
