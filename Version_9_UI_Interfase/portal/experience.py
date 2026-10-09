from clock import utc_today
"""Version 4 workspace: scoped discovery, alerts, checklists and reporting."""
from datetime import date, timedelta
from urllib.parse import urlencode
from collections import Counter
import json
import auth,audit,config,database,governance,ui

GOV=['Manager','Auditor','IAMOperator']
STEPS=['Verify workforce details','Complete induction','Confirm role and facility','Review resident assignments']
SCHEMA='''
CREATE TABLE IF NOT EXISTS notification_reads (
 employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 notification_key TEXT NOT NULL, read_at TEXT NOT NULL,
 PRIMARY KEY(employee_id,notification_key)
);
CREATE TABLE IF NOT EXISTS onboarding_steps (
 employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 step_no INTEGER NOT NULL, completed INTEGER NOT NULL DEFAULT 0,
 evidence TEXT, updated_by TEXT, updated_at TEXT,
 PRIMARY KEY(employee_id,step_no)
);
'''

def alerts(user):
    import release_v11
    with database.connect() as c:
        args=release_v11.inbox_context(c,user['employee_id'])
        return [dict(r) for r in c.execute(release_v11.INBOX,args)]

def chart_panel():
    with database.connect() as c:
        employees=c.execute("SELECT approved_role,facility FROM employees WHERE status='Active'").fetchall()
    views=[]
    for facility in ['All facilities']+config.FACILITIES:
        counts=Counter(e['approved_role'] for e in employees if facility=='All facilities' or e['facility']==facility)
        bars=''; maximum=max(counts.values(),default=1)
        for role in config.ALLOWED_ROLES:
            n=counts[role]
            bars+=f'<div class="metric-bar"><span>{ui.e(role)}</span><div><i style="width:{n/maximum*100:.2f}%"></i></div><b>{n}</b></div>'
        views.append(f'<div class="chart-view" data-facility="{ui.e(facility)}" {"hidden" if facility!="All facilities" else ""}><div class="chart-total"><strong>{sum(counts.values())}</strong><span>active workers</span></div>{bars}</div>')
    opts=''.join(f'<option>{ui.e(f)}</option>' for f in ['All facilities']+config.FACILITIES)
    return f'<section class="panel analytics-panel"><div class="panel-head"><div><span class="eyebrow">WORKFORCE ANALYTICS</span><h3>Who has access?</h3><p class="muted">Explore the live role distribution by facility.</p></div><label class="chart-select">Facility<select id="chartFacility">{opts}</select></label></div><div aria-live="polite">'+''.join(views)+'</div></section>'

def pdf_document(lines):
    """Small dependency-free, paginated PDF for the ASCII aggregate report."""
    import textwrap
    text=[]
    for line in lines:text.extend(textwrap.wrap(str(line),90) or [''])
    pages=[text[i:i+43] for i in range(0,len(text),43)] or [[]]
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    kids=[]
    def literal(s):return s.encode('latin-1','replace').replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')
    for number,page in enumerate(pages,1):
        pid=len(objects)+1;cid=pid+1;kids.append(f'{pid} 0 R')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {cid} 0 R >>'.encode())
        commands=b'0.12 0.23 0.22 rg BT /F1 11 Tf 48 744 Td 15 TL\n'
        for line in page:commands+=b'('+literal(line)+b') Tj T*\n'
        commands+=b'ET BT /F1 9 Tf 48 30 Td (Sunhaven Care IAM 10.0 - Page '+str(number).encode()+b') Tj ET'
        objects.append(b'<< /Length '+str(len(commands)).encode()+b' >>\nstream\n'+commands+b'\nendstream')
    objects[1]=f'<< /Type /Pages /Count {len(pages)} /Kids [{" ".join(kids)}] >>'.encode()
    output=b'%PDF-1.4\n';offsets=[0]
    for i,obj in enumerate(objects,1):offsets.append(len(output));output+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    start=len(output);output+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]:output+=f'{offset:010} 00000 n \n'.encode()
    return output+f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()

class Experience:
    def notifications_page(self,query=None):
        user=self.require_login()
        if not user:return
        items=alerts(user);cards=''
        for a in items:
            action=ui.badge('Read','neutral') if a['read'] else f'<form method="post" action="/notifications/read"><input type="hidden" name="key" value="{ui.e(a["key"])}"><button class="btn btn-small btn-secondary">Mark read</button></form>'
            cards+=f'<article class="panel notification-card {"is-read" if a["read"] else ""}"><span class="notification-dot badge-{a["tone"]}"></span><div><span class="eyebrow">{ui.e(a["title"])}</span><h3><a href="{ui.e(a["href"])}">{ui.e(a["text"])}</a></h3><small>Live reminder · marking read does not resolve the issue</small></div>{action}</article>'
        content=ui.page_header('YOUR INBOX','Stay ahead of the next action',f'{sum(not a["read"] for a in items)} unread reminders across {len(items)} current items.')
        self.send_html(ui.layout('Notifications',content+(cards or '<div class="empty-state"><h3>You’re all caught up</h3><p>No current reminders for your access scope.</p></div>'),user,active='notifications'))

    def notification_read(self,query=None):
        user=self.require_login()
        if not user:return
        key=self.form().get('key','')
        if key not in {a['key'] for a in alerts(user)}:return self.error_page('Reminder unavailable','This reminder is outside your scope or no longer current.',404)
        with database.connect() as c:c.execute('INSERT OR REPLACE INTO notification_reads VALUES (?,?,?)',(user['employee_id'],key,governance.now()))
        self.redirect('/notifications')

    def search_page(self,query=None):
        user=self.require_login()
        if not user:return
        term=(query.get('q') or [''])[0].strip()[:100];elevated=auth.has_role(user['employee_id'],GOV);groups=[]
        if len(term)>=2:
            pattern='%'+term.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
            with database.connect() as c:
                if elevated:
                    workers=c.execute("SELECT employee_id,name,approved_role FROM employees WHERE name LIKE ? ESCAPE '\\' OR employee_id LIKE ? ESCAPE '\\' OR email LIKE ? ESCAPE '\\' LIMIT 30",(pattern,pattern,pattern)).fetchall()
                    groups.append(('Workers',[(r['name'],r['approved_role'],'/employees/'+r['employee_id']) for r in workers]))
                    notes=c.execute("SELECT employee_id,category,body FROM work_notes WHERE body LIKE ? ESCAPE '\\' ORDER BY note_id DESC LIMIT 20",(pattern,)).fetchall()
                    groups.append(('Notes',[(r['category'],r['body'][:160],'/employees/'+r['employee_id']) for r in notes]))
                    tasks=c.execute("SELECT title,status FROM remediation_tasks WHERE title LIKE ? ESCAPE '\\' LIMIT 20",(pattern,)).fetchall()
                    groups.append(('Remediation',[(r['title'],r['status'],'/operations') for r in tasks]))
                req=c.execute("SELECT request_id,requested_role,status FROM access_requests WHERE (reason LIKE ? ESCAPE '\\' OR requested_role LIKE ? ESCAPE '\\')"+('' if elevated else ' AND employee_id=?')+' ORDER BY request_id DESC LIMIT 30',(pattern,pattern) if elevated else (pattern,pattern,user['employee_id'])).fetchall()
                groups.append(('Requests',[(f'REQ-{r["request_id"]:04} · '+r['requested_role'],r['status'],f'/requests/{r["request_id"]}') for r in req]))
        content=ui.page_header('WORKSPACE SEARCH','Find the right record','Search workers, requests, notes and remediation within your role’s access scope.')
        content+=f'<form method="get" action="/search" class="panel search-form"><input class="search" name="q" value="{ui.e(term)}" minlength="2" maxlength="100" required aria-label="Search workspace" placeholder="Name, employee ID, request or note…"><button class="btn btn-primary">Search</button></form>'
        count=0
        for title,rows in groups:
            if rows:
                count+=len(rows);content+=f'<section class="panel"><h3>{title}</h3>'+''.join(f'<a class="search-result" href="{ui.e(href)}"><b>{ui.e(label)}</b><span>{ui.e(detail)}</span><i>→</i></a>' for label,detail,href in rows)+'</section>'
        if term and not count:content+='<div class="empty-state"><h3>No matching records</h3><p>Use at least two characters and try a different search.</p></div>'
        self.send_html(ui.layout('Search',content,user))

    def request_history(self,request_id,query=None):
        user=self.require_login()
        if not user:return
        with database.connect() as c:
            r=c.execute('SELECT * FROM access_requests WHERE request_id=?',(request_id,)).fetchone()
            if not r:return self.not_found()
            if r['employee_id']!=user['employee_id'] and not auth.has_role(user['employee_id'],GOV):return self.error_page('Access denied','This request is outside your scope.',403)
            s=c.execute('SELECT * FROM request_snapshots WHERE request_id=?',(request_id,)).fetchone()
        entries=[('Request submitted',r['created_at'],r['employee_id'],r['reason'])]
        if r['decision_by']:entries.append((r['status'] if r['status']=='Rejected' else 'Approved',r['decided_at'] or 'Legacy timestamp unavailable',r['decision_by'],r['decision_note']))
        if s and s['executed_at']:entries.append(('Change implemented',s['executed_at'],s['executed_by'],'Previous role: '+s['role_before']+' · Previous facility: '+s['facility_before']))
        timeline=''.join(f'<article class="history-item"><div class="history-marker">{i}</div><div><span class="eyebrow">{ui.e(when)}</span><h3>{ui.e(title)}</h3><small>Actor {ui.e(actor)}</small><p class="note-body">{ui.e(body)}</p></div></article>' for i,(title,when,actor,body) in enumerate(entries,1))
        content=ui.page_header('APPROVAL HISTORY',f'REQ-{int(request_id):04}',r['requested_role']+' · '+r['facility'],ui.badge(r['status'],'blue'))+'<section class="panel history-list">'+timeline+'</section><a class="btn btn-secondary" href="/requests">Back to requests</a>'
        self.send_html(ui.layout('Approval history',content,user,active='requests'))

    def onboarding_page(self,query=None):
        user=self.require_roles(GOV,'/onboarding')
        if not user:return
        selected=(query.get('employee') or [''])[0]
        with database.connect() as c:
            workers=c.execute("SELECT employee_id,name,approved_role FROM employees WHERE status='Active' ORDER BY name").fetchall()
            if selected not in {w['employee_id'] for w in workers}:selected=workers[0]['employee_id'] if workers else ''
            saved={r['step_no']:r for r in c.execute('SELECT * FROM onboarding_steps WHERE employee_id=?',(selected,))}
        opts=''.join(f'<option value="{w["employee_id"]}" {"selected" if w["employee_id"]==selected else ""}>{ui.e(w["name"])} · {ui.e(w["approved_role"])}</option>' for w in workers)
        editable=auth.has_role(user['employee_id'],['Manager','IAMOperator']);done=sum(bool(r['completed']) for r in saved.values());cards=''
        for i,title in enumerate(STEPS):
            r=saved.get(i);complete=bool(r and r['completed'])
            cards+=f'<label class="checklist-row"><input type="checkbox" name="step_{i}" value="1" {"checked" if complete else ""} {"disabled" if not editable else ""}><span><b>{ui.e(title)}</b><small>{ui.e((r["evidence"] or "") if r else "Not yet recorded")}</small>{("<small>Updated by "+ui.e(r["updated_by"])+" · "+ui.e(r["updated_at"])+"</small>") if r else ""}</span>{ui.badge("Complete" if complete else "To do","green" if complete else "neutral")}</label>'
        content=ui.page_header('JOINER WORKSPACE','A confident start for every worker','Track induction evidence without granting or changing access.')+f'<form method="get" action="/onboarding" class="panel toolbar"><label for="onboardWorker">Worker</label><select id="onboardWorker" name="employee">{opts}</select><button class="btn btn-secondary">Open checklist</button></form>'
        content+=f'<section class="panel"><div class="panel-head"><h3>{done} of {len(STEPS)} steps complete</h3><button class="btn btn-ghost" type="button" id="checkAllSteps" {"disabled" if not editable else ""}>Select all steps</button></div><progress value="{done}" max="4" aria-label="Onboarding progress"></progress><form method="post" action="/onboarding"><input type="hidden" name="employee_id" value="{ui.e(selected)}">{cards}'
        if editable:content+='<div class="field"><label for="checkEvidence">Evidence for this update</label><textarea id="checkEvidence" name="evidence" minlength="10" maxlength="2000" required rows="3" placeholder="Describe what you verified…"></textarea></div><div class="form-actions"><button class="btn btn-primary">Save checklist</button></div>'
        content+='</form></section>'
        self.send_html(ui.layout('Onboarding',content,user,active='onboarding'))

    def onboarding_save(self,query=None):
        user=self.require_roles(['Manager','IAMOperator'],'/onboarding')
        if not user:return
        d=self.form();eid=d.get('employee_id')
        try:why=governance.reason(d.get('evidence'))
        except ValueError as exc:return self.error_page('Evidence required',str(exc),400)
        with database.connect() as c:
            c.execute('BEGIN IMMEDIATE');governance.require(c,user['employee_id'],{'Manager','IAMOperator'})
            if not c.execute("SELECT 1 FROM employees WHERE employee_id=? AND status='Active'",(eid,)).fetchone():return self.error_page('Worker unavailable','Select an active worker.',400)
            for i in range(len(STEPS)):
                old=c.execute('SELECT completed FROM onboarding_steps WHERE employee_id=? AND step_no=?',(eid,i)).fetchone()
                complete=int(d.get(f'step_{i}')=='1')
                if not old or old['completed']!=complete:c.execute('INSERT INTO onboarding_steps VALUES (?,?,?,?,?,?) ON CONFLICT(employee_id,step_no) DO UPDATE SET completed=excluded.completed,evidence=excluded.evidence,updated_by=excluded.updated_by,updated_at=excluded.updated_at',(eid,i,complete,why,user['employee_id'],governance.now()))
            governance.event(c,user['employee_id'],eid,'ONBOARDING_UPDATED',{'evidence':why,'completed':[i for i in range(len(STEPS)) if d.get(f'step_{i}')=='1']})
        self.redirect('/onboarding?'+urlencode({'employee':eid}))

    def reports_page(self,query=None):
        user=self.require_roles(GOV,'/reports')
        if not user:return
        facility=(query.get('facility') or [''])[0];status=(query.get('status') or [''])[0]
        if facility and facility not in config.FACILITIES or status and status not in config.STATUSES:return self.error_page('Invalid filter','Choose a listed facility and status.',400)
        with database.connect() as c:
            workers=c.execute('SELECT employee_id,approved_role,status,facility FROM employees WHERE (?="" OR facility=?) AND (?="" OR status=?)',(facility,facility,status,status)).fetchall()
        counts=Counter(w['approved_role'] for w in workers);states=Counter(w['status'] for w in workers)
        lines=['SUNHAVEN CARE IAM','Workforce summary report','Generated UTC: '+governance.now(),'Synthetic demonstration data - mock directory','', 'Facility: '+(facility or 'All facilities'),'Status: '+(status or 'All statuses'),'Workers matching filters: '+str(len(workers)),'','ROLE DISTRIBUTION']
        lines += [f'{role}: {counts[role]}' for role in config.ALLOWED_ROLES]+['','STATUS DISTRIBUTION']+[f'{s}: {states[s]}' for s in config.STATUSES]
        lines+=['','Scope: workforce counts only. Filters do not change access.','This report is not evidence of live Microsoft Graph provisioning.']
        if (query.get('format') or [''])[0]=='pdf':
            raw=pdf_document(lines);audit.record(user['employee_id'],None,'REPORT_EXPORTED','PASS',{'facility':facility,'status':status,'worker_count':len(workers)})
            self.send_response(200);self.send_header('Content-Type','application/pdf');self.send_header('Content-Disposition','attachment; filename="sunhaven-workforce-summary.pdf"');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw);return
        url='/reports?'+urlencode({'facility':facility,'status':status,'format':'pdf'})
        form=f'<form class="panel toolbar" method="get" action="/reports"><label>Facility <select name="facility"><option value="">All facilities</option>{ui.facility_options(facility)}</select></label><label>Status <select name="status"><option value="">All statuses</option>'+''.join(f'<option {"selected" if s==status else ""}>{s}</option>' for s in config.STATUSES)+'</select></label><button class="btn btn-primary">Apply filters</button></form>'
        content=ui.page_header('REPORT CENTRE','Clear answers, ready to share','Generate a PDF summary from the current workforce filters.',f'<a class="btn btn-primary" href="{ui.e(url)}">Download PDF ↓</a>')+form+f'<section class="panel"><h3>{len(workers)} matching workers</h3>'+''.join(f'<div class="report-line"><span>{ui.e(role)}</span><b>{counts[role]}</b></div>' for role in config.ALLOWED_ROLES)+'</section>'
        self.send_html(ui.layout('Reports',content,user,active='reports'))
