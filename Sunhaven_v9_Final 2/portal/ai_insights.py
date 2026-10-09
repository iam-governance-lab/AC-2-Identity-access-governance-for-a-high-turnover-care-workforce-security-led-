"""Read-only, explainable intelligence. No model makes an access decision."""
from collections import Counter
from datetime import timedelta
import database,enterprise,assurance,release_v12
from clock import utc_today
GOV={'Manager','IAMOperator','Auditor'}

def migrate(c):
    c.execute("CREATE INDEX IF NOT EXISTS ix_v14_pending_apps ON entitlement_requests(status,employee_id,entitlement)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_v14_usage ON observed_entitlements(enabled,last_used_at,entitlement)")
    c.execute('INSERT OR IGNORE INTO schema_versions VALUES (14,?)',(enterprise.now(),))

def current_roles(actor):
    with database.connect() as c:
        enterprise.active(c,actor)
        return {r[0] for r in c.execute('SELECT role FROM employee_roles WHERE employee_id=?',(actor,))}

def access_explanations(actor):
    with database.connect() as c:
        enterprise.active(c,actor)
        out=[]
        for ent in c.execute('SELECT * FROM app_entitlements ORDER BY application,key').fetchall():
            desired,reason=release_v12.desired(c,actor,ent['key'])
            observed=c.execute('SELECT enabled FROM observed_entitlements WHERE employee_id=? AND entitlement=?',(actor,ent['key'])).fetchone()
            delivered=bool(observed and observed[0])
            out.append({'permission':ent['key'],'application':ent['application'],'name':ent['name'],'allowed':desired and delivered,'desired':desired,'delivered':delivered,'reason':reason if not desired or delivered else 'Approved context, but local delivery is pending.'})
        return {'scope':'signed-in worker only; local mock access','permissions':out}

def governance_briefing(actor):
    with database.connect() as c:
        enterprise.require(c,actor,GOV)
        today=utc_today();qual=Counter({'expired':0,'due_7_days':0,'due_8_30_days':0})
        for q in c.execute("SELECT q.expires_on FROM qualifications q JOIN employees e USING(employee_id) WHERE e.status='Active'"):
            from datetime import date
            days=(date.fromisoformat(q[0])-today).days
            if days<0:qual['expired']+=1
            elif days<=7:qual['due_7_days']+=1
            elif days<=30:qual['due_8_30_days']+=1
        risk=assurance.risk_inventory(c,actor)
        bands=Counter({'high':0,'medium':0,'low':0});reasons=Counter()
        for item in risk:
            bands['high' if item['score']>=60 else 'medium' if item['score']>=30 else 'low']+=1
            reasons.update(item['reasons'])
        pending=c.execute("SELECT COUNT(*) FROM entitlement_requests WHERE status='Pending'").fetchone()[0]
        dead=c.execute("SELECT COUNT(*) FROM provisioning_jobs WHERE status='Dead'").fetchone()[0]
        unused=c.execute('SELECT COUNT(*) FROM observed_entitlements WHERE enabled=1 AND last_used_at IS NULL').fetchone()[0]
        priorities=[]
        for count,signal,step,path in [(dead,'Exhausted delivery retries','Investigate failed attempts, then explicitly retry.','/connectors'),(qual['expired'],'Expired qualification records','Verify evidence and renew valid qualifications.','/qualifications'),(bands['high'],'High configured risk scores','Inspect evidence and confirm remediation with the owner.','/insights'),(unused,'Enabled grants without local use','Ask the manager to attest business need; missing use is not proof.','/access-reviews'),(pending,'Pending app requests','Review independently against current duties.','/application-access')]:
            if count:priorities.append({'count':count,'signal':signal,'next_step':step,'path':path})
        return {'generated_at':enterprise.now(),'scope':'aggregate local governance; no personal or clinical records','qualification_outlook':dict(qual),'risk_bands':dict(bands),'risk_reasons':dict(reasons),'pending_requests':pending,'dead_jobs':dead,'unused_grants':unused,'priorities':priorities,'decision_rule':'Human review required. No automatic approval or removal. Calendar outlook and configured rules are not machine-learning predictions.'}

def seed_examples(c):
    """Only fresh expanded synthetic data; never rewrite an upgraded database."""
    rows=c.execute("SELECT id FROM qualifications WHERE employee_id NOT IN ('SC1001','SC1002','SC1005') ORDER BY id DESC LIMIT 12").fetchall()
    for i,row in enumerate(rows):
        c.execute('UPDATE qualifications SET expires_on=? WHERE id=?',(str(utc_today()+timedelta(days=[-5,3,20][i%3])),row[0]))
