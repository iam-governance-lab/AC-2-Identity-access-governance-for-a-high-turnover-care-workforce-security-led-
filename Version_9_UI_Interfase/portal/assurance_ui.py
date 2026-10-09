from clock import utc_today
"""Server rendered final-release assurance console and read-only JSON API."""
from datetime import date, timedelta
import json
from itertools import count
_FIELDS=count(1)
from urllib.parse import urlencode
import assurance as a
from security_workstream import ledger
import auth, config, database, enterprise, governance, ui

GOV={'Manager','IAMOperator','Auditor','SiteDelegate'}
def field(label,name,kind='text',value='',options=None,required=True):
    field_id=f'field-{next(_FIELDS)}'
    control=(f'<select id="{field_id}" name="{ui.e(name)}">'+''.join(f'<option value="{ui.e(v)}" {"selected" if str(v)==str(value) else ""}>{ui.e(t)}</option>' for v,t in options)+'</select>') if options is not None else f'<input id="{field_id}" name="{ui.e(name)}" type="{kind}" value="{ui.e(value)}" {"required" if required else ""} maxlength="2000">'
    return f'<div class="field"><label for="{field_id}">{ui.e(label)}</label>{control}</div>'
def form(action,contents,button):
    return f'<form method="post" action="/assurance-action/{ui.e(action)}" class="form-grid">{contents}<div class="form-actions full"><button class="btn btn-primary">{ui.e(button)}</button></div></form>'
def panel(title,body):return f'<section class="panel"><div class="panel-head"><h3>{ui.e(title)}</h3></div>{body}</section>'
def table(headers,rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th scope="col">'+ui.e(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+(''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows) or '<tr><td colspan="'+str(len(headers))+'">No records in your current scope.</td></tr>')+'</tbody></table></div>'

class AssurancePages:
    def assurance_page(self,page,query=None):
        user=self.require_login()
        if not user:return
        eid=user['employee_id'];query=query or {}
        if page!='coverage' and not auth.has_role(eid,GOV):return self.error_page('Access denied','A governance role is required.',403,user)
        with database.connect() as c:
            scope=a.scopes(c,eid);pol=a.policy(c)
            people=[dict(r) for r in c.execute('SELECT * FROM employees ORDER BY name') if r['facility'] in scope]
            opts=[(r['employee_id'],r['name']+' · '+r['employee_id']) for r in people]
            editable=auth.has_role(eid,{'Manager','IAMOperator','SiteDelegate'})
            operator=auth.has_role(eid,{'IAMOperator'})
            content=''
            if page=='qualifications':
                rows=[dict(r) for r in c.execute('SELECT q.*,e.name,e.facility FROM qualifications q JOIN employees e USING(employee_id) ORDER BY q.expires_on,q.id') if r['facility'] in scope]
                due=[r for r in rows if r['expires_on']<=str(utc_today()+timedelta(days=pol['renewal_days']))]
                current={}
                for r in rows:
                    if r['expires_on']>=str(utc_today()):current.setdefault(r['employee_id'],set()).add(r['kind'])
                missing=[r for r in people if auth.employment_valid(r) and r['approved_role'] in ('Nurse','Manager','CareWorker','AgencyWorker') and not ({'Safeguarding','Professional registration'} if r['approved_role']=='Nurse' else {'Safeguarding'}).issubset(current.get(r['employee_id'],set()))]
                content=ui.page_header('WORKFORCE ASSURANCE','Qualified people. Safer access.','Care access requires current verified qualifications. Evidence references contain no certificate images or sensitive identity documents.')
                content+='<div class="stats-grid">'+ui.stat_card('Verified records',len(rows),'Current and expired')+ui.stat_card('Renewal alerts',len(due),f'Within {pol["renewal_days"]} days','orange')+ui.stat_card('Qualification gaps',len(missing),'Care access is denied','red')+'</div>'
                if editable:content+=panel('Verify or renew qualification',form('qualification',field('Worker','employee_id',options=opts)+field('Qualification','kind',options=[(x,x) for x in a.KINDS])+field('Valid through','expires_on','date')+field('Evidence reference (10+ characters)','evidence_ref'),'Save verified record'))
                from v10_ui import pager
                q=(query.get('q') or [''])[0][:100];number=int((query.get('page') or ['1'])[0])
                if not 1<=number<=1000000:raise ValueError('Invalid qualification page.')
                register=[r for r in rows if q.lower() in (r['name']+' '+r['kind']+' '+r['employee_id']).lower()]
                register_rows=register[(number-1)*25:number*25]
                content+='<form class="panel form-grid" method="get" action="/qualifications">'+field('Search qualification register','q',value=q,required=False)+'<button class="btn btn-secondary">Search register</button></form>'
                content+=panel('Qualification register',table(['Worker','Qualification','Valid through','State','Verified by'],[[ui.e(r['name']),ui.e(r['kind']),ui.e(r['expires_on']),ui.badge('Expired' if r['expires_on']<str(utc_today()) else 'Current','red' if r['expires_on']<str(utc_today()) else 'green'),ui.e(r['verified_by'])] for r in register_rows]))
                content+=pager('/qualifications',{'q':q},number,len(register),25)
                content+=panel('Required action',table(['Worker','Role','Action'],[[ui.e(r['name']),ui.e(r['approved_role']),'Verify required safeguarding'+(' and professional registration' if r['approved_role']=='Nurse' else '')] for r in missing]))
            elif page=='coverage':
                governor=auth.has_role(eid,{'Manager','IAMOperator','Auditor'})
                rows=[dict(r) for r in c.execute('SELECT * FROM cover_requests'+('' if governor else ' WHERE employee_id=?')+' ORDER BY id DESC LIMIT 100',() if governor else (eid,))]
                emergency=[dict(r) for r in c.execute('SELECT * FROM emergency_grants'+('' if governor else ' WHERE employee_id=?')+' ORDER BY id DESC LIMIT 100',() if governor else (eid,))]
                content=ui.page_header('TIME-BOUND ACCESS','Site cover & emergency access','Temporary site cover requires a manager and a separate IAM operator. Emergency access is limited to one resident and triggers independent review.')
                content+='<div class="stats-grid">'+ui.stat_card('Site-cover limit',str(pol['cover_minutes'])+' min','Two approval stages')+ui.stat_card('Emergency limit',str(pol['emergency_minutes'])+' min','Qualified nurses only','orange')+ui.stat_card('Awaiting review',sum(not r['reviewed_at'] for r in emergency),'Emergency events','red')+'</div>'
                if auth.has_role(eid,{'Nurse'}):
                    content+='<div class="grid-2">'+panel('Request temporary site cover',form('cover',field('Site','facility',options=[(x,x) for x in config.FACILITIES])+field('Minutes','minutes','number',60)+field('Business reason (10+ characters)','reason'),'Request two-stage approval'))
                    content+=panel('Activate emergency access',ui.alert('Use only for an actual care emergency in the fictional demo. This never grants administrator rights.','warning')+form('emergency',field('Resident ID','resident_id',value='R003')+field('Incident reference (8+ characters)','incident_ref')+field('Emergency justification (10+ characters)','reason'),'Activate limited access'))+'</div>'
                content+=panel('Site-cover requests',table(['Request','Worker','Site / reason','Status','Approvers','Expires'],[[str(r['id']),ui.e(r['employee_id']),ui.e(r['facility'])+'<br>'+ui.e(r['reason']),ui.badge('Expired' if r['status']=='Active' and r['expires_at']<=enterprise.now() else r['status'],'blue'),ui.e((r['manager_id'] or '—')+' / '+(r['operator_id'] or '—')),ui.e(r['expires_at'] or 'After approval')] for r in rows]))
                if governor and auth.has_role(eid,{'Manager','IAMOperator'}):
                    openrows=[r for r in rows if r['status'] in ('Pending manager','Pending operator','Active')]
                    if openrows:content+=panel('Make a site-cover decision',form('cover-decision',field('Request','id',options=[(r['id'],f'#{r["id"]} · {r["employee_id"]} · {r["status"]}') for r in openrows])+field('Decision','decision',options=[(x,x) for x in ('Approve','Reject','Revoke')])+field('Decision evidence','reason'),'Record decision'))
                content+=panel('Emergency evidence',table(['Event','Worker','Resident / incident','Expires','Review'],[[str(r['id']),ui.e(r['employee_id']),ui.e(r['resident_id'])+'<br>'+ui.e(r['incident_ref'])+'<br>'+ui.e(r['reason']),ui.e(r['expires_at']),ui.e(r['reviewed_by'] or 'Independent review due within 24h')] for r in emergency]))
                pending=[r for r in emergency if not r['reviewed_at']]
                if pending and auth.has_role(eid,{'Manager','IAMOperator'}):content+=panel('Review and close emergency access',form('emergency-review',field('Event','id',options=[(r['id'],f'#{r["id"]} · {r["employee_id"]}') for r in pending])+field('Investigation evidence','reason'),'Close access and record review'))
            elif page=='insights':
                rows=a.risk_inventory(c,eid)
                question=(query.get('q') or [''])[0];result=None
                if question:
                    try:result=a.report_query(eid,question);rows=result['rows']
                    except ValueError as exc:content+=ui.alert(str(exc),'warning')
                content+=ui.page_header('EXPLAINABLE INSIGHTS','Understand access risk','Transparent rules explain each signal. Scores support human review and never grant or remove access automatically.')
                content+='<form method="get" action="/insights" class="panel form-grid">'+field('Ask: dormant accounts, expired qualifications, agency risks, show high risk workers','q',value=question)+'<button class="btn btn-primary">Run report</button></form>'
                content+=ui.alert(f'{len(rows)} matching workers. Rule-based reporting; no external AI service receives workforce data.')
                content+=panel('Risk findings',table(['Worker','Site','Risk / 100','Explanation','Last portal sign-in'],[[ui.e(r['name'])+'<br><span class="mono">'+ui.e(r['employee_id'])+'</span>',ui.e(r['facility']),ui.badge(r['score'],'red' if r['score']>=35 else 'orange' if r['score'] else 'green'),'<ul>'+''.join('<li>'+ui.e(x)+'</li>' for x in r['reasons'])+'</ul>',ui.e(r['last_login'])] for r in rows]))
            elif page=='control-centre':
                jobs=[dict(r) for r in c.execute('SELECT * FROM operational_jobs ORDER BY id DESC LIMIT 15')]
                outbox=c.execute('SELECT COUNT(*) FROM notification_outbox').fetchone()[0]
                content=ui.page_header('SERVICE OPERATIONS','Control centre','Monitor local automation, integration boundaries, policy versions and organisation structure.')
                content+='<div class="stats-grid">'+ui.stat_card('Database','Connected','SQLite · WAL')+ui.stat_card('Policy version',pol['version'],'Version checked on save')+ui.stat_card('Outbox messages',outbox,'In-app ready; email not configured','orange')+'</div>'
                content+=panel('Daily governance job',('<p>Disables expired agency access in the mock directory, expires temporary cover, removes expired sessions and creates renewal/review reminders. One committed run per UTC day.</p>'+form('jobs','','Run daily job now')) if operator else '<p>IAM operators run this job manually or through the documented scheduler command.</p>')
                content+=table(['Job','State','Completed','Result'],[[ui.e(r['job_key']),ui.badge(r['status'],'green'),ui.e(r['finished_at']),ui.e(r['result_json'])] for r in jobs])
                if operator:
                    fields=''.join(field(label,key,'number',pol[key]) for key,label in [('dormant_days','Dormancy window · 30–180 days'),('renewal_days','Renewal reminder · 7–90 days'),('emergency_minutes','Emergency access · 5–30 minutes'),('cover_minutes','Site cover · 30–480 minutes'),('auto_expiry','Automatic agency expiry · 0 off / 1 on')])
                    content+=panel('Configure assurance policy',form('policy',f'<input type="hidden" name="version" value="{pol["version"]}">'+fields+field('Change reason','reason'),'Save versioned policy'))
                    content+=panel('Delegate qualification administration',form('delegate',field('SiteDelegate worker','employee_id',options=[(r['employee_id'],r['name']) for r in people if r['approved_role']=='SiteDelegate'])+field('Site','facility',options=[(x,x) for x in config.FACILITIES])+field('Expires within 90 days','expires_on','date'),'Save delegation')) if any(r['approved_role']=='SiteDelegate' for r in people) else panel('Delegated administration','<p>Onboard a worker with the SiteDelegate role to enable site-scoped qualification administration. Then grant a delegation here for up to 90 days. This does not grant global workforce or audit access.</p>')
                content+=panel('Organisation / site / team',table(['Organisation','Site','Team','Workers'],[["Sunhaven Care",ui.e(r['name']),ui.e(r['team']),r['workers']] for r in c.execute('SELECT s.name,t.name team,COUNT(m.employee_id) workers FROM sites s JOIN teams t USING(site_id) LEFT JOIN team_members m USING(team_id) GROUP BY t.team_id ORDER BY s.name')]))
                content+=panel('Integration readiness',table(['Component','Working capability','Connection state'],[
                    ['Entra / OIDC','Tenant and immutable-object binding; production configuration gate','Tenant test required'],
                    ['Graph / Microsoft 365','Original scripts preserved; portal connector is mock','Live portal mutations disabled'],
                    ['Okta / HRIS / payroll / rostering','Versioned connector contract; reviewed roster CSV','External adapter and credentials required'],
                    ['SCIM','Read-only user representation at /api/v1/scim/Users','Not a full SCIM provisioning server'],
                    ['SIEM','Sanitised NDJSON audit export and local integrity check','Remote transport and retention required'],
                    ['Email','Durable notification outbox','No messages sent; email provider required'],
                    ['API','Session-authenticated, role-scoped paginated reads','/api/v1/docs']]))
                content+='<p><a href="/api/v1/docs">Open API documentation</a> · <a href="/security-assurance">Verify audit integrity</a> · <a href="/automation">Preview agency expiry</a></p>'
        if (query.get('saved') or [''])[0]=='1':content=ui.alert('Action completed and audit evidence recorded.','success')+content
        self.send_html(ui.layout({'qualifications':'Qualifications','coverage':'Temporary & emergency access','insights':'Risk insights','control-centre':'Control centre'}[page],content,user,active=page))

    def assurance_save(self,action,query=None):
        user=self.require_login()
        if not user:return
        data=self.form();eid=user['employee_id'];dest='control-centre'
        try:
            if action=='qualification':a.verify_qualification(eid,data);dest='qualifications'
            elif action=='cover':a.request_cover(eid,data);dest='coverage'
            elif action=='cover-decision':a.decide_cover(eid,data);dest='coverage'
            elif action=='emergency':a.emergency(eid,data);dest='coverage'
            elif action=='emergency-review':a.review_emergency(eid,data);dest='coverage'
            elif action=='policy':a.save_policy(eid,data)
            elif action=='delegate':a.delegate(eid,data)
            elif action=='jobs':a.run_jobs(eid)
            else:raise ValueError('Unknown action.')
        except PermissionError as exc:return self.error_page('Access denied',str(exc),403,user)
        except ledger.IntegrityError:raise
        except (ValueError,RuntimeError) as exc:return self.error_page('Check the request',str(exc),400,user)
        self.redirect('/'+dest+'?saved=1')

    def assurance_api(self,resource,query=None):
        user=self.user();qid=getattr(self,'request_id','')
        def failure(code,msg,status):return self.send_json({'error':{'code':code,'message':msg},'request_id':qid},status)
        if not user:return failure('unauthenticated','Sign in to the portal before calling the API.',401)
        query=query or {};eid=user['employee_id']
        if not auth.has_role(eid,GOV):return failure('forbidden','A governance role is required.',403)
        try:
            page=int((query.get('page') or ['1'])[0]);size=int((query.get('page_size') or ['25'])[0])
            if not 1<=page<=1000000 or not 1<=size<=100:raise ValueError()
        except (ValueError,TypeError):return failure('invalid_pagination','page must be positive; page_size must be 1–100.',400)
        with database.connect() as c:
            allowed=a.scopes(c,eid)
            if resource=='docs':return self.send_json({'version':config.RELEASE_VERSION,'authentication':'Portal session cookie; same-origin only','methods':['GET'],'pagination':{'page':1,'page_size':'1–100'},'resources':['employees','risks','qualifications','scim/Users','health','docs'],'errors':[400,401,403,404,429],'scim':'Read-only representation. SCIM writes/filter/bulk are not implemented.','request_id':qid})
            elif resource in ('employees','scim/Users','qualifications'):
                scope_params=sorted(allowed);marks=','.join('?' for _ in scope_params) or 'NULL'
                if resource=='qualifications':
                    base=' FROM qualifications q JOIN employees e USING(employee_id) WHERE e.facility IN ('+marks+')'
                    select='q.employee_id,q.kind,q.expires_on,q.verified_by,e.facility';order='q.id'
                else:
                    base=' FROM employees e WHERE e.facility IN ('+marks+')'
                    select='employee_id,name,worker_type,approved_role,facility,status';order='employee_id'
                total=c.execute('SELECT COUNT(*)'+base,scope_params).fetchone()[0]
                rows=[dict(r) for r in c.execute('SELECT '+select+base+' ORDER BY '+order+' LIMIT ? OFFSET ?',[*scope_params,size,(page-1)*size])]
                if resource=='scim/Users':return self.send_json({'schemas':['urn:ietf:params:scim:api:messages:2.0:ListResponse'],'totalResults':total,'startIndex':(page-1)*size+1,'itemsPerPage':len(rows),'Resources':[{'schemas':['urn:ietf:params:scim:schemas:core:2.0:User'],'id':r['employee_id'],'userName':r['employee_id'],'displayName':r['name'],'active':r['status']=='Active'} for r in rows],'readOnlyPreview':True})
                return self.send_json({'data':rows,'total':total,'page':page,'page_size':size,'request_id':qid})
            elif resource=='risks':rows=a.risk_inventory(c,eid)
            elif resource=='health':
                if not auth.has_role(eid,{'IAMOperator','Auditor'}):return failure('forbidden','Operator or auditor role required.',403)
                return self.send_json({'status':'ok','version':config.RELEASE_VERSION,'database':'connected','foreign_keys':bool(c.execute('PRAGMA foreign_keys').fetchone()[0]),'latest_job':dict(c.execute('SELECT job_key,status,finished_at FROM operational_jobs ORDER BY id DESC LIMIT 1').fetchone() or {}),'request_id':qid})
            else:return failure('not_found','Unknown API resource.',404)
        total=len(rows);rows=rows[(page-1)*size:page*size]
        if resource=='scim/Users':return self.send_json({'schemas':['urn:ietf:params:scim:api:messages:2.0:ListResponse'],'totalResults':total,'startIndex':(page-1)*size+1,'itemsPerPage':len(rows),'Resources':[{'schemas':['urn:ietf:params:scim:schemas:core:2.0:User'],'id':r['employee_id'],'userName':r['employee_id'],'displayName':r['name'],'active':r['status']=='Active'} for r in rows],'readOnlyPreview':True})
        return self.send_json({'data':rows,'total':total,'page':page,'page_size':size,'request_id':qid})

    def audit_log(self,query=None):
        user=self.require_roles(['Manager','Auditor','IAMOperator'],'/audit')
        if not user:return
        query=query or {};q=(query.get('q') or [''])[0].strip()[:100]
        try:page=max(1,int((query.get('page') or ['1'])[0]))
        except ValueError:return self.error_page('Invalid page','Use a positive page number.',400,user)
        where=' WHERE actor_id LIKE ? OR target_id LIKE ? OR action LIKE ? OR correlation_id LIKE ?'
        args=('%'+q+'%',)*4
        with database.connect() as c:
            total=c.execute('SELECT COUNT(*) FROM audit_events'+where,args).fetchone()[0]
            rows=[dict(r) for r in c.execute('SELECT * FROM audit_events'+where+' ORDER BY event_id DESC LIMIT 50 OFFSET ?',(*args,(page-1)*50))]
        content=ui.page_header('AUDIT INVESTIGATION','Trace a decision','Search actor, target, action or correlation ID across the full audit history. Expand an event to inspect its recorded evidence.','<a class="btn btn-secondary" href="/exports/audit">Export CSV</a>')
        content+='<form method="get" action="/audit" class="panel form-grid">'+field('Search audit history','q',value=q,required=False)+'<button class="btn btn-primary">Search events</button></form>'
        content+=panel('Matching events',table(['Correlation / UTC','Actor → target','Action','Result','Evidence'],[[ui.e(r['correlation_id'])+'<br>'+ui.e(r['event_time']),ui.e(r['actor_id'])+' → '+ui.e(r['target_id'] or '—'),ui.e(r['action']),ui.badge(r['result'],'green' if r['result']=='PASS' else 'red'),'<details><summary>Inspect evidence</summary><pre class="result-json">'+ui.e(r['details'] or '{}')+'</pre></details>'] for r in rows]))
        content+=f'<div class="pagination"><span>{total} results · page {page} · up to 50 per page</span><div class="buttons">'
        if page>1:content+='<a class="btn btn-secondary" href="/audit?'+ui.e(urlencode({'q':q,'page':page-1}))+'">Previous</a>'
        if page*50<total:content+='<a class="btn btn-secondary" href="/audit?'+ui.e(urlencode({'q':q,'page':page+1}))+'">Next</a>'
        content+='</div></div>'
        self.send_html(ui.layout('Audit investigation',content,user,active='audit'))
