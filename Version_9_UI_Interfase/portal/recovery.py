"""Atomic offline backup bundles. Stop every application writer before use.
Manifest hashes detect accidental damage; ledger verification checks signed evidence.
Bundles contain confidential data and may contain the ledger key: protect storage.
"""
from pathlib import Path
import hashlib,json,os,shutil,sqlite3,subprocess,sys,tempfile
import config,database
from security_workstream import ledger
NAMES={'sunhaven.db','sunhaven.db.ledger.key','sunhaven.db.ledger.head'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def _verify_database(path):
    env={**os.environ,'SUNHAVEN_DB_PATH':str(path),'SUNHAVEN_SEED_DEMO':'0'}
    code="""import json,sqlite3,config
from security_workstream import ledger
c=sqlite3.connect(config.DB_PATH)
if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Database integrity failed')
if c.execute('PRAGMA foreign_key_check').fetchall():raise RuntimeError('Foreign keys failed')
c.close()
r=ledger.verify()
if r['status']!='PASS' or r.get('pending'):raise RuntimeError('Ledger verification failed')
print(json.dumps(r))"""
    r=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).parent,env=env,capture_output=True,text=True,timeout=30)
    if r.returncode:raise ValueError('Database or signed ledger verification failed. Preserve the source and check the matching key/checkpoint.')
    return json.loads(r.stdout)

def _durable(path):
    with path.open('rb') as f:os.fsync(f.fileno())

def create_bundle(destination):
    destination=Path(destination).absolute()
    if destination.exists():raise ValueError('Backup destination already exists; choose a new directory.')
    if not config.DB_PATH.is_file():raise ValueError('Source database does not exist.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.sunhaven-backup-',dir=destination.parent));stage.chmod(0o700)
    try:
        ledger.sync()
        with database.connect() as guard:
            guard.execute('BEGIN IMMEDIATE')
            db=stage/'sunhaven.db'
            src=sqlite3.connect(config.DB_PATH);target=sqlite3.connect(db)
            try:src.backup(target)
            finally:src.close();target.close()
            for source,suffix in ((ledger.key_path(),'.ledger.key'),(ledger.head_path(),'.ledger.head')):
                if source.exists():shutil.copyfile(source,stage/('sunhaven.db'+suffix))
            for f in stage.iterdir():f.chmod(0o600)
        verified=_verify_database(db)
        files={f.name:{'sha256':digest(f),'bytes':f.stat().st_size} for f in stage.iterdir() if f.name in NAMES}
        manifest={'format':'sunhaven-backup-v1','release':config.RELEASE_VERSION,'external_key_required':bool(os.getenv('SUNHAVEN_LEDGER_KEY')),'files':files,'ledger_events':verified['count']}
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2));(stage/'manifest.json').chmod(0o600)
        for f in stage.iterdir():
            if f.is_file():_durable(f)
        if destination.exists():raise ValueError('Backup destination appeared during creation; nothing was overwritten.')
        os.rename(stage,destination)
        return {'status':'PASS','bundle':str(destination),'ledger_events':verified['count'],'external_key_required':manifest['external_key_required']}
    finally:
        if stage.exists():shutil.rmtree(stage)

def inspect_bundle(source):
    source=Path(source)
    if source.is_symlink() or not source.is_dir():raise ValueError('Choose a regular backup directory.')
    mf=source/'manifest.json'
    if mf.is_symlink() or not mf.is_file() or mf.stat().st_size>65536:raise ValueError('Backup manifest is missing or invalid.')
    try:
        manifest=json.loads(mf.read_text());files=manifest['files']
        if type(manifest.get('external_key_required')) is not bool:raise ValueError('Invalid external key flag.')
        if manifest['format']!='sunhaven-backup-v1' or not isinstance(files,dict) or not {'sunhaven.db','sunhaven.db.ledger.head'}<=set(files) or not set(files)<=NAMES:raise ValueError("Backup manifest format or file list is invalid.")
        if manifest['external_key_required'] and not os.getenv('SUNHAVEN_LEDGER_KEY'):raise ValueError('The original externally managed ledger key is required.')
        if not manifest['external_key_required'] and 'sunhaven.db.ledger.key' not in files:raise ValueError('Ledger key missing from backup.')
        for name,item in files.items():
            f=source/name
            if f.is_symlink() or not f.is_file() or f.stat().st_size!=item['bytes'] or digest(f)!=item['sha256']:raise ValueError('Backup file is missing or damaged: '+name)
        return manifest
    except (KeyError,TypeError,json.JSONDecodeError):raise ValueError('Backup manifest is malformed.')

def restore_bundle(source,destination):
    """Restore into a NEW directory and verify before publishing it. Never in-place."""
    source=Path(source).absolute();manifest=inspect_bundle(source);destination=Path(destination).absolute()
    if destination.exists():raise ValueError('Restore destination exists; choose a new directory.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.sunhaven-restore-',dir=destination.parent));stage.chmod(0o700)
    try:
        for name in manifest['files']:
            shutil.copyfile(source/name,stage/name);(stage/name).chmod(0o600)
            if digest(stage/name)!=manifest['files'][name]['sha256']:raise ValueError('Backup changed during restoration; nothing restored.')
        verified=_verify_database(stage/'sunhaven.db')
        for f in stage.iterdir():
            if f.is_file():_durable(f)
        if destination.exists():raise ValueError('Restore destination appeared; nothing overwritten.')
        os.rename(stage,destination)
        return {'status':'PASS','database':str(destination/'sunhaven.db'),'ledger_events':verified['count'],'restored_to_new_directory':True}
    finally:
        if stage.exists():shutil.rmtree(stage)
