"""Verification of the integrated lab security modules."""
from pathlib import Path
import tempfile,unittest,os
from datetime import datetime,timezone,timedelta
import config,database,audit
from security_workstream import ledger,mfa,threats
from test_web import WebTests

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=config.DB_PATH
        config.DB_PATH=Path(self.tmp.name)/'sunhaven.db';database.init_db()
    def tearDown(self):config.DB_PATH=self.old;self.tmp.cleanup()
    def test_mirrors_real_audit_and_detects_event_tampering(self):
        correlation=audit.record('SC1005','SC1001','TEST_EVENT','PASS',{'action':'test'})
        self.assertEqual(ledger.verify()['status'],'PASS')
        with database.connect() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM security_ledger WHERE canonical LIKE ?",('%'+correlation+'%',)).fetchone()[0],1)
            c.execute("UPDATE audit_events SET action='FORGED' WHERE correlation_id=?",(correlation,))
        with self.assertRaisesRegex(ledger.IntegrityError,'changed'):ledger.verify()
    def test_detects_middle_change_missing_tail_and_key_loss(self):
        audit.record('SC1005',None,'ONE','PASS');audit.record('SC1005',None,'TWO','PASS')
        with database.connect() as c:c.execute('UPDATE security_ledger SET canonical=? WHERE sequence=1',('tampered',))
        with self.assertRaisesRegex(ledger.IntegrityError,'Event or HMAC'):ledger.verify()
        # Recreate the ledger to test an external checkpoint against a removed tail.
        config.DB_PATH=Path(self.tmp.name)/'other.db';database.init_db()
        audit.record('SC1005',None,'ONE','PASS');audit.record('SC1005',None,'TWO','PASS')
        with database.connect() as c:c.execute('DELETE FROM security_ledger WHERE sequence=(SELECT MAX(sequence) FROM security_ledger)')
        with self.assertRaisesRegex(ledger.IntegrityError,'tail'):ledger.verify()
        config.DB_PATH=Path(self.tmp.name)/'third.db';database.init_db();audit.record('SC1005',None,'ONE','PASS')
        ledger.key_path().unlink()
        with self.assertRaisesRegex(ledger.IntegrityError,'key missing'):ledger.verify()
    def test_finding_ingestion_and_duplicate_sync(self):
        audit.record('SC1005',None,'ONE','PASS');count=ledger.sync()['count']
        self.assertEqual(count,ledger.sync()['count'])
        f=dict(rule_id='MFA_PROMPT_BURST',severity='High',actor_id='SC1005',timestamp_utc='2026-09-24T00:00:00Z',event_ids=['e1'],explanation='Five prompts in five minutes')
        ledger.append_finding(f);self.assertEqual(ledger.verify()['count'],count+1)
        self.assertEqual(ledger.sync()['count'],count+1)

class MfaTests(unittest.TestCase):
    def test_correlated_patterns_and_outcome_distinction(self):
        start=datetime(2026,9,24,tzinfo=timezone.utc)
        def event(i,outcome,who='SC1005',delta=None):return {'event_id':str(i),'actor_id':who,'outcome':outcome,'timestamp_utc':(start+timedelta(seconds=delta if delta is not None else i*40)).isoformat()}
        sample=[event(i,'denied') for i in range(5)]+[event(5,'success')]
        rules={f['rule_id'] for f in mfa.analyze(list(reversed(sample))+[sample[0]])}
        self.assertEqual(rules,{'MFA_REPEATED_DENIAL','MFA_PROMPT_BURST','MFA_DENIAL_TO_SUCCESS'})
        self.assertEqual(mfa.analyze([event(1,'unknown_failure'),event(2,'timeout'),event(3,'success')]),[])
        self.assertEqual(mfa.analyze([event(1,'denied'),event(2,'denied',delta=1000),event(3,'denied',delta=2000)]),[])
        with self.assertRaises(ValueError):mfa.analyze([event(1,'denied')|{'timestamp_utc':'bad'}])
    def test_state_is_local_and_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            old=config.DB_PATH;config.DB_PATH=Path(d)/'demo.db'
            try:
                database.init_db();report=threats.compare()
                self.assertEqual(len(report['scenarios']),6)
                self.assertEqual(report['source'],'local synthetic workforce snapshot')
                self.assertIn('UNMANAGED_DEVICE',{s['id'] for s in report['scenarios'] if s['controlled']=='OPEN'})
            finally:config.DB_PATH=old

class AssuranceWebTests(WebTests):
    def test_page_scope_and_real_access_events(self):
        self.login();self.assertEqual(self.call('/security-assurance')['status'],200)
        self.assertIn('Audit',self.call('/audit')['body'])
        self.call('/protected/iam-admin')
        with database.connect() as c:
            self.assertTrue(c.execute("SELECT 1 FROM security_ledger WHERE canonical LIKE '%ACCESS_ALLOWED%'").fetchone())
        self.login('SC1003');self.assertEqual(self.call('/security-assurance')['status'],403)
        self.assertEqual(self.call('/protected/iam-admin')['status'],403)
        with database.connect() as c:self.assertTrue(c.execute("SELECT 1 FROM security_ledger WHERE canonical LIKE '%ACCESS_DENIED%'").fetchone())
for name in dir(WebTests):
    if name.startswith('test_') and name not in AssuranceWebTests.__dict__:setattr(AssuranceWebTests,name,None)
del WebTests
