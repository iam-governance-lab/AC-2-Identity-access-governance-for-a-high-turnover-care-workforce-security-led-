"""Local sequential profile for the expanded v12 fixture; not a load test."""
from pathlib import Path
import sys,time,json,statistics
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'portal'),str(ROOT/'portal/tests')]
import config,database
from test_web import WebTests
from assets import cached_asset
config.DEMO_PROFILE='expanded';case=WebTests('test_seed_counts');case.setUp();results=[]
try:
 case.login()
 for path in ('/notifications','/qualifications','/application-access','/connectors','/help'):
  times=[]
  for _ in range(7):
   begin=time.perf_counter();response=case.call(path);times.append((time.perf_counter()-begin)*1000);assert response['status']==200
  results.append({'path':path,'median_ms':round(statistics.median(times),3),'response_bytes':len(response['body'].encode()),'runs':7})
 f=ROOT/'portal/static/app.bundle.css';st=f.stat();plain=cached_asset(str(f),st.st_mtime_ns,st.st_size);compressed=cached_asset(str(f),st.st_mtime_ns,st.st_size,True)
 report={'workers':320,'method':'Local sequential in-process WSGI; seven requests/page; no network or concurrency claim','pages':results,'css_bytes':len(plain[0]),'gzip_css_bytes':len(compressed[0]),'css_transfer_reduction_percent':round(100*(1-len(compressed[0])/len(plain[0])),1)}
 (ROOT/'evidence/v12/performance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:case.tearDown()
