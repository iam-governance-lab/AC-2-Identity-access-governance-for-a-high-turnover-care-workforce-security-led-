"""Export a local audit handover with ledger validation and a content hash."""
import argparse,hashlib,json,os,tempfile
from pathlib import Path
import database,enterprise
from security_workstream import ledger

def export(actor,destination):
    target=Path(destination).resolve()
    if target.exists() or not target.parent.is_dir():raise ValueError('Choose a new filename in an existing directory.')
    rows,check=ledger.verified_audit_snapshot(actor)
    contents=''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows).encode('utf-8')
    fd,tmp=tempfile.mkstemp(dir=target.parent,prefix='.sunhaven-export-')
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'wb') as f:f.write(contents);f.flush();os.fsync(f.fileno())
        os.link(tmp,target)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return {'path':str(target),'events':len(rows),'sha256':hashlib.sha256(contents).hexdigest(),'ledger':check['status'],'mode':'local evidence export; no remote sink'}

def main():
    p=argparse.ArgumentParser(description='Export synthetic audit with SHA-256 checksum')
    p.add_argument('destination');p.add_argument('--actor',required=True);a=p.parse_args();database.init_db()
    try:print(json.dumps(export(a.actor,a.destination),indent=2))
    except (ValueError,PermissionError) as e:p.error(str(e))
if __name__=='__main__':main()
