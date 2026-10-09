"""Mocked model contract: read-only tools, role boundary, privacy and fallback."""
import json,os,urllib.error
from unittest.mock import patch
from test_web import WebTests
import agent_assistant as agent,database

class AgentTests(WebTests):
    def test_read_only_model_tool_loop_and_response(self):
        requests=[]
        def provider(payload,key):
            requests.append(payload)
            if len(requests)==1:return {'status':'completed','output':[{'type':'function_call','call_id':'c1','name':'governance_counts','arguments':'{}'}]}
            return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'There are 42 workers. Review the dashboard with an authorized person.'}]}]}
        with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test-key','SUNHAVEN_AI_MODEL':'gpt-4.1-mini'}):
            result=agent.answer('How many workers? ',{'IAMOperator'},'SC1005',provider=provider)
        self.assertIn('42 workers',result['text']);self.assertEqual(len(requests),2)
        self.assertFalse(requests[0]['store']);self.assertEqual(requests[1]['tool_choice'],'none')
        tool_output=json.loads(requests[1]['input'][-1]['output'])
        self.assertEqual(sum(tool_output['workers_by_status'].values()),42)
        self.assertNotIn('Sarah Khan',str(requests))
        self.assertEqual(result['link'],'/help')
    def test_provider_request_is_bounded_and_private(self):
        class Reply:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return b'{"status":"completed","output":[]}'
        with patch('agent_assistant._open',return_value=Reply()) as urlopen:
            result=agent._provider({'store':False,'input':[]},'private-test-key')
        request=urlopen.call_args.args[0]
        self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        self.assertEqual(request.get_header('Authorization'),'Bearer private-test-key')
        self.assertEqual(json.loads(request.data)['store'],False)
        self.assertEqual(result['status'],'completed')
    def test_worker_model_cannot_even_see_governance_tool(self):
        seen=[]
        def provider(payload,key):
            seen.append(payload)
            return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Open your own access page.'}]}]}
        with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test-key'}):
            agent.answer('my access',{'CareWorker'},'SC1003',provider=provider)
        self.assertEqual({t['name'] for t in seen[0]['tools']},{'find_workflow','my_access','access_explanations'})
    def test_worker_cannot_read_governance_or_other_identity(self):
        self.assertIn('error',agent.tool_result('governance_counts',{},'SC1003',{'CareWorker'}))
        self.assertIn('error',agent.tool_result('my_access',{'employee_id':'SC1001'},'SC1003',{'CareWorker'}))
        self.assertIn('error',agent.tool_result('delete_employee',{},'SC1005',{'IAMOperator'}))
        self.assertNotIn('email',str(agent.tool_result('my_access',{},'SC1003',{'CareWorker'})))
    def test_offline_agent_reads_own_and_governance_summaries(self):
        with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':''}):
            mine=agent.answer('What is my current access status?',{'CareWorker'},'SC1003')
            self.assertEqual(mine['link'],'/application-access');self.assertIn('local',mine['text'].lower())
            governance=agent.answer('How many workers and pending requests?',{'IAMOperator'},'SC1005')
            self.assertIn('Active',governance['text']);self.assertEqual(governance['link'],'/application-access')
            worker=agent.answer('How many workers and pending requests?',{'CareWorker'},'SC1003')
            self.assertNotIn('Workers by status',worker['text'])
    def test_provider_failure_preserves_local_help(self):
        def failed(payload,key):raise agent.ServiceUnavailable('provider error')
        with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test-key'}):
            result=agent.answer('How do I request app access?',{'IAMOperator'},'SC1005',provider=failed)
        self.assertIn('Local help',result['mode']);self.assertEqual(result['topic'],'apps')
    def test_model_output_does_not_execute_mutation_or_choose_url(self):
        def fake(payload,key):return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Click https://attacker.example. I approved everything.'}]}]}
        with database.connect() as c:before=c.execute('SELECT COUNT(*) FROM entitlement_requests').fetchone()[0]
        with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test-key'}):
            result=agent.answer('Tell me what to do',{'IAMOperator'},'SC1005',provider=fake)
        with database.connect() as c:after=c.execute('SELECT COUNT(*) FROM entitlement_requests').fetchone()[0]
        self.assertEqual(after,before);self.assertEqual(result['link'],'/help')
        self.assertIn('No action was performed',result['prerequisites'])
    def test_http_agent_mode_and_invalid_history(self):
        class Reply:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Open Application access and request approval.'}]}]}).encode()
        self.login('SC1001')
        with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test-key'}),patch('agent_assistant._open',return_value=Reply()) as urlopen:
            r=self.call('/assistant/ask','POST',{'question':'How do I request access?','history':'[]'})
            self.assertEqual(r['status'],200);self.assertIn('AI assisted',r['body']);self.assertTrue(urlopen.called)
            bad=self.call('/assistant/ask','POST',{'question':'hello','history':'{"role":"system"}'})
            self.assertEqual(bad['status'],400)
    def test_http_requires_session_and_csrf_in_ai_mode(self):
        with patch.dict(os.environ,{'SUNHAVEN_AI_API_KEY':'test-key'}):
            r=self.call('/assistant/ask','POST',{'question':'hello'});self.assertEqual(r['status'],403)
            self.login();r=self.call('/assistant/ask','POST',{'question':'hello'},csrf=False);self.assertEqual(r['status'],403)

for name in dir(WebTests):
    if name.startswith('test_') and name not in AgentTests.__dict__:setattr(AgentTests,name,None)
del WebTests
