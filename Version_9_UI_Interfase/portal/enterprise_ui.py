"""Unified governance console. Every mutation passes service-side authorization."""
import json, sqlite3, subprocess, itertools
import audit
FIELD_IDS=itertools.count()
import auth,database,enterprise,integrations,ui

def field(name,label,kind='text',value='',options=None):
    fid=name+'-'+str(next(FIELD_IDS))
    label=f'<label for="{ui.e(fid)}">{ui.e(label)}</label>'
    if options is not None:control=f'<select id="{ui.e(fid)}" name="{ui.e(name)}">'+''.join(f'<option value="{ui.e(x)}">{ui.e(x)}</option>' for x in options)+'</select>'
    elif kind=='textarea':control=f'<textarea id="{ui.e(fid)}" name="{ui.e(name)}" rows="3" minlength="10" maxlength="2000" required>{ui.e(value)}</textarea>'
    else:control=f'<input id="{ui.e(fid)}" name="{ui.e(name)}" type="{kind}" value="{ui.e(value)}" maxlength="140" required>'
    return '<div class="field">'+label+control+'</div>'

def form(action,body,button):return f'<form method="post" action="{action}" class="stack-form">{body}<button class="btn btn-primary" type="submit">{ui.e(button)}</button></form>'
def hidden(k,v):return f'<input type="hidden" name="{ui.e(k)}" value="{ui.e(v)}">'
def table(headers,rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+ui.e(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+(''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows) or f'<tr><td colspan="{len(headers)}">No records yet.</td></tr>')+'</tbody></table></div>'
def panel(title,body):return '<section class="panel"><h3>'+ui.e(title)+'</h3>'+body+'</section>'

class EnterprisePages:
    def enterprise_page(self,page='hub',query=None):
        user=self.require_login() if page=='catalog' else self.require_roles(['Manager','Auditor','IAMOperator'],'/'+page)
        if not user:return
        actor=user['employee_id'];state=enterprise.inventory(actor)
        can=auth.has_role(actor,['Manager','IAMOperator']);operator=auth.has_role(actor,['IAMOperator'])
        titles={'hub':'Unified governance','catalog':'Access catalogue','services':'Service & agent identities','incidents':'Incident response','policy-lab':'Conditional access lab','integrations':'Original project integrations'}
        intro={'hub':'Your complete local workspace, with the original Microsoft lab preserved alongside it.','catalog':'Request a time-limited workspace. A different manager or operator must approve it. Expiry is enforced on every resource request.','services':'Register synthetic service and agent identities, assign owners and scopes, evaluate policy, and disable locally.','incidents':'Track investigations with evidence. Changes require an approved, active incident-responder package.','policy-lab':'Test declared risk, device and authentication inputs. This simulator does not enforce Entra sign-in policy.','integrations':'Run the original SITAS engine and SAIF validator here. Microsoft tenant changes remain in the original approved scripts.'}
        content=ui.page_header('SUNHAVEN / UNIFIED 8.0',titles[page],intro[page])
        content+='<nav class="console-tabs" aria-label="Governance modules">'+''.join(f'<a class="btn btn-ghost" href="/{k}">{ui.e(v)}</a>' for k,v in titles.items() if state['governor'] or k=='catalog')+'</nav>'
        if page=='hub':
            content+='<div class="stats-grid">'+ui.stat_card('Original files retained','545','Source, policy and evidence baseline','blue')+ui.stat_card('Local time-bound packages',3,'Approval · expiry · separation of duties','green')+ui.stat_card('Open incidents',sum(x['status']!='Resolved' for x in state['incidents']),'Latest 100 records','orange')+'</div>'
            cards=[('catalog','Access packages','Independent decisions, one-hour responder activation and expiring resources.'),('services','Nonhuman identities','Ownership, scope allowlists, bounded lifetime and disable controls.'),('integrations','SITAS + SAIF','Original analysis engines connected to this portal; live scripts preserved.'),('policy-lab','Policy what-if lab','Explain passkey, device and risk decisions using synthetic inputs.'),('incidents','Response evidence','Audited incident transitions with time-limited response access.'),('workforce-sync','Roster reconciliation','Reviewed HR import, safe preview and leaver/agency updates.'),('campaigns','Quarterly reviews','Independent certification, revocation and remediation.'),('automation','Workforce automation','Reviewed agency expiry alongside joiner, mover and leaver workflows.')]
            content+='<div class="module-grid">'+''.join(f'<a class="module-card" href="/{k}"><span class="eyebrow">EXPLORE MODULE</span><h3>{ui.e(n)}</h3><p>{ui.e(d)}</p><b>Open workspace →</b></a>' for k,n,d in cards)+'</div>'
            content+=panel('Release boundaries','<p>Original Entra/Graph/Flask and B2B invitation modules are retained under <code>original/</code>. The v10 portal uses a synthetic directory. Original tenant writes are not automatically dispatched by this console. Device posture, passkeys and cloud agent credentials require a configured identity provider.</p>')
        elif page=='catalog':
            content+='<div class="module-grid">'
            for pid,p in enterprise.PACKAGES.items():
                content+=panel(p['name'],f'<p>{ui.e(p["description"])}</p><p><b>{p["minutes"]} minutes</b> · Eligible roles: {ui.e(", ".join(sorted(p["roles"])))}</p>'+('<a class="btn btn-primary" href="/catalog/resource/'+pid+'">Open approved workspace</a>' if pid in state['grants'] else form('/console/catalog-request',hidden('package_id',pid)+field('reason','Business reason','textarea'),'Request access')))
            content+='</div>'
            rows=[]
            for r in state['requests']:
                action=''
                if can and r['employee_id']!=actor and r['status'] in ('Pending','Approved'):
                    opts=['Approved','Rejected'] if r['status']=='Pending' else ['Revoked']
                    action=form('/console/catalog-decision',hidden('id',r['id'])+field('decision','Decision',options=opts)+field('reason','Decision evidence','textarea'),'Record decision')
                rows.append([ui.e(r['id']),ui.e(r['employee_id']),ui.e(r['package_id']),ui.badge(r['status']),ui.e(r['expires_at'] or '—'),ui.e(r['reason']),action])
            content+=panel('Latest 100 requests',table(['ID','Worker','Package','State','Expiry UTC','Reason','Review'],rows))
        elif page=='services':
            if operator:content+=panel('Register a local identity',form('/console/service-add',field('name','Identity name',value='Care summary assistant')+field('kind','Identity type',options=['Agent','Service'])+field('owner_id','Active manager / operator ID',value='SC1002')+field('scopes','Allowed scopes (comma separated)',value='metrics.read,training.read')+field('days','Lifetime in days (1–90)','number','7'),'Register identity'))
            rows=[]
            for r in state['services']:
                action=''
                if operator:action=form('/console/service-action',hidden('id',r['id'])+field('action','Action',options=['evaluate','disable'])+field('scope','Local scope',options=sorted(enterprise.SCOPES)),'Apply')
                rows.append([ui.e(r['name']),ui.e(r['kind']),ui.e(r['owner_id']),ui.e(', '.join(json.loads(r['scopes']))),ui.e(r['expires_at']),ui.badge(r['status']),action])
            content+=panel('Local inventory — latest 100',table(['Name','Type','Owner','Scopes','Expiry UTC','State','Action'],rows))
            content+=ui.alert('Registry and policy evaluations are local. No agent is deployed and no cloud credential is created.')
        elif page=='incidents':
            enabled='incident-response' in state['grants']
            if enabled:content+=panel('Open an incident',form('/console/incident',hidden('action','create')+field('title','Incident title')+field('severity','Severity',options=['Low','Medium','High','Critical'])+field('owner_id','Response owner ID',value=actor)+field('evidence','Initial evidence','textarea'),'Open incident'))
            else:content+=ui.alert('Request Temporary incident responder in the access catalogue to change incident records.')
            rows=[]
            for r in state['incidents']:
                next_states=sorted(enterprise.TRANSITIONS[r['status']]);action=''
                if enabled and next_states:action=form('/console/incident',hidden('action','transition')+hidden('id',r['id'])+field('status','Next state',options=next_states)+field('evidence','Transition evidence','textarea'),'Update incident')
                rows.append([ui.e(r['id']),ui.e(r['title']),ui.badge(r['severity']),ui.e(r['owner_id']),ui.badge(r['status']),ui.e(r['evidence']),action])
            content+=panel('Latest 100 incidents',table(['ID','Title','Severity','Owner','Status','Evidence','Action'],rows))
        elif page=='policy-lab':
            content+=panel('Explain a simulated decision',form('/console/policy',field('risk','Sign-in risk',options=['Low','Medium','High'])+field('device','Device posture',options=['Managed','Unmanaged'])+field('auth','Authentication method',options=['Password','Push MFA','Passkey'])+field('active','Identity active?',options=['Yes','No']),'Evaluate policy'))
        elif page=='integrations':
            content+=panel('Original feature preservation',table(['Component','Integration mode'],[[ui.e(a),ui.e(b)] for a,b in [('Flask OIDC care portal','Retained, run separately with the original tenant configuration'),('Graph PowerShell JML / readback / review','Retained, exact approval gates and tenant checks unchanged'),('SITAS attack-path engine','Callable below with all six scenarios and current portal workforce'),('SAIF agency federation','Original validator + invitation preview below; real Graph invitation retained in original/'),('Policies, tests and evidence','All 545 original files preserved byte-for-byte; manifest included')]]))
            if can:
                content+=panel('Run original SITAS',form('/console/integration',hidden('kind','sitas'), 'Analyze six scenarios + portal workforce'))
                content+=panel('Validate an external worker',form('/console/integration',hidden('kind','saif')+field('workerId','Fictional worker ID',value='EXT-DEMO-01')+field('displayName','Fictional name',value='Demo Agency Worker')+field('email','Agency email','email','demo@sydneycare.example')+field('agencyId','Agency',options=['AG001','AG002','AG003']),'Validate & preview invitation'))
            for r in integrations.latest():
                result=json.loads(r['result_json']);body=f'<p>{ui.e(r["created_at"])} UTC · {ui.e(r["actor_id"])}</p>'
                if r['kind']=='sitas':
                    rows=[[ui.e(s['scenarioName']),ui.e(s['baseline']['risk']['riskScore']),ui.badge(s['comparison']['baselineStatus']),ui.badge(s['comparison']['protectedStatus']),ui.e(s['comparison']['result'])] for s in result['scenarios']]
                    body+=table(['Scenario','Risk / 25','Before','After','Control result'],rows)
                    body+='<p>Current portal mapping findings: '+ui.e(json.dumps(result['mapping_findings']))+'</p>'
                body+='<details><summary>Read complete result</summary><pre class="result-json">'+ui.e(json.dumps(result,indent=2))+'</pre></details>'
                content+=panel(r['kind'].upper()+' run '+str(r['id']),body)
        self.send_html(ui.layout(titles[page],content,user,active='hub' if page!='catalog' else 'catalog'))

    def enterprise_save(self,action,query=None):
        user=self.require_login()
        if not user:return
        d=self.form();actor=user['employee_id'];target='/hub';result=None
        try:
            if action=='catalog-request':enterprise.request_package(actor,d.get('package_id'),d.get('reason'));target='/catalog'
            elif action=='catalog-decision':enterprise.decide_package(actor,d.get('id'),d.get('decision'),d.get('reason'));target='/catalog'
            elif action=='service-add':enterprise.add_service(actor,d);target='/services'
            elif action=='service-action':result=enterprise.service_action(actor,d.get('id'),d.get('action'),d.get('scope'));target='/services'
            elif action=='incident':enterprise.incident(actor,d);target='/incidents'
            elif action=='policy':
                if not auth.has_role(actor,['Manager','Auditor','IAMOperator']):raise PermissionError('Governance role required.')
                result=enterprise.evaluate_policy(d);target='/policy-lab'
            elif action=='integration':integrations.run(actor,d.get('kind'),d);target='/integrations'
            else:return self.not_found()
        except PermissionError as exc:
            audit.record(actor,None,'CONSOLE_DENIED','DENIED',{'action':action})
            return self.error_page('Action denied',str(exc),403)
        except ValueError as exc:return self.error_page('Action could not complete',str(exc),409)
        except (sqlite3.IntegrityError,subprocess.TimeoutExpired):return self.error_page('Action could not complete','Check required fields or retry the original module. No completed result was recorded.',409)
        if result:return self.send_html(ui.layout('Decision result',panel('Policy result','<pre class="result-json">'+ui.e(json.dumps(result,indent=2))+'</pre><a class="btn btn-primary" href="'+target+'">Return to workspace</a>'),user,active='hub'))
        self.redirect(target)

    def package_resource(self,pid,query=None):
        user=self.require_login()
        if not user:return
        with database.connect() as c:
            if not enterprise.has_access(c,user['employee_id'],pid):
                audit.record(user['employee_id'],pid,'PACKAGE_RESOURCE_DENIED','DENIED')
                return self.error_page('Access denied','A current approved package matching your worker state is required.',403)
            if pid=='quality-review':body='<p>Active workers: '+str(c.execute("SELECT COUNT(*) FROM employees WHERE status='Active'").fetchone()[0])+'</p><p>This view exposes aggregate synthetic metrics only.</p>'
            elif pid=='incident-response':body='<p>Your temporary response capability is active.</p><a href="/incidents" class="btn btn-primary">Manage incident cases</a>'
            else:body='<ol><li>Confirm sponsor and contract dates.</li><li>Use only assigned fictional resident records.</li><li>Report unexpected access immediately.</li><li>Lock shared workstations after each session.</li></ol>'
        self.send_html(ui.layout('Approved workspace',panel(enterprise.PACKAGES[pid]['name'],body),user,active='catalog'))
