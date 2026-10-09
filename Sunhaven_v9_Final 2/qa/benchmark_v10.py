"""Local ledger microbenchmark, not a load or production capacity test."""
from pathlib import Path
import sys,tempfile,time,json,statistics
ROOT=Path(__file__).resolve().parents[1]
portal=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'portal'
sys.path.insert(0,str(portal))
import database,config
from security_workstream import ledger
with tempfile.TemporaryDirectory() as td:
 config.DB_PATH=Path(td)/'bench.db';database.init_db()
 with database.connect() as c:
  c.executemany("INSERT INTO audit_events(actor_id,action,event_time,result,correlation_id,details) VALUES ('SC1005','BENCHMARK','2026-09-27T00:00:00Z','PASS',?,'{}')",[(f'BENCH-{i}',) for i in range(1000)])
 ledger.sync();durations=[];statements=[]
 for i in range(7):
  with database.connect() as c:
   if i==0:c.set_trace_callback(statements.append)
   t=time.perf_counter();state=ledger._verify(c,ledger._key());durations.append((time.perf_counter()-t)*1000)
 print(json.dumps({'version':getattr(config,'RELEASE_VERSION','9.0'),'events':state['count'],'select_statements':len([s for s in statements if s.startswith('SELECT')]),'median_ms':round(statistics.median(durations),3),'min_ms':round(min(durations),3),'max_ms':round(max(durations),3),'runs':7,'scope':'single-process local microbenchmark; not a load test'},indent=2))
