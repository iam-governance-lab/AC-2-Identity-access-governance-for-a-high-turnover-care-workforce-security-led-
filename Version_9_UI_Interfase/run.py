"""One entry point for the preserved lab and expanded local portal."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys
if sys.version_info < (3,12):
    raise SystemExit('Sunhaven 9 Final requires Python 3.12 or later. Install Python 3.12+ and try again.')
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description='Sunhaven Version 9 Final — controlled demonstration release')
    parser.add_argument('command',nargs='?',default='portal',choices=['portal','sitas','verify-original','test','lab','review-worker','smfaa'])
    args=parser.parse_args()
    if args.command=='verify-original':
        items=json.loads((ROOT/'ORIGINAL_MANIFEST.json').read_text())['files'];bad=[]
        for x in items:
            f=ROOT/'original'/x['path']
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=x['sha256']:bad.append(x['path'])
        print(json.dumps({'files_checked':len(items),'status':'FAIL' if bad else 'PASS','mismatches':bad},indent=2));return bool(bad)
    if args.command=='sitas':return subprocess.call([sys.executable,'src/sitas.py','compare-all'],cwd=ROOT/'original/sunhaven-sitas-threat-simulator')
    if args.command=='lab':
        return subprocess.call([sys.executable,'-m','flask','--app','app','run','--host','127.0.0.1','--port','5000'],cwd=ROOT/'team_lab/app')
    if args.command=='review-worker':return subprocess.call([sys.executable,'access_review_worker.py'],cwd=ROOT/'team_lab/app')
    if args.command=='smfaa':return subprocess.call([sys.executable,'src/smfaa.py','--source','demo','--output-dir',str(ROOT/'runtime/smfaa')],cwd=ROOT/'team_lab/services/Sunhaven MFA Fatigue Attack Analyzer')
    if args.command=='test':
        commands=[([sys.executable,'-m','unittest','discover','-s','tests','-v'],ROOT/'portal'),([sys.executable,'-m','pytest','-q'],ROOT/'original/sunhaven-sitas-threat-simulator'),([sys.executable,'-m','pytest','-q'],ROOT/'original/sunhaven-saif-agency-identity-federation')]
        commands.extend([([sys.executable,'-m','pytest','-q'],ROOT/'team_lab/services/Sunhaven MFA Fatigue Attack Analyzer'),([sys.executable,'-m','pytest','-q','tests/test_access_review_db.py'],ROOT/'team_lab')])
        results=[subprocess.call(cmd,cwd=path,env={**os.environ,'SUNHAVEN_DEMO_PROFILE':'standard','SUNHAVEN_SEED_DEMO':'1','SUNHAVEN_ENV':'development','SUNHAVEN_AUTH_MODE':'local','SUNHAVEN_GRAPH_MODE':'mock','PYTHONPATH':str(ROOT/'team_lab/app')}) for cmd,path in commands]
        return int(any(results))
    os.environ.setdefault('SUNHAVEN_DEMO_PROFILE','expanded')
    return subprocess.call([sys.executable,'run.py'],cwd=ROOT/'portal')

if __name__=='__main__':raise SystemExit(main())
