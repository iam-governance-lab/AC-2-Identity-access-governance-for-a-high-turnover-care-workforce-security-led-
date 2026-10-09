"""Recovery release regression: actual authorization, AI bounds and workspace routes."""
import os,json
from unittest.mock import patch
from test_web import WebTests
import ai_insights,agent_assistant as agent,database,enterprise,recovery
class V14Tests(WebTests):
 def test_workspace_and_aggregate_export(self):
  self.login();r=self.call('/ai-workspace');self.assertEqual(r['status'],200);self.assertIn('Why your application access',r['body'])
  b=self.call('/ai-briefing.json');self.assertEqual(b['status'],200);self.assertIn('qualification_outlook',b['body']);self.assertNotIn('Sarah Khan',b['body']);self.assertNotIn('SC1001',b['body'])
 def test_worker_can_only_see_own_explanations(self):
  self.login('SC1001');self.assertEqual(self.call('/ai-workspace')['status'],200);self.assertEqual(self.call('/ai-briefing.json')['status'],403)
  result=ai_insights.access_explanations('SC1001');self.assertEqual(len(result['permissions']),4)
 def test_current_roles_override_client_hint(self):
  self.assertIn('error',agent.tool_result('governance_briefing',{},'SC1001',{'IAMOperator'}))
 def test_inactive_actor_blocked(self):
  with database.connect() as c:c.execute("UPDATE employees SET status='Inactive' WHERE employee_id='SC1001'")
  with self.assertRaises(PermissionError):agent.answer('Explain my access',{'Nurse'},'SC1001')
 def test_malformed_provider_output_falls_back(self):
  for bad in [None,[],{'status':'completed','output':[None]},{'status':'completed','output':[{'type':'message','content':[42]}]},{'status':'completed','output':[{'type':'function_call','name':None}]}]:
   with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test'}):
    result=agent.answer('How do I request access?',{'Nurse'},'SC1001',provider=lambda p,k:bad)
   self.assertIn('Local help',result['mode'])
 def test_slow_response_role_change_is_rechecked(self):
  def provider(p,k):
   with database.connect() as c:c.execute("DELETE FROM employee_roles WHERE employee_id='SC1005'");c.execute("INSERT INTO employee_roles(employee_id,role) VALUES ('SC1005','CareWorker')")
   return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'private stale governance answer'}]}]}
  with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test'}):r=agent.answer('How many workers?',{'IAMOperator'},'SC1005',provider=provider)
  self.assertNotIn('private stale',r['text'])
 def test_provider_concurrency_fallback(self):
  self.assertTrue(agent._MODEL_SLOTS.acquire(False));self.assertTrue(agent._MODEL_SLOTS.acquire(False))
  try:
   with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test'}):r=agent.answer('hello',{'Nurse'},'SC1001',provider=lambda p,k:self.fail('should not call'))
   self.assertIn('busy',r['mode'])
  finally:agent._MODEL_SLOTS.release();agent._MODEL_SLOTS.release()
 def test_offline_explain_and_brief(self):
  with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':''}):
   for actor,q in [('SC1001','Explain my access'),('SC1005','What qualifications expire soon?'),('SC1005','Give me review priorities')]:
    r=agent.answer(q,set(),actor);self.assertEqual(r['link'],'/ai-workspace');self.assertTrue(r['text'])
 def test_additive_migration_and_indexes(self):
  database.init_db()
  with database.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM employees').fetchone()[0],42)
   self.assertIsNotNone(c.execute("SELECT name FROM sqlite_master WHERE name='ix_v14_usage'").fetchone())
   self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_redirect_is_refused(self):
  self.assertIsNone(agent.NoRedirect().redirect_request(None,None,302,'m',{},'https://example.com'))
for name in dir(WebTests):
 if name.startswith('test_') and name not in V14Tests.__dict__:setattr(V14Tests,name,None)
del WebTests
