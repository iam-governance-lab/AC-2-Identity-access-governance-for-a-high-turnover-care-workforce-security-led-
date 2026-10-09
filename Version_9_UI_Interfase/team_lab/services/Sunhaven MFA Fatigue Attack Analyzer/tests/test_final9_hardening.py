import importlib,sys,json,types
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from detector import load_rules
@pytest.mark.parametrize('bad',[0,-1,True,'3',10001])
def test_invalid_detection_threshold(tmp_path,bad):
 rules=json.loads((Path(__file__).resolve().parents[1]/'config/detection-rules.json').read_text());rules['prompt_burst']['count']=bad
 f=tmp_path/'rules.json';f.write_text(json.dumps(rules))
 with pytest.raises(ValueError):load_rules(f)
@pytest.mark.parametrize('case',['pagination','foreign_host','redirect','malformed'])
def test_graph_response_boundaries(monkeypatch,case):
 class App:
  def __init__(self,*a,**k):pass
  def initiate_device_flow(self,**k):return {'user_code':'demo','message':'Synthetic test'}
  def acquire_token_by_device_flow(self,flow):return {'access_token':'synthetic-token'}
 calls=[]
 def get(url,**kwargs):
  calls.append(url);assert kwargs['allow_redirects'] is False;assert kwargs['timeout']==30
  body={'value':[]}
  if len(calls)==1 and case in ('pagination','foreign_host'):body['@odata.nextLink']=('https://graph.microsoft.com/v1.0/auditLogs/signIns?$skiptoken=next' if case=='pagination' else 'https://attacker.invalid/signins')
  if case=='malformed':body={'value':'bad'}
  return types.SimpleNamespace(status_code=302 if case=='redirect' else 200,raise_for_status=lambda:None,json=lambda:body)
 monkeypatch.setitem(sys.modules,'msal',types.SimpleNamespace(PublicClientApplication=App));monkeypatch.setitem(sys.modules,'requests',types.SimpleNamespace(get=get))
 monkeypatch.setenv('SMFAA_CLIENT_ID','test');monkeypatch.setenv('SMFAA_TENANT_ID','test')
 sys.modules.pop('entra_graph_adapter',None);adapter=importlib.import_module('entra_graph_adapter')
 if case=='pagination':
  events,stats=adapter.load_graph_signins({},[]);assert stats['pages']==2 and not stats['truncated']
 else:
  with pytest.raises(RuntimeError):adapter.load_graph_signins({},[])
  assert len(calls)==1
