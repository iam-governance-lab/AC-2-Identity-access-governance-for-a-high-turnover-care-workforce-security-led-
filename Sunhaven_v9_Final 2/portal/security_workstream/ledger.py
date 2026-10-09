"""Tamper-evident lab ledger sourced from committed Sunhaven audit rows.

The signing key and head checkpoint are outside SQLite. Back up all three files.
This is a laboratory integrity aid, not immutable storage or a remote SIEM.
"""
import hashlib
import hmac
import json
import os
import secrets
import threading
from pathlib import Path
import config
import database

LOCK = threading.RLock()
ZERO = '0' * 64
SCHEMA = '''
CREATE TABLE IF NOT EXISTS security_ledger (
 sequence INTEGER PRIMARY KEY,
 source_id TEXT NOT NULL UNIQUE,
 canonical TEXT NOT NULL,
 previous_hash TEXT NOT NULL,
 event_hash TEXT NOT NULL,
 tag TEXT NOT NULL
);
'''
class IntegrityError(RuntimeError): pass

def key_path(): return Path(str(config.DB_PATH) + '.ledger.key')
def head_path(): return Path(str(config.DB_PATH) + '.ledger.head')

def _key(create=False):
    supplied = os.getenv('SUNHAVEN_LEDGER_KEY')
    if supplied:
        if len(supplied) < 32: raise IntegrityError('SUNHAVEN_LEDGER_KEY must contain at least 32 characters.')
        return supplied.encode()
    path = key_path()
    if not path.exists() and create:
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb') as f:f.write(secrets.token_bytes(32))
        except FileExistsError:pass
    if not path.exists():raise IntegrityError('Ledger signing key missing; restore the original key to verify evidence.')
    return path.read_bytes()

def _canonical(event):
    return json.dumps(event,sort_keys=True,separators=(',',':'),ensure_ascii=True)

def _head_message(seq,digest): return f'{seq}:{digest}'.encode()
def _save_head(seq,digest,key):
    tag=hmac.new(key,_head_message(seq,digest),hashlib.sha256).hexdigest()
    path=head_path();temp=path.with_name(path.name+'.'+secrets.token_hex(5)+'.tmp')
    try:
        with open(temp,'x') as f:
            os.chmod(temp,0o600)
            json.dump({'sequence':seq,'hash':digest,'tag':tag},f)
            f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)

def _verify(conn,key,checkpoint=None):
    expected=ZERO;count=0;last_source=0
    # One batched source read replaces one SELECT for every ledger event.
    sources={r['event_id']:r for r in conn.execute('SELECT * FROM audit_events')}
    for row in conn.execute('SELECT * FROM security_ledger ORDER BY sequence'):
        count+=1
        if row['sequence']!=count:raise IntegrityError(f'Sequence gap at {count}')
        if row['previous_hash']!=expected:raise IntegrityError(f'Previous hash mismatch at {count}')
        payload=(expected+'\n'+row['canonical']).encode()
        digest=hashlib.sha256(payload).hexdigest()
        tag=hmac.new(key,payload,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest,row['event_hash']) or not hmac.compare_digest(tag,row['tag']):
            raise IntegrityError(f'Event or HMAC mismatch at {count}')
        try:event=json.loads(row['canonical'])
        except (ValueError,TypeError):raise IntegrityError(f'Invalid event data at {count}')
        if event.get('source')=='PORTAL':
            try:
                source_id=int(row['source_id'].removeprefix('audit:'))
            except ValueError:raise IntegrityError(f'Invalid audit ID at {count}')
            if source_id<=last_source:raise IntegrityError(f'Audit event reordered at {count}')
            original=sources.get(source_id)
            if not original or _canonical(_from_audit(original, event.get('schema','security-event-v1')))!=row['canonical']:
                raise IntegrityError(f'Original audit event changed or missing at {count}')
            last_source=source_id
        expected=digest
    anchor=head_path()
    if checkpoint is not None or anchor.exists():
        try:data=checkpoint if checkpoint is not None else json.loads(anchor.read_text())
        except (OSError,ValueError):raise IntegrityError('Unreadable external ledger checkpoint')
        saved_seq=data.get('sequence');saved_hash=data.get('hash')
        signature=hmac.new(key,_head_message(saved_seq,saved_hash),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(str(data.get('tag','')),signature):raise IntegrityError('Checkpoint signature mismatch')
        if saved_seq!=count or saved_hash!=expected:raise IntegrityError('Ledger tail differs from external checkpoint')
    elif count:raise IntegrityError('External ledger checkpoint missing')
    return {'count':count,'head':expected,'last_audit_id':last_source,'status':'PASS'}

def _from_audit(r, schema='security-event-v2'):
    event={'schema':schema,'source':'PORTAL','source_id':f'audit:{r["event_id"]}',
        'timestamp_utc':r['event_time'],'actor_id':r['actor_id'],'target_id':r['target_id'],
        'action':r['action'],'result':r['result'],'correlation_id':r['correlation_id'],
        'metadata':json.loads(r['details'] or '{}')}
    if schema=='security-event-v2':
        event['final_state']=json.loads(r['final_state'] or '{}')
    return event

def _append(conn,event,key):
    seq,prev=conn.execute('SELECT sequence,event_hash FROM security_ledger ORDER BY sequence DESC LIMIT 1').fetchone() or (0,ZERO)
    serial=_canonical(event);payload=(prev+'\n'+serial).encode()
    digest=hashlib.sha256(payload).hexdigest()
    tag=hmac.new(key,payload,hashlib.sha256).hexdigest()
    conn.execute('INSERT INTO security_ledger VALUES (?,?,?,?,?,?)',(seq+1,event['source_id'],serial,prev,digest,tag))
    return seq+1,digest

def pending_path(): return Path(str(config.DB_PATH) + '.ledger.pending')

def _anchor(seq,digest,key):
    return {'sequence':seq,'hash':digest,'tag':hmac.new(key,_head_message(seq,digest),hashlib.sha256).hexdigest()}

def _recover(conn,key):
    path=pending_path()
    if not path.exists(): return
    try:
        saved=json.loads(path.read_text())
        payload=_canonical(saved['payload'])
        if not hmac.compare_digest(saved['tag'],hmac.new(key,payload.encode(),hashlib.sha256).hexdigest()):
            raise IntegrityError('Pending checkpoint signature mismatch')
        tip=conn.execute('SELECT sequence,event_hash FROM security_ledger ORDER BY sequence DESC LIMIT 1').fetchone() or (0,ZERO)
        target=saved['payload']['new'];old=saved['payload']['old']
        if tuple(tip)==(target['sequence'],target['hash']):
            _verify(conn,key,checkpoint=_anchor(*tip,key))
            _save_head(*tip,key)
        elif tuple(tip)==(old['sequence'],old['hash']):
            _verify(conn,key)
        else: raise IntegrityError('Pending checkpoint does not match committed ledger')
        path.unlink()
    except (KeyError,TypeError,ValueError,OSError) as exc:
        raise IntegrityError('Cannot recover audit checkpoint; preserve files for investigation.') from exc

def begin(conn):
    """Fail before a business mutation if existing evidence is damaged."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='security_ledger'").fetchone(): return None
    existing=conn.execute('SELECT COUNT(*) FROM security_ledger').fetchone()[0]
    key=_key(create=not existing and not head_path().exists() and not pending_path().exists())
    _recover(conn,key)
    state=_verify(conn,key)
    return state | {'key':key}

def prepare(conn,state):
    """Append audit rows in the same SQLite transaction as their business change."""
    if state is None:return None
    key=state['key']
    for r in conn.execute('SELECT * FROM audit_events WHERE event_id>? ORDER BY event_id',(state['last_audit_id'],)).fetchall():
        _append(conn,_from_audit(r),key)
    tip=conn.execute('SELECT sequence,event_hash FROM security_ledger ORDER BY sequence DESC LIMIT 1').fetchone() or (0,ZERO)
    if tuple(tip)==(state['count'],state['head']) and head_path().exists(): return None
    payload={'old':{'sequence':state['count'],'hash':state['head']},'new':{'sequence':tip[0],'hash':tip[1]}}
    serial=_canonical(payload); path=pending_path()
    temp=path.with_name(path.name+'.'+secrets.token_hex(5)+'.tmp')
    try:
        with open(temp,'x') as f:
            os.chmod(temp,0o600)
            json.dump({'payload':payload,'tag':hmac.new(key,serial.encode(),hashlib.sha256).hexdigest()},f)
            f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)
    return tip[0],tip[1],key

def finish(prepared):
    _save_head(*prepared)
    pending_path().unlink(missing_ok=True)

def sync():
    """Ingest pending history, verifying before commit; safe after a crash."""
    with database.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        before=conn.execute('SELECT COUNT(*) FROM security_ledger').fetchone()[0]
        conn.commit()
        tip=conn.execute('SELECT sequence,event_hash FROM security_ledger ORDER BY sequence DESC LIMIT 1').fetchone() or (0,ZERO)
        return {'status':'PASS','count':tip[0],'head':tip[1],'new':tip[0]-before}

def verify():
    with LOCK:
        with database.connect(integrity=False) as conn:
            count=conn.execute('SELECT COUNT(*) FROM security_ledger').fetchone()[0]
            if not count and not head_path().exists() and not pending_path().exists():return {'status':'EMPTY','count':0,'head':ZERO}
            key=_key()
            _recover(conn,key)
            state=_verify(conn,key)
            missing=conn.execute('SELECT COUNT(*) FROM audit_events WHERE event_id>?',(state['last_audit_id'],)).fetchone()[0]
            state['pending']=missing
            return state

def append_finding(finding):
    """Ingest a validated, sanitised MFA finding through the same chain."""
    safe={k:finding[k] for k in ('rule_id','severity','actor_id','timestamp_utc','event_ids','explanation')}
    with LOCK:
        sync()
        with database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE');key=_key()
            event={'schema':'security-event-v1','source':'SMFAA','source_id':'mfa:'+secrets.token_hex(12),
              'timestamp_utc':safe['timestamp_utc'],'actor_id':safe['actor_id'],'target_id':safe['actor_id'],
              'action':safe['rule_id'],'result':'FINDING','correlation_id':'MFA-'+secrets.token_hex(6),
              'metadata':{'severity':safe['severity'],'event_ids':safe['event_ids'],'explanation':safe['explanation']}}
            seq,head=_append(conn,event,key);conn.commit()
            return {'sequence':seq,'correlation_id':event['correlation_id']}


def verified_audit_snapshot(actor):
    """Hold the writer lock while checking and copying one consistent evidence snapshot."""
    import enterprise
    with LOCK:
        with database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            enterprise.require(conn,actor,{'Auditor','IAMOperator'})
            state=_verify(conn,_key())
            pending=conn.execute('SELECT COUNT(*) FROM audit_events WHERE event_id>?',(state['last_audit_id'],)).fetchone()[0]
            if pending:raise ValueError('Pending audit events need ledger ingestion before export.')
            return [dict(r) for r in conn.execute('SELECT * FROM audit_events ORDER BY event_id')],state
