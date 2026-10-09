import json
from unittest.mock import patch
from test_web import WebTests
import team_services,help_assistant,database,subprocess
class Final9Tests(WebTests):
 def test_demo_audit_export(self):
  self.login();page=self.call('/team-services');self.assertEqual(page['status'],200);self.assertIn('action="/team-services/analyze"',page['body']);self.assertNotIn('/assurance-action//',page['body'])
  self.assertEqual(self.call('/team-services/analyze','POST',{'mode':'demo'})['status'],303)
  out=self.call('/team-services/result.json');self.assertEqual(out['status'],200)
  result=json.loads(out['body']);self.assertGreater(result['events_analyzed'],0);self.assertGreater(len(result['findings']),0)
  with database.connect() as c:self.assertEqual(c.execute("SELECT count(*) FROM integration_runs WHERE kind='smfaa'").fetchone()[0],1)
 def test_worker_denied(self):
  self.login('SC1001')
  for path in ['/team-services','/team-services/result.json']:self.assertEqual(self.call(path)['status'],403)
  self.assertEqual(self.call('/team-services/analyze','POST',{'mode':'demo'})['status'],403)
 def test_csrf(self):
  self.login();self.assertEqual(self.call('/team-services/analyze','POST',{'mode':'demo'},False)['status'],403)
 def test_input_validation(self):
  header='event_id,employee_id,timestamp,event_type\n';row='e1,SC1001,2026-10-07T10:00:00Z,MFA_PROMPT\n'
  for text in ['',header,header+row+row,header+'e1,SC1001,broken,MFA_PROMPT',header+'e1,SC1001,2026-10-07T10:00:00Z,OTHER','x'*60001]:
   with self.subTest(text=text[:60]):
    with self.assertRaises(ValueError):team_services.analyze('SC1005','csv',text)
  result=team_services.analyze('SC1005','csv',header+row);self.assertEqual(result['events_analyzed'],1)
 def test_timeout(self):
  with patch('team_services.subprocess.run',side_effect=subprocess.TimeoutExpired('worker',20)):
   with self.assertRaisesRegex(ValueError,'timed out'):team_services.analyze('SC1005')
 def test_help_regressions(self):
  for question,topic in [('How do I check security risks?','insights'),('How do I manage roles?','roles'),('Where is MFA analysis?','team-services')]:
   with self.subTest(question=question):self.assertEqual(help_assistant.answer(question,{'IAMOperator'})['topic'],topic)
for name in dir(WebTests):
 if name.startswith('test_') and name not in Final9Tests.__dict__:setattr(Final9Tests,name,None)
del WebTests
