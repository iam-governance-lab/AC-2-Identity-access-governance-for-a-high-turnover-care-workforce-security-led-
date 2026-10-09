"""Run daily with cron/Task Scheduler. Creates a review campaign, previews expiry."""
import argparse,json
import config,database,enterprise,workforce_v8,automation

def preview():
    database.init_db()
    with database.connect() as c:
        period=workforce_v8.quarter()
        exists=c.execute('SELECT id FROM review_campaigns WHERE period=?',(period,)).fetchone()
        overdue=c.execute("SELECT count(*) FROM campaign_items i JOIN review_campaigns g ON g.id=i.campaign_id WHERE i.decision='Pending' AND g.due_at<?",(enterprise.now(),)).fetchone()[0]
    plan=automation.preview()
    return {'quarter':period,'campaign_due':exists is None,'overdue_reviews':overdue,'agency_expiry_count':len(plan['expired']),'agency_fingerprint':plan['fingerprint'],'mode':'preview; no cloud changes'}

def execute(actor):
    database.init_db()
    if config.ENVIRONMENT!='development' or config.GRAPH_MODE!='mock':raise RuntimeError('Automatic campaign creation is limited to the mock laboratory.')
    with database.connect() as c:enterprise.require(c,actor,{'IAMOperator'})
    import assurance
    jobs=assurance.run_jobs(actor)
    cid=workforce_v8.create_campaign(actor)
    return {'campaign_id':cid,'quarter':workforce_v8.quarter(),'daily_jobs':jobs}

def main():
    p=argparse.ArgumentParser(description='Daily local governance check')
    p.add_argument('--apply',action='store_true');p.add_argument('--actor',default='')
    a=p.parse_args()
    if a.apply and not a.actor:p.error('--apply requires --actor')
    try:print(json.dumps(execute(a.actor) if a.apply else preview(),indent=2))
    except (PermissionError,RuntimeError) as e:p.error(str(e))
if __name__=='__main__':main()
