"""One entry point for the preserved lab and expanded local portal."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys
if sys.version_info < (3,12):
    raise SystemExit('Sunhaven 9 requires Python 3.12 or later. Install Python 3.12+ and try again.')
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description='Sunhaven Final 9.0 — controlled demonstration release')
    parser.add_argument('command',nargs='?',default='portal',choices=['portal','sitas','verify-original','test'])
    args=parser.parse_args()
    if args.command=='verify-original':
        items=json.loads((ROOT/'ORIGINAL_MANIFEST.json').read_text())['files'];bad=[]
        for x in items:
            f=ROOT/'original'/x['path']
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=x['sha256']:bad.append(x['path'])
        print(json.dumps({'files_checked':len(items),'status':'FAIL' if bad else 'PASS','mismatches':bad},indent=2));return bool(bad)
    if args.command=='sitas':return subprocess.call([sys.executable,'src/sitas.py','compare-all'],cwd=ROOT/'original/sunhaven-sitas-threat-simulator')
    if args.command=='test':
        commands=[([sys.executable,'-m','unittest','discover','-s','tests','-v'],ROOT/'portal'),([sys.executable,'-m','pytest','-q'],ROOT/'original/sunhaven-sitas-threat-simulator'),([sys.executable,'-m','pytest','-q'],ROOT/'original/sunhaven-saif-agency-identity-federation')]
        results=[subprocess.call(cmd,cwd=path) for cmd,path in commands]
        return int(any(results))
    return subprocess.call([sys.executable,'run.py'],cwd=ROOT/'portal')

if __name__=='__main__':raise SystemExit(main())
