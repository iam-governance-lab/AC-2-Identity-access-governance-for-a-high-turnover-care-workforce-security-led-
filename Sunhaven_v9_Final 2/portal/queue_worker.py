"""Opt-in in-process local connector scheduling; no competing DB writer process."""
import logging,os,threading
from datetime import datetime,timezone
import release_v12
_lock=threading.Lock()
_state={"enabled":False,"running":False,"interval":0,"last_success":None,"last_error_type":None,"ticks":0}
def status():
    with _lock:return dict(_state)
def _update(**values):
    with _lock:_state.update(values)
log=logging.getLogger('sunhaven.queue')
def start():
    interval=int(os.getenv('SUNHAVEN_QUEUE_INTERVAL','0'))
    if interval==0:return None
    if not 15<=interval<=3600:raise ValueError('SUNHAVEN_QUEUE_INTERVAL must be 0 or 15..3600 seconds.')
    actor=os.getenv('SUNHAVEN_QUEUE_ACTOR','').strip()
    if not actor:raise ValueError('SUNHAVEN_QUEUE_ACTOR must identify an authorized IAM operator.')
    import database,enterprise
    with database.connect() as c:enterprise.require(c,actor,{'IAMOperator'})
    stop=threading.Event()
    _update(enabled=True,interval=interval)
    def loop():
        while not stop.wait(interval):
            try:
                _update(running=True)
                changes=release_v12.reconcile(actor);result=release_v12.process_jobs(actor)
                _update(last_success=datetime.now(timezone.utc).isoformat(),last_error_type=None,ticks=status()['ticks']+1)
                log.info('local_connector_tick differences=%s result=%s',changes,result)
            except Exception as exc:
                _update(last_error_type=type(exc).__name__)
                log.error('local_connector_tick_failed error_type=%s',type(exc).__name__)
            finally:_update(running=False)
        _update(enabled=False)
    threading.Thread(target=loop,name='sunhaven-local-connector',daemon=True).start()
    return stop
