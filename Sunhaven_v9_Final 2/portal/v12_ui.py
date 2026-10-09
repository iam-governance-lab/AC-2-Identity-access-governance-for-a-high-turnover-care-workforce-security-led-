"""V12 app governance, connector operations and contextual help."""
import json
from urllib.parse import urlencode
import auth,config,database,enterprise,help_assistant as helpbot,agent_assistant,release_v12 as v12,ui
from assurance_ui import field,panel,table
from v10_ui import pager

def action(name,body,label):
    return '<form class="form-grid" method="post" action="/v12-action/'+name+'">'+body+'<button class="btn btn-primary">'+ui.e(label)+'</button></form>'
def hidden(name,value):return '<input type="hidden" name="'+ui.e(name)+'" value="'+ui.e(value)+'">'
def role_set(eid):
    with database.connect() as c:return {r[0] for r in c.execute('SELECT role FROM employee_roles WHERE employee_id=?',(eid,))}
def page_no(query):
    page=int((query.get('page') or ['1'])[0])
    if not 1<=page<=1000000:raise ValueError('Invalid page number.')
    return page

class V12Pages:
    def help_page(self,query=None):
        user=self.require_login()
        if not user:return
        query=query or {};roles=role_set(user['employee_id']);q=(query.get('q') or [''])[0][:100];topic=(query.get('topic') or [''])[0]
        items=helpbot.topics_for(roles)
        if topic:items=[t for t in items if t['id']==topic]
        if q:items=[t for t in items if q.lower() in json.dumps(t).lower()]
        content=ui.page_header('HELP CENTRE','Find your next step','Search the workflow library or ask Sunhaven for guidance. Optional AI can explain role-filtered live summaries.')
        content+='<form class="panel form-grid" method="get" action="/help">'+field('Search help','q',value=q,required=False)+'<button class="btn btn-secondary">Search help</button><a class="btn btn-ghost" href="/help">All help topics</a></form>'
        content+='<div class="help-grid">'
        for t in items:
            content+='<article class="panel help-card"><h3>'+ui.e(t['title'])+'</h3><p>'+ui.e(t['summary'])+'</p><details><summary>Show instructions and requirements</summary><ol>'+''.join('<li>'+ui.e(x)+'</li>' for x in t['steps'])+'</ol><p class="muted">'+ui.e(t['prerequisites'])+'</p></details><a class="btn btn-secondary" href="'+ui.e(t['path'])+'">Open workspace</a></article>'
        content+='</div>'
        if not items:content+='<div class="empty-state">No matching help topics in your role. Try a shorter search or ask your manager.</div>'
        self.send_html(ui.layout('Help centre',content,user,active='help'))

    def assistant_ask(self,query=None):
        user=self.user()
        if not user:return self.send_json({'error':{'code':'session_expired','message':'Sign in again to continue using help.'},'request_id':self.request_id},401)
        data=self.form();result=agent_assistant.answer(data.get('question'),role_set(user['employee_id']),user['employee_id'],data.get('previous',''),data.get('context',''),history=data.get('history',''))
        self.send_json(result)

    def v12_page(self,page,query=None):
        user=self.require_login()
        if not user:return
        roles=role_set(user['employee_id']);gov=bool(roles&v12.GOV);operator='IAMOperator' in roles;editor=bool(roles&{'Manager','IAMOperator'})
        if page in ('connectors','sponsors') and not gov:return self.error_page('Access denied','A governance role is required.',403,user)
        query=query or {};number=page_no(query);offset=(number-1)*25;q=(query.get('q') or [''])[0][:100]
        eid=user['employee_id'];content=''
        with database.connect() as c:
            if page=='application-access':
                ents=[dict(r) for r in c.execute('SELECT * FROM app_entitlements ORDER BY application')]
                choices=[(r['key'],r['application']+' / '+r['name']) for r in ents if user['approved_role'] in json.loads(r['roles'])]
                content=ui.page_header('APPLICATION ACCESS','Approved, delivered and verified','Permission approvals are time-limited. Delivery uses the local demo connector; no external application is connected.')
                if choices:content+=panel('Request access for yourself',action('request',field('Application permission','entitlement',options=choices)+field('Minutes (privileged max 60; ordinary max 10080)','minutes','number',60)+field('Business reason','reason'),'Submit for independent approval'))
                filt=" WHERE (?=1 OR r.employee_id=?) AND (r.employee_id LIKE ? OR e.name LIKE ?)";args=(int(gov),eid,'%'+q+'%','%'+q+'%')
                total=c.execute('SELECT COUNT(*) FROM entitlement_requests r JOIN app_entitlements e ON e.key=r.entitlement'+filt,args).fetchone()[0]
                rows=c.execute('SELECT r.*,e.name,e.privileged FROM entitlement_requests r JOIN app_entitlements e ON e.key=r.entitlement'+filt+' ORDER BY r.id DESC LIMIT 25 OFFSET ?',(*args,offset)).fetchall()
                content+='<form class="panel form-grid" method="get">'+field('Search request history','q',value=q,required=False)+'<button class="btn btn-secondary">Search</button></form>'
                tr=[]
                for r in rows:
                    state='Expired' if r['status']=='Approved' and r['expires_at']<=enterprise.now() else r['status'];controls=''
                    if editor and r['employee_id']!=eid and (not r['privileged'] or operator) and r['status'] in ('Pending','Approved'):
                        options=[('Approved','Approve'),('Rejected','Reject')] if r['status']=='Pending' else [('Revoked','Revoke')]
                        controls='<details><summary>Review decision</summary>'+action('decision',hidden('id',r['id'])+field('Decision','decision',options=options)+field('Decision reason','reason'),'Record decision')+'</details>'
                    tr.append([str(r['id']),ui.e(r['employee_id']),ui.e(r['name']),ui.badge(state),ui.e(r['expires_at'] or 'After approval'),controls])
                content+=panel('Approval history',table(['ID','Worker','Permission','State','Expiry UTC','Decision'],tr))+pager('/application-access',{'q':q},number,total,25)
                scope='' if gov else ' WHERE o.employee_id=?';inventory=c.execute('SELECT o.*,e.application,e.name FROM observed_entitlements o JOIN app_entitlements e ON e.key=o.entitlement'+scope+' ORDER BY o.synced_at DESC LIMIT 25',() if gov else (eid,)).fetchall()
                content+=panel('Most recently delivered permissions (up to 25)',table(['Worker','Application / permission','Delivered state','Last used UTC'],[[ui.e(r['employee_id']),ui.e(r['application']+' / '+r['name']),ui.badge('Enabled' if r['enabled'] else 'Disabled'),ui.e(r['last_used_at'] or 'No local usage recorded')] for r in inventory]))
                content+=panel('Check your local application access',action('resource',field('Permission','entitlement',options=choices or [(r['key'],r['name']) for r in ents]),'Evaluate my current access')+'<p>This checks current employment, approval, expiry, delivered state and any shift/qualification conditions. It does not open real care records.</p>')
                if gov:
                    insights=c.execute("SELECT e.application,e.name,COUNT(*) total,SUM(o.last_used_at IS NULL) never_used FROM observed_entitlements o JOIN app_entitlements e ON e.key=o.entitlement WHERE o.enabled=1 GROUP BY e.key").fetchall()
                    content+=panel('Usage evidence for human review',table(['Application','Permission','Delivered grants','No local use recorded'],[[ui.e(r['application']),ui.e(r['name']),str(r['total']),str(r['never_used'])] for r in insights])+'<p>No use recorded is an investigation signal, not proof that access is unnecessary. No automatic removals are made from this report.</p>')
            elif page=='shifts':
                content=ui.page_header('SHIFT-AWARE ACCESS','Right site. Right time.','Schedule in UTC. A shift alone does not grant care access; current qualifications and an approved app permission are also required.')
                if editor:content+=panel('Schedule a shift',action('shift',field('Worker ID','employee_id')+field('Approved site','facility',options=[(x,x) for x in config.FACILITIES])+field('Start UTC','starts_at','datetime-local')+field('End UTC','ends_at','datetime-local')+field('Reason','reason'),'Schedule shift'))
                where='' if gov else ' WHERE employee_id=?';args=() if gov else (eid,)
                total=c.execute('SELECT COUNT(*) FROM shift_assignments'+where,args).fetchone()[0]
                rows=c.execute('SELECT * FROM shift_assignments'+where+' ORDER BY starts_at DESC LIMIT 25 OFFSET ?',(*args,offset)).fetchall()
                content+=panel('Shift register',table(['Worker / site','Start UTC','End UTC','State','Action'],[[ui.e(r['employee_id']+' / '+r['facility']),ui.e(r['starts_at']),ui.e(r['ends_at']),ui.badge('Ended' if r['status']=='Scheduled' and r['ends_at']<=enterprise.now() else r['status']),action('cancel-shift',hidden('id',r['id']),'Cancel shift') if editor and r['status']=='Scheduled' else ''] for r in rows]))+pager('/shifts',{},number,total,25)
            elif page=='sponsors':
                content=ui.page_header('SPONSORED WORKFORCE','Agency and contractor intake','A sponsor submits the details; an independent operator decides. Approved intake creates a local worker only. No invitation email is sent.')
                if editor:content+=panel('Submit an intake',action('intake',field('Worker name','name')+field('Email','email','email')+field('Type','worker_type',options=[('Agency','Agency'),('ThirdParty','Contractor')])+field('Site','facility',options=[(x,x) for x in config.FACILITIES])+field('Start date','starts_on','date')+field('End date (within 90 days)','ends_on','date')+field('Business reason','reason'),'Submit sponsored intake'))
                total=c.execute('SELECT COUNT(*) FROM sponsor_intakes').fetchone()[0];rows=c.execute('SELECT * FROM sponsor_intakes ORDER BY id DESC LIMIT 25 OFFSET ?',(offset,)).fetchall();tr=[]
                for r in rows:
                    controls=action('intake-decision',hidden('id',r['id'])+field('Decision','decision',options=[('Approved','Approve'),('Rejected','Reject')])+field('Reason','reason'),'Record intake decision') if operator and r['sponsor_id']!=eid and r['status']=='Pending' else ''
                    tr.append([ui.e(r['name']),ui.e(r['sponsor_id']),ui.e(r['facility']),ui.e(r['ends_on']),ui.badge(r['status']),ui.e(r['employee_id'] or ''),controls])
                content+=panel('Intake history',table(['Name','Sponsor','Site','Contract end','Status','Created ID','Decision'],tr))+pager('/sponsors',{},number,total,25)
            elif page=='connectors':
                content=ui.page_header('CONNECTOR OPERATIONS','Follow every access delivery','Durable local queue, reconciliation and attempt history. Entra, Okta, HRIS, payroll, email, care-record and SIEM transports remain unconfigured.')
                import queue_worker
                health=queue_worker.status()
                content+=panel('Background scheduler',table(['Mode','Interval seconds','Running','Last success UTC','Last error type','Completed ticks'],[[('Enabled' if health['enabled'] else 'Disabled; manual delivery available'),str(health['interval']),str(health['running']),ui.e(health['last_success'] or 'No successful tick this process'),ui.e(health['last_error_type'] or 'None'),str(health['ticks'])]]))
                counts={r[0]:r[1] for r in c.execute('SELECT status,COUNT(*) FROM provisioning_jobs GROUP BY status')}
                content+='<div class="stats-grid">'+''.join(ui.stat_card(k,counts.get(k,0),'Local connector jobs') for k in ('Queued','Retry','Dead','Succeeded'))+'</div>'
                if operator:
                    content+=panel('Run delivery',action('reconcile','','Reconcile desired and delivered access')+action('process','','Process up to 20 due jobs')+'<p>Your administrator can enable automatic background delivery; otherwise use the buttons above. Automatic retry delays are 30 and 60 seconds before the third attempt.</p>')
                    if config.ENVIRONMENT=='development':content+='<details class="panel"><summary>Demo failure and recovery exercise</summary>'+action('fault',field('Next delivery attempts to fail','count',options=[(str(n),str(n)) for n in range(4)]),'Configure local demo failure')+'</details>'
                total=c.execute('SELECT COUNT(*) FROM provisioning_jobs').fetchone()[0];rows=c.execute('SELECT * FROM provisioning_jobs ORDER BY id DESC LIMIT 25 OFFSET ?',(offset,)).fetchall()
                content+=panel('Delivery jobs',table(['ID / worker','Permission','State','Attempts','Next eligible UTC','Last error','Action'],[[str(r['id'])+' / '+ui.e(r['employee_id']),ui.e(r['entitlement']),ui.badge(r['status']),str(r['attempts']),ui.e(r['available_at']),ui.e(r['last_error'] or ''),action('retry',hidden('id',r['id']),'Retry failed job') if operator and r['status']=='Dead' else ''] for r in rows]))+pager('/connectors',{},number,total,25)
                history=c.execute('SELECT * FROM provisioning_attempts ORDER BY id DESC LIMIT 25').fetchall()
                content+=panel('Latest 25 attempt records',table(['Job','UTC','Outcome','Evidence'],[[str(r['job_id']),ui.e(r['attempted_at']),ui.e(r['outcome']),ui.e(r['detail'])] for r in history]))
                content+=panel('Portable audit events','<p>Export up to 500 events per request. Use after=&lt;event ID&gt; for the next batch. These are download adapters; no live SIEM or clinical integration is connected.</p><a class="btn btn-secondary" href="/integration-export/ndjson">Download NDJSON</a> <a class="btn btn-secondary" href="/integration-export/fhir">Download FHIR-shaped events</a>')
        self.send_html(ui.layout({'application-access':'Application access','shifts':'Shifts','sponsors':'Sponsor intake','connectors':'Connector operations'}[page],content,user,active=page))

    def v12_action(self,name,query=None):
        user=self.require_login()
        if not user:return
        actor=user['employee_id'];d=self.form();dest='/application-access'
        if name=='request':v12.request_access(actor,d.get('entitlement'),d.get('minutes'),d.get('reason'))
        elif name=='decision':v12.decide_access(actor,d.get('id'),d.get('decision'),d.get('reason'))
        elif name=='resource':
            result=v12.use_resource(actor,d.get('entitlement'))
            content=ui.page_header('LOCAL ACCESS EVALUATION','Access allowed' if result['allowed'] else 'Access denied',result['explanation'])+ui.alert(result['mode'])+'<a class="btn btn-secondary" href="/application-access">Back to application access</a>'
            return self.send_html(ui.layout('Application access check',content,user,active='application-access'),200 if result['allowed'] else 403)
        elif name=='shift':v12.add_shift(actor,d);dest='/shifts'
        elif name=='cancel-shift':v12.cancel_shift(actor,d.get('id'));dest='/shifts'
        elif name=='intake':v12.submit_intake(actor,d);dest='/sponsors'
        elif name=='intake-decision':v12.decide_intake(actor,d.get('id'),d.get('decision'),d.get('reason'));dest='/sponsors'
        elif name=='reconcile':v12.reconcile(actor);dest='/connectors'
        elif name=='process':v12.process_jobs(actor);dest='/connectors'
        elif name=='retry':v12.retry_job(actor,d.get('id'));dest='/connectors'
        elif name=='fault':v12.fail_demo(actor,d.get('count'));dest='/connectors'
        else:raise ValueError('Unknown operation.')
        self.redirect(dest+'?saved=1')

    def integration_export(self,kind,query=None):
        user=self.require_roles(list(v12.GOV),'/integration-export')
        if not user:return
        query=query or {};after=int((query.get('after') or ['0'])[0])
        if after<0 or after>2147483647:raise ValueError('Invalid event cursor.')
        with database.connect() as c:rows=[dict(r) for r in c.execute('SELECT event_id,event_time,actor_id,target_id,action,result,correlation_id FROM audit_events WHERE event_id>? ORDER BY event_id LIMIT 500',(after,))]
        if kind=='fhir':
            entries=[{'resource':{'resourceType':'AuditEvent','id':str(r['event_id']),'type':{'system':'urn:sunhaven:audit-type','code':r['action']},'recorded':r['event_time'].replace('+00:00','').rstrip('Z')+'Z','outcome':'0' if r['result']=='PASS' else '8','agent':[{'who':{'identifier':{'value':r['actor_id']}},'requestor':True}],'source':{'observer':{'display':'Sunhaven local demonstration'}},'entity':[{'what':{'identifier':{'value':r['correlation_id']}}}]}} for r in rows]
            payload={'resourceType':'Bundle','type':'collection','entry':entries};raw=json.dumps(payload,indent=2).encode();mime='application/json';ext='json'
        else:raw=('\n'.join(json.dumps(r) for r in rows)+ ('\n' if rows else '')).encode();mime='application/x-ndjson';ext='ndjson'
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('Content-Disposition','attachment; filename="sunhaven-events.'+ext+'"');self.send_header('X-Next-Cursor',str(rows[-1]['event_id'] if rows else after));self.end_headers();self.wfile.write(raw)
