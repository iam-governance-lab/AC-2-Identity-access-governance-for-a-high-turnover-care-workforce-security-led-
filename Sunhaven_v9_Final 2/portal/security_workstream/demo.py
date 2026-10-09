"""Repeatable controlled demonstration; writes evidence files, never secrets."""
import argparse,csv,json
from datetime import datetime,timezone,timedelta
from html import escape
from pathlib import Path
from security_workstream import threats,mfa,ledger
import database

def demo(output):
    database.init_db()
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    base=datetime.now(timezone.utc).replace(microsecond=0)
    events=[{'event_id':f'MFA-{i}','actor_id':'SC1005','timestamp_utc':(base+timedelta(seconds=i*30)).isoformat().replace('+00:00','Z'), 'outcome':'denied' if i<5 else 'success'} for i in range(6)]
    comparison=threats.compare();findings=mfa.analyze(events)
    before=ledger.sync();ingested=[ledger.append_finding(f) for f in findings]
    after=ledger.verify()
    for name,data in [('threat-comparison.json',comparison),('mfa-findings.json',findings),('ledger-verification.json',{'before':before,'ingested':ingested,'after':after})]:
        (output/name).write_text(json.dumps(data,indent=2)+'\n')
    with (output/'threat-summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['id','scenario','control','baseline','controlled','baseline_risk','controlled_risk','evidence']);writer.writeheader();writer.writerows(comparison['scenarios'])
    rows=''.join('<tr>' + ''.join('<td>'+escape(str(x[k]))+'</td>' for k in ('scenario','control','baseline','controlled','evidence'))+'</tr>' for x in comparison['scenarios'])
    (output/'threat-report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Sunhaven threat comparison</title><style>body{font:16px Arial;max-width:1000px;margin:40px auto;color:#183d31}td,th{padding:12px;border:1px solid #cedbd2;text-align:left}table{border-collapse:collapse}</style><h1>Sunhaven threat comparison</h1><p>Synthetic local snapshot; simulated outcomes require independent security validation.</p><table><tr><th>Scenario</th><th>Control</th><th>Baseline</th><th>Controlled</th><th>Basis</th></tr>'+rows+'</table></html>')
    return {'output':str(output),'findings':len(findings),'ledger':after['status'],'events':after['count']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='demo-evidence');args=parser.parse_args()
    print(json.dumps(demo(args.output),indent=2))
