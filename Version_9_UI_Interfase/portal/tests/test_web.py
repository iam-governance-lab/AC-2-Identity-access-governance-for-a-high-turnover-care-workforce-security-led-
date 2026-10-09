"""Integration tests through the production WSGI route adapter."""
import sys, tempfile, unittest
from io import BytesIO
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlencode
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import config, database, lifecycle
from wsgi import application

class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.old_db=config.DB_PATH
        config.DB_PATH=Path(self.tmp.name)/'test.db'; self.cookies={};database.init_db()
    def tearDown(self):
        config.DB_PATH=self.old_db; self.tmp.cleanup()
    def call(self,path,method='GET',data=None,csrf=True):
        data=dict(data or {})
        if method=='POST' and csrf:data['_csrf']=self.cookies.get('sunhaven_csrf','')
        body=urlencode(data).encode();parts=path.split('?',1)
        env={'REQUEST_METHOD':method,'PATH_INFO':parts[0],'QUERY_STRING':parts[1] if len(parts)>1 else '', 'wsgi.input':BytesIO(body),'CONTENT_LENGTH':str(len(body)), 'CONTENT_TYPE':'application/x-www-form-urlencoded','HTTP_COOKIE':'; '.join(k+'='+v for k,v in self.cookies.items()),'REMOTE_ADDR':'127.0.0.1'}
        result={}
        def start(status,headers):result.update(status=int(status[:3]),headers=headers)
        result['body']=b''.join(application(env,start)).decode('utf-8-sig')
        for k,v in result['headers']:
            if k.lower()=='set-cookie':
                c=SimpleCookie();c.load(v);self.cookies.update({k:v.value for k,v in c.items()})
        return result
    def login(self,eid='SC1005'):
        self.call('/login');self.assertEqual(self.call('/login','POST',{'employee_id':eid})['status'],303)
    def latest_request(self):
        with database.connect() as c:return c.execute('SELECT MAX(request_id) FROM access_requests').fetchone()[0]
    def request(self,role='Manager'):
        return self.call('/requests','POST',{'requested_role':role,'facility':'North Wing','reason':'Testing a planned workforce role change.'})
    def decide(self,rid):
        return self.call(f'/requests/{rid}/decision','POST',{'decision':'Approved','decision_note':'Business reason confirmed.'})
    def test_all_governance_pages_render(self):
        self.login()
        for path in ['/','/employees','/employees/SC1001','/employees/new','/employees/SC1001/move','/residents','/access-reviews','/audit','/compliance','/requirements','/notes','/requests','/guide']:
            with self.subTest(path=path):self.assertEqual(self.call(path)['status'],200)
    def test_seed_counts(self):
        with database.connect() as c:
            for table,count in [('employees',42),('residents',30),('work_notes',35)]:
                self.assertEqual(c.execute('SELECT count(*) FROM '+table).fetchone()[0],count)
    def test_csrf_missing_and_forged(self):
        self.call('/login');self.assertEqual(self.call('/login','POST',{'employee_id':'SC1005'},False)['status'],403)
        self.cookies['sunhaven_csrf']='forged.cookie'
        self.assertEqual(self.call('/login','POST',{'employee_id':'SC1005'})['status'],403)
    def test_entra_disables_demo_login(self):
        with patch.object(config,'AUTH_MODE','entra'):
            self.assertNotIn('action="/login"',self.call('/login')['body'])
            self.assertEqual(self.call('/login','POST',{'employee_id':'SC1005'})['status'],403)
    def test_expired_agency_denied(self):
        self.call('/login');self.assertEqual(self.call('/login','POST',{'employee_id':'SC1006'})['status'],403)
    def test_worker_permissions_and_assignment_scope(self):
        self.login('SC1003')
        for path in ['/employees','/notes','/audit','/compliance','/exports/employees']:
            self.assertEqual(self.call(path)['status'],403)
        self.assertNotIn('Recent audit evidence',self.call('/')['body'])
        self.assertIn('Resident Charlie',self.call('/residents')['body']);self.assertNotIn('Resident Alpha',self.call('/residents')['body'])
    def test_note_persistence_and_html_escape(self):
        self.login();note='<script>alert("test")</script> Handover complete.'
        self.assertEqual(self.call('/notes','POST',{'employee_id':'SC1001','category':'Handover','body':note})['status'],303)
        page=self.call('/notes')['body'];self.assertIn('&lt;script&gt;',page);self.assertNotIn(note,page)
        self.assertIn('Handover complete.',self.call('/employees/SC1001')['body'])
    def test_auditor_cannot_add_note(self):
        self.login('SC1004');self.assertEqual(self.call('/notes','POST',{'employee_id':'SC1001','category':'General','body':'Example note'})['status'],403)
    def test_approval_duplicate_and_final_decision(self):
        self.login('SC1001');self.assertEqual(self.request()['status'],303);self.assertEqual(self.request()['status'],409)
        rid=self.latest_request();self.login('SC1002');self.assertEqual(self.decide(rid)['status'],303)
        self.assertEqual(lifecycle.get_employee_state('SC1001')['approved_role'],'Nurse')
        self.assertEqual(self.decide(rid)['status'],409)
    def test_self_approval_denied(self):
        self.login();self.request();self.assertEqual(self.decide(self.latest_request())['status'],403)
    def test_manager_cannot_approve_privilege(self):
        self.login('SC1001');self.request('IAMOperator');rid=self.latest_request()
        self.login('SC1002');self.assertEqual(self.decide(rid)['status'],403)
    def test_review_validation(self):
        self.login('SC1002');d={'employee_id':'SC1001','decision':'Temporary Exception','reason':'Temporary role overlap required.','remediation_status':'Closed'}
        self.assertEqual(self.call('/access-reviews','POST',d)['status'],400)
        d['decision']='Remove';self.assertEqual(self.call('/access-reviews','POST',d)['status'],303)
        with database.connect() as c:self.assertEqual(c.execute('SELECT remediation_status FROM access_reviews ORDER BY review_id DESC').fetchone()[0],'Pending')
    def test_csv_formula_neutralisation(self):
        with database.connect() as c:c.execute("UPDATE employees SET name='=1+1' WHERE employee_id='SC1001'")
        self.login();r=self.call('/exports/employees');self.assertEqual(r['status'],200);self.assertIn("'=1+1",r['body'])
    def test_mover_revokes_session_and_cannot_reactivate(self):
        self.login('SC1001');lifecycle.mover('SC1001','Manager','North Wing','SC1005');self.assertEqual(self.call('/')['status'],303)
        with self.assertRaises(lifecycle.ValidationError):lifecycle.mover('SC1007','Nurse','North Wing','SC1005')
    def test_disabled_session_denied(self):
        self.login()
        with database.connect() as c:c.execute("UPDATE employees SET status='Suspended' WHERE employee_id='SC1005'")
        self.assertEqual(self.call('/employees')['status'],303)
    def test_production_config_and_cookies(self):
        with patch.object(config,'ENVIRONMENT','production'):
            with self.assertRaises(RuntimeError):config.validate_config()
        with patch.object(config,'SECURE_COOKIES',True):
            r=self.call('/login');self.assertTrue(any(k=='Set-Cookie' and '; Secure' in v and 'HttpOnly' in v for k,v in r['headers']))
            self.assertTrue(any(k=='Strict-Transport-Security' for k,v in r['headers']))
    def test_body_limit_method_and_health(self):
        self.assertEqual(self.call('/login','POST',{'x':'a'*70000})['status'],400)
        self.assertEqual(self.call('/health','DELETE')['status'],405)
        self.assertEqual(self.call('/health')['status'],200)

if __name__=='__main__':unittest.main()
