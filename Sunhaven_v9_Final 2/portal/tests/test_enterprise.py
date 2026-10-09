import unittest
import database,enterprise,integrations
from test_web import WebTests
from security_workstream import ledger

class EnterpriseTests(WebTests):
    def grant(self,pid='incident-response',actor='SC1005'):
        rid=enterprise.request_package(actor,pid,'Approved business need for the demonstration.')
        enterprise.decide_package('SC1002',rid,'Approved','Independent review completed for this access.')
        return rid
    def test_pages_role_csrf_and_direct_mutation(self):
        self.login()
        for p in ['/hub','/catalog','/services','/incidents','/policy-lab','/integrations']:
            with self.subTest(path=p):self.assertEqual(self.call(p)['status'],200)
        self.login('SC1003');self.assertEqual(self.call('/catalog')['status'],200)
        for p in ['/hub','/services','/incidents','/policy-lab','/integrations']:self.assertEqual(self.call(p)['status'],403)
        d={'name':'Demo agent','kind':'Agent','owner_id':'SC1002','scopes':'metrics.read','days':'7'}
        self.assertEqual(self.call('/console/service-add','POST',d,csrf=False)['status'],403)
        self.assertEqual(self.call('/console/service-add','POST',d)['status'],403)
    def test_self_approval_duplicate_and_replay(self):
        rid=enterprise.request_package('SC1005','incident-response','Meaningful business reason recorded.')
        with self.assertRaises(PermissionError):enterprise.decide_package('SC1005',rid,'Approved','Independent decision is required.')
        with self.assertRaises(ValueError):enterprise.request_package('SC1005','incident-response','Duplicate request should be blocked.')
        enterprise.decide_package('SC1002',rid,'Approved','Independent review completed successfully.')
        with self.assertRaises(ValueError):enterprise.decide_package('SC1002',rid,'Approved','Approval must not be replayed.')
        self.login();self.assertEqual(self.call('/catalog/resource/incident-response')['status'],200)
    def test_expiry_and_revocation_enforced(self):
        rid=self.grant();self.login()
        with database.connect() as c:c.execute("UPDATE package_requests SET expires_at='2000-01-01T00:00:00' WHERE id=?",(rid,))
        self.assertEqual(self.call('/catalog/resource/incident-response')['status'],403)
        rid=self.grant();enterprise.decide_package('SC1002',rid,'Revoked','Revoked after demonstration completed.')
        self.assertEqual(self.call('/catalog/resource/incident-response')['status'],403)
    def test_stale_worker_and_request(self):
        rid=enterprise.request_package('SC1001','quality-review','Business requirement for a quality review.')
        with database.connect() as c:c.execute("UPDATE employees SET facility='South Wing' WHERE employee_id='SC1001'")
        with self.assertRaises(ValueError):enterprise.decide_package('SC1002',rid,'Approved','Worker state changed since request.')
        rid=enterprise.request_package('SC1005','incident-response','Request for local incident response.')
        with database.connect() as c:c.execute("UPDATE package_requests SET created_at='2000-01-01T00:00:00' WHERE id=?",(rid,))
        with self.assertRaises(ValueError):enterprise.decide_package('SC1002',rid,'Approved','Old request cannot be approved now.')
    def test_sod_and_changed_grant_state(self):
        self.grant('quality-review')
        rid=enterprise.request_package('SC1005','incident-response','Emergency incident response access.')
        with self.assertRaises(ValueError):enterprise.decide_package('SC1002',rid,'Approved','Conflicting quality review grant remains.')
        self.login()
        with database.connect() as c:c.execute("UPDATE employees SET facility='North Wing' WHERE employee_id='SC1005'")
        self.assertEqual(self.call('/catalog/resource/quality-review')['status'],403)
    def test_ineligible_expired_and_blocked_workers(self):
        for actor,pid in [('SC1006','care-learning'),('SC1007','care-learning'),('SC1003','incident-response')]:
            with self.assertRaises(PermissionError):enterprise.request_package(actor,pid,'This worker must not receive this package.')
    def test_service_scope_owner_expiry_disable(self):
        sid=enterprise.add_service('SC1005',{'name':'Test assistant','kind':'Agent','owner_id':'SC1002','scopes':'metrics.read','days':'7'})
        evaluate=lambda scope:enterprise.service_action('SC1005',sid,'evaluate',scope)['decision']
        self.assertEqual(evaluate('metrics.read'),'ALLOW');self.assertEqual(evaluate('training.read'),'DENY')
        with database.connect() as c:c.execute("UPDATE employees SET status='Suspended' WHERE employee_id='SC1002'")
        self.assertEqual(evaluate('metrics.read'),'DENY')
        with database.connect() as c:
            c.execute("UPDATE employees SET status='Active' WHERE employee_id='SC1002'")
            c.execute("UPDATE service_identities SET expires_at='2000-01-01T00:00:00' WHERE id=?",(sid,))
        self.assertEqual(evaluate('metrics.read'),'DENY');enterprise.service_action('SC1005',sid,'disable')
        with database.connect() as c:c.execute("UPDATE service_identities SET expires_at='2099-01-01T00:00:00' WHERE id=?",(sid,))
        self.assertEqual(evaluate('metrics.read'),'DENY');self.assertEqual(ledger.verify()['status'],'PASS')
    def test_service_validation_no_write(self):
        with self.assertRaises(ValueError):enterprise.add_service('SC1005',{'name':'Bad agent','kind':'Agent','owner_id':'SC1002','scopes':'directory.write','days':'7'})
        with database.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM service_identities').fetchone()[0],0)
    def test_incident_transitions_require_active_grant(self):
        d={'action':'create','title':'Suspicious MFA sequence','severity':'High','owner_id':'SC1002','evidence':'Synthetic event IDs 1 to 6 investigated.'}
        with self.assertRaises(PermissionError):enterprise.incident('SC1005',d)
        rid=self.grant();iid=enterprise.incident('SC1005',d)
        with self.assertRaises(ValueError):enterprise.incident('SC1005',{'id':iid,'status':'Resolved','evidence':'Cannot skip investigation and containment.'})
        for status in ['Investigating','Contained','Resolved']:enterprise.incident('SC1005',{'id':iid,'status':status,'evidence':'Evidence recorded for '+status+' transition.'})
        with database.connect() as c:c.execute("UPDATE package_requests SET expires_at='2000-01-01T00:00:00' WHERE id=?",(rid,))
        with self.assertRaises(PermissionError):enterprise.incident('SC1005',d)
    def test_policy_explanation_and_validation(self):
        d={'risk':'Low','device':'Managed','auth':'Passkey','active':'Yes'}
        self.assertEqual(enterprise.evaluate_policy(d)['decision'],'ALLOW')
        for k,v in [('risk','High'),('device','Unmanaged'),('auth','Push MFA'),('active','No')]:self.assertEqual(enterprise.evaluate_policy({**d,k:v})['decision'],'BLOCK')
        with self.assertRaises(ValueError):enterprise.evaluate_policy({**d,'risk':'unknown'})
    def test_original_sitas_current_portal_integration(self):
        result=integrations.run('SC1005','sitas');self.assertEqual(len(result['scenarios']),6)
        self.assertEqual(result['portal_leaver_comparison']['integration']['employeeId'],'SC1007')
        self.assertTrue(any('IAMOperator' in x.get('values',[]) for x in result['mapping_findings']))
        self.login();self.assertEqual(self.call('/integrations')['status'],200)
    def test_original_saif_validation_no_invitation(self):
        d={'workerId':'EXT001','displayName':'Demo Worker','email':'worker@sydneycare.example','agencyId':'AG001'}
        result=integrations.run('SC1005','saif',d);self.assertEqual(result['result'],'APPROVED');self.assertIn('nothing sent',result['mode'])
        d['agencyId']='AG003';self.assertTrue(integrations.run('SC1005','saif',d)['result'].startswith('REJECTED'))
        with self.assertRaises(PermissionError):integrations.run('SC1004','sitas')
    def test_browser_request_flow_and_escaping(self):
        self.login('SC1001')
        self.assertEqual(self.call('/console/catalog-request','POST',{'package_id':'quality-review','reason':'<script>test</script> synthetic reason.'})['status'],303)
        self.assertNotIn('<script>test</script>',self.call('/catalog')['body'])
        with database.connect() as c:rid=c.execute('SELECT max(id) FROM package_requests').fetchone()[0]
        self.login('SC1002');self.assertEqual(self.call('/console/catalog-decision','POST',{'id':rid,'decision':'Approved','reason':'Approved following independent review.'})['status'],303)
        self.login('SC1001');self.assertEqual(self.call('/catalog/resource/quality-review')['status'],200)

for name in dir(WebTests):
    if name.startswith('test_') and name not in EnterpriseTests.__dict__:setattr(EnterpriseTests,name,None)
del WebTests
