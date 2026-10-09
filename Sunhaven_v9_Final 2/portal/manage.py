"""Offline administration. Access to this command must be restricted to operators."""
import argparse
from pathlib import Path
import sqlite3
import uuid
import shutil
import json
import config
import database
import audit

def main():
    parser=argparse.ArgumentParser(description='Sunhaven administration')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init',help='Create missing tables without removing existing records')
    expiry=sub.add_parser('expire-agency',help='Preview or enforce overdue agency expiry in mock directory')
    expiry.add_argument('--apply',action='store_true')
    expiry.add_argument('--actor-id',default='')
    expiry.add_argument('--reason',default='')
    backup=sub.add_parser('backup',help='Create a consistent SQLite backup, including WAL changes')
    backup.add_argument('destination',type=Path)
    bundle=sub.add_parser('backup-bundle',help='Offline verified backup into a new directory')
    bundle.add_argument('destination',type=Path)
    restore=sub.add_parser('restore-bundle',help='Verify and restore an offline bundle into a new directory')
    restore.add_argument('source',type=Path)
    restore.add_argument('destination',type=Path)
    bind=sub.add_parser('bootstrap',help='Provision the first Entra-linked IAM operator in an empty database')
    bind.add_argument('--employee-id',required=True)
    bind.add_argument('--name',required=True)
    bind.add_argument('--email',required=True)
    bind.add_argument('--object-id',required=True)
    args=parser.parse_args()
    if args.command in ('backup-bundle','restore-bundle'):
        import recovery,subprocess
        try:
            result=recovery.create_bundle(args.destination) if args.command=='backup-bundle' else recovery.restore_bundle(args.source,args.destination)
        except (ValueError,OSError,subprocess.SubprocessError) as exc:parser.error(str(exc))
        print(json.dumps(result,indent=2));return
    if args.command=='expire-agency':
        import automation
        database.init_db()
        plan=automation.preview()
        if not args.apply:
            print(json.dumps({'as_of':plan['as_of'],'expired':plan['expired'],'upcoming':plan['upcoming'],'fingerprint':plan['fingerprint']},indent=2));return
        if config.ENVIRONMENT!='development' or config.GRAPH_MODE!='mock':parser.error('Expiry apply is limited to the local mock-directory lab')
        if not args.actor_id or not args.reason:parser.error('--apply requires --actor-id and --reason')
        try:changed=automation.execute(args.actor_id,plan['fingerprint'],args.reason)
        except (ValueError,PermissionError,RuntimeError) as exc:parser.error(str(exc))
        print(json.dumps({'disabled_local_ids':changed,'count':len(changed)}));return
    if args.command=='init':
        database.init_db();print('Database initialised; existing records preserved.');return
    if args.command=='backup':
        if not config.DB_PATH.exists():parser.error('Database does not exist')
        if args.destination.exists():parser.error('Destination exists; choose a new backup path')
        from security_workstream import ledger
        for suffix in ('.ledger.key','.ledger.head'):
            target=Path(str(args.destination)+suffix)
            if target.exists():parser.error('Evidence backup target already exists: '+str(target))
        args.destination.parent.mkdir(parents=True,exist_ok=True)
        # Recover/verify first, then hold the SQLite writer lock across snapshot and checkpoint copies.
        # A separate read connection permits the backup API to read the committed WAL snapshot.
        ledger.sync()
        with database.connect() as guard:
            guard.execute('BEGIN IMMEDIATE')
            src=sqlite3.connect(config.DB_PATH); dst=sqlite3.connect(args.destination)
            try:src.backup(dst)
            finally:src.close();dst.close()
            args.destination.chmod(0o600)
            for original,suffix in [(ledger.key_path(),'.ledger.key'),(ledger.head_path(),'.ledger.head')]:
                if original.exists():
                    target=Path(str(args.destination)+suffix)
                    shutil.copy2(original,target);target.chmod(0o600)
        print('Verified backup created with ledger key/checkpoint when present. Restore to a separate path and verify before use.');return
    uuid.UUID(args.object_id)
    if config.SEED_DEMO:parser.error('Bootstrap requires SUNHAVEN_SEED_DEMO=0')
    database.init_db()
    with database.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute('SELECT COUNT(*) FROM employees').fetchone()[0]:
            parser.error('Bootstrap only accepts an empty workforce database')
        conn.execute('''INSERT INTO employees(employee_id,name,email,worker_type,approved_role,facility,status,manager_sponsor,start_date,entra_object_id,cloud_enabled,cloud_role,admin_privilege) VALUES (?,?,?,'Permanent','IAMOperator','Ashford Main','Active','SERVICE-OWNER',date('now'),?,1,'IAMOperator',1)''',(args.employee_id,args.name,args.email,args.object_id))
        conn.execute("INSERT INTO employee_roles VALUES (?,'IAMOperator')",(args.employee_id,))
        audit.record_on(conn,'OFFLINE_ADMIN',args.employee_id,'BOOTSTRAP','PASS',{})
    print('Initial operator provisioned. Sign in through the configured Entra tenant.')

if __name__=='__main__':main()
