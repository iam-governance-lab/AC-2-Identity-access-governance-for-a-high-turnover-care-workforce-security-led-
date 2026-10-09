"""Analyse an already sanitised MFA event JSON array from a controlled lab export."""
import argparse,json
from pathlib import Path
from security_workstream import mfa,ledger

def main():
    parser=argparse.ArgumentParser(description='Analyse a sanitised MFA event array')
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--ingest-findings',action='store_true',help='Append findings to the local integrity ledger')
    args=parser.parse_args()
    if args.input.stat().st_size>2_000_000:parser.error('Event file exceeds 2 MB')
    events=json.loads(args.input.read_text())
    if not isinstance(events,list) or len(events)>10000:parser.error('Expected an array of up to 10,000 events')
    results=mfa.analyze(events)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,indent=2)+'\n')
    if args.ingest_findings:
        import database
        database.init_db()
        for f in results:ledger.append_finding(f)
    print(f'{len(results)} findings written to {args.output}')
if __name__=='__main__':main()
