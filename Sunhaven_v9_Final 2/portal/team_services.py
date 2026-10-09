"""Bounded, audited bridge to the full team MFA detector."""
import csv,io,json,subprocess,sys
from pathlib import Path
import database,enterprise,governance
GOV={'IAMOperator','Manager','Auditor'}
def analyze(actor,mode='demo',csv_text=''):
    with database.connect() as c:enterprise.require(c,actor,GOV)
    if mode not in {'demo','csv'}:raise ValueError('Choose demo or normalized CSV.')
    if len(csv_text.encode('utf-8'))>60000:raise ValueError('CSV must be under 60 KB.')
    rows=[]
    if mode=='csv':
        reader=csv.DictReader(io.StringIO(csv_text))
        required={'event_id','employee_id','timestamp','event_type'}
        if not required.issubset(reader.fieldnames or []):raise ValueError('CSV requires event_id, employee_id, timestamp, event_type.')
        seen=set()
        for row in reader:
            if len(rows)>=2000:raise ValueError('Maximum 2,000 events per run.')
            clean={k:(row.get(k) or '').strip() for k in required}
            if any(not v or len(v)>120 for v in clean.values()):raise ValueError('Required values must contain 1–120 characters.')
            if clean['event_id'] in seen:raise ValueError('Duplicate event_id. Remove duplicates before analysis.')
            seen.add(clean['event_id']);rows.append(clean)
        if not rows:raise ValueError('CSV contains no events.')
    try:
        proc=subprocess.run([sys.executable,str(Path(__file__).with_name('integration_worker.py')),'smfaa'],input=json.dumps({'mode':mode,'rows':rows}),capture_output=True,text=True,timeout=20)
    except subprocess.TimeoutExpired as exc:raise ValueError('Analysis timed out. Reduce the CSV size and retry.') from exc
    if proc.returncode:raise ValueError('Analysis failed. Check timestamps and supported MFA event types.')
    result=json.loads(proc.stdout)
    with database.connect() as c:
        c.execute('BEGIN IMMEDIATE');enterprise.require(c,actor,GOV)
        c.execute('INSERT INTO integration_runs(kind,actor_id,created_at,result_json) VALUES (?,?,?,?)',('smfaa',actor,enterprise.now(),json.dumps(result)))
        governance.event(c,actor,None,'SMFAA_ANALYSIS',{'mode':mode,'events':result['events_analyzed'],'findings':len(result['findings'])})
    return result

def latest(actor):
    with database.connect() as c:
        enterprise.require(c,actor,GOV)
        row=c.execute("SELECT result_json FROM integration_runs WHERE kind='smfaa' ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(row['result_json']) if row else None
