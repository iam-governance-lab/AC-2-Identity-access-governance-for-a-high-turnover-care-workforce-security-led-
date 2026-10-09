"""Reproducible WSGI profile with isolated 180-worker data, no production claims."""
from pathlib import Path
import sys,tempfile,json,time,statistics
root=Path(__file__).resolve().parents[1]
portal=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'portal'
sys.path[:0]=[str(portal),str(portal/'tests')]
import config,database
config.DEMO_PROFILE='expanded'
from test_web import WebTests
case=WebTests('test_seed_counts');case.setUp()
try:
 case.login();connect=database.connect;sql=[]
 def traced(*a,**kw):
  c=connect(*a,**kw);c.set_trace_callback(sql.append);return c
 database.connect=traced;results=[]
 for path in ('/notifications','/qualifications','/workbench','/employees'):
  times=[];counts=[]
  for i in range(7):
   sql.clear();start=time.perf_counter();r=case.call(path);times.append((time.perf_counter()-start)*1000)
   assert r['status']==200,(path,r['status']);counts.append(sum(s.lstrip().upper().startswith('SELECT') for s in sql))
  results.append({'path':path,'selects':counts[0],'median_ms':round(statistics.median(times),3),'response_bytes':len(r['body'].encode()),'runs':7})
 print(json.dumps({'release':config.RELEASE_VERSION,'workers':180,'transport':'in-process WSGI; local sequential microbenchmark','pages':results},indent=2))
finally:case.tearDown()
