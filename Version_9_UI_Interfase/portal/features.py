from datetime import timezone
"""Operational features with server-side authorisation and parameterised queries."""
import csv
import io
from datetime import datetime
import auth
import audit
import config
import database
import ui
import governance

GOVERNANCE = ['Manager','Auditor','IAMOperator']
CATEGORIES = ['Onboarding','Access review','Handover','Offboarding','General']

class Features:
    def notes_page(self, query=None):
        user=self.require_roles(GOVERNANCE, '/notes')
        if not user: return
        query=query or {};selected=(query.get('employee') or [''])[0];q=(query.get('q') or [''])[0][:100]
        page=int((query.get('page') or ['1'])[0])
        if not 1<=page<=1000000:raise ValueError('Use a positive page number.')
        where=' WHERE (n.body LIKE ? OR n.category LIKE ? OR e.name LIKE ?)';args=['%'+q+'%']*3
        if selected:where+=' AND n.employee_id=?';args.append(selected)
        base=' FROM work_notes n JOIN employees e ON n.employee_id=e.employee_id JOIN employees a ON n.author_id=a.employee_id'+where
        with database.connect() as conn:
            people=conn.execute('SELECT employee_id,name FROM employees ORDER BY name').fetchall()
            total=conn.execute('SELECT COUNT(*)'+base,args).fetchone()[0]
            notes=conn.execute('SELECT n.*,e.name,a.name AS author'+base+' ORDER BY n.note_id DESC LIMIT 24 OFFSET ?',[*args,(page-1)*24]).fetchall()
        opts=''.join(f'<option value="{ui.e(p["employee_id"])}" {"selected" if p["employee_id"]==selected else ""}>{ui.e(p["name"])}</option>' for p in people)
        form=''
        if auth.has_role(user['employee_id'],['Manager','IAMOperator']):
            cats=''.join(f'<option>{c}</option>' for c in CATEGORIES)
            form=f'''<form class="panel form-grid" method="post" action="/notes"><div class="field"><label for="note-worker">Worker</label><select id="note-worker" name="employee_id">{opts}</select></div><div class="field"><label for="category">Category</label><select id="category" name="category">{cats}</select></div><div class="field full"><label for="note-body">Operational note</label><textarea id="note-body" name="body" rows="4" minlength="5" maxlength="2000" required placeholder="Record the handover, decision or next action…"></textarea><small class="muted">5–2,000 characters. Keep passwords and clinical information out of workforce notes.</small></div><div class="form-actions full"><button class="btn btn-primary">Save note</button></div></form>'''
        cards=''.join(f'''<article class="panel note-card" data-searchable><div class="panel-head"><div>{ui.badge(n['category'],'blue')}<h3>{ui.e(n['name'])}</h3></div><span class="muted">{ui.e(n['created_at'][:10])}</span></div><p class="note-body">{ui.e(n['body'])}</p><footer>{ui.e(n['author'])} · <a href="/employees/{ui.e(n['employee_id'])}">{ui.e(n['employee_id'])}</a></footer></article>''' for n in notes)
        content=ui.page_header('TEAM WORKSPACE','Notes & handovers','Keep a clear, dated record of workforce decisions. Notes are append-only so the original context is preserved.')
        from assurance_ui import field
        from v10_ui import pager
        content+=form+'<form class="panel form-grid" method="get" action="/notes">'+field('Search all notes','q',value=q,required=False)+field('Worker','employee',value=selected,options=[('','All workers')]+[(p['employee_id'],p['name']) for p in people])+'<button class="btn btn-primary">Search notes</button></form><div class="notes-grid">'+(cards or '<p>No notes match these filters.</p>')+'</div>'
        from v11_ui import save_control
        content+=save_control('notes',{'q':q,'employee':selected})
        content+=pager('/notes',{'q':q,'employee':selected},page,total,24)
        self.send_html(ui.layout('Notes & handovers',content,user,active='notes'))

    def note_save(self, query=None):
        user=self.require_roles(['Manager','IAMOperator'],'/notes')
        if not user:return
        d=self.form(); body=d.get('body','').strip()
        if d.get('category') not in CATEGORIES or not 5<=len(body)<=2000:
            return self.error_page('Invalid note','Select a category and enter 5–2,000 characters.',400)
        with database.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            governance.require(conn,user["employee_id"],{"Manager","IAMOperator"})
            if not conn.execute('SELECT 1 FROM employees WHERE employee_id=?',(d.get('employee_id'),)).fetchone():
                return self.error_page('Invalid worker','Select an existing worker.',400)
            conn.execute('INSERT INTO work_notes(employee_id,author_id,category,body) VALUES (?,?,?,?)',(d['employee_id'],user['employee_id'],d['category'],body))
            audit.record_on(conn,user['employee_id'],d['employee_id'],'NOTE_ADDED','PASS',{'category':d['category']})
        self.redirect('/notes?saved=1')

    def requests_page(self, query=None):
        user=self.require_login()
        if not user:return
        governor=auth.has_role(user['employee_id'],GOVERNANCE)
        decider=auth.has_role(user['employee_id'],['Manager','IAMOperator'])
        with database.connect() as conn:
            sql='SELECT r.*, e.name FROM access_requests r JOIN employees e ON e.employee_id=r.employee_id'
            rows=conn.execute(sql+('' if governor else ' WHERE r.employee_id=?')+' ORDER BY r.request_id DESC LIMIT 100',() if governor else (user['employee_id'],)).fetchall()
        cards=''
        for r in rows:
            decision=''
            if decider and r['status']=='Pending' and r['employee_id']!=user['employee_id']:
                decision=f'''<form method="post" action="/requests/{r['request_id']}/decision" class="decision-form"><label for="decision-{r['request_id']}">Decision reason</label><input id="decision-{r['request_id']}" name="decision_note" required minlength="5" maxlength="1000" placeholder="Explain your decision"><button class="btn btn-primary btn-small" name="decision" value="Approved">Approve</button><button class="btn btn-danger btn-small" name="decision" value="Rejected">Reject</button></form>'''
            if r['status']=='Approved' and auth.has_role(user['employee_id'],['IAMOperator']) and r['employee_id']!=user['employee_id']:
                decision += f'<form method="post" action="/operations"><input type="hidden" name="action" value="execute"><input type="hidden" name="request_id" value="{r["request_id"]}"><button class="btn btn-primary">Execute approved change</button></form>'
            if r['status']=='Pending' and r['employee_id']==user['employee_id']:
                from v10_ui import action_form
                from assurance_ui import field
                decision+=action_form('cancel',f'<input type="hidden" name="id" value="{r["request_id"]}">'+field('Withdrawal reason','reason'),'Withdraw my request')
            cards+=f'''<article class="panel"><div class="panel-head"><div><span class="eyebrow">REQ-{r['request_id']:04} · {ui.e(r['created_at'][:10])}</span><h3>{ui.e(r['name'])}</h3></div>{ui.badge(r['status'],'orange' if r['status']=='Pending' else ('green' if r['status']=='Approved' else 'neutral'))}</div><p><b>{ui.e(r['requested_role'])}</b> · {ui.e(r['facility'])}</p><p class="note-body">{ui.e(r['reason'])}</p>{('<p class="muted">Decision: '+ui.e(r['decision_note'])+'</p>') if r['decision_note'] else ''}{decision}<a class="history-link" href="/requests/{r['request_id']}">View approval history →</a></article>'''
        form=f'''<details class="panel"><summary>+ Request a change to my access</summary><form class="form-grid request-form" method="post" action="/requests"><div class="field"><label for="req-role">Requested role</label><select id="req-role" name="requested_role">{ui.role_options(user['approved_role'])}</select></div><div class="field"><label for="req-facility">Facility</label><select id="req-facility" name="facility">{ui.facility_options(user['facility'])}</select></div><div class="field full"><label for="req-reason">Business reason</label><textarea id="req-reason" name="reason" required minlength="10" maxlength="2000" rows="3" placeholder="Explain why this access is needed…"></textarea></div><div class="form-actions full"><button class="btn btn-primary">Submit request</button></div></form></details>'''
        content=ui.page_header('ACCESS GOVERNANCE','Access requests','Request, review and record approval before a role change. An IAM operator executes an approved change within seven days. Self-execution and stale approvals are blocked.')+form+'<div class="notes-grid">'+(cards or '<div class="panel">No access requests yet.</div>')+'</div>'
        self.send_html(ui.layout('Access requests',content,user,active='requests'))

    def request_save(self,query=None):
        user=self.require_login()
        if not user:return
        d=self.form(); reason=d.get('reason','').strip()
        if d.get('requested_role') not in config.ALLOWED_ROLES or d.get('facility') not in config.FACILITIES or not 10<=len(reason)<=2000:
            return self.error_page('Invalid request','Select a valid role and facility, and enter a reason of 10–2,000 characters.',400)
        with database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute("SELECT 1 FROM access_requests WHERE employee_id=? AND requested_role=? AND facility=? AND status='Pending'",(user['employee_id'],d['requested_role'],d['facility'])).fetchone():
                return self.error_page('Request already open','A pending request for this role and facility already exists.',409)
            conn.execute('INSERT INTO access_requests(employee_id,requested_role,facility,reason) VALUES (?,?,?,?)',(user['employee_id'],d['requested_role'],d['facility'],reason))
            audit.record_on(conn,user['employee_id'],user['employee_id'],'ACCESS_REQUESTED','PASS',{'role':d['requested_role'],'facility':d['facility']})
        self.redirect('/requests')

    def request_decide(self,request_id,query=None):
        user=self.require_roles(['Manager','IAMOperator'],'/requests')
        if not user:return
        d=self.form(); note=d.get('decision_note','').strip()
        if d.get('decision') not in ('Approved','Rejected') or not 5<=len(note)<=1000:
            return self.error_page('Invalid decision','Choose approve or reject and provide a reason of 5–1,000 characters.',400)
        with database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            governance.require(conn,user['employee_id'],{'Manager','IAMOperator'})
            row=conn.execute('SELECT * FROM access_requests WHERE request_id=?',(request_id,)).fetchone()
            if not row:return self.not_found()
            if row['employee_id']==user['employee_id']:
                return self.error_page('Independent approval required','You cannot decide your own access request.',403)
            if row['status']!='Pending':return self.error_page('Already decided','This request has already been reviewed.',409)
            if row['requested_role']=='IAMOperator' and not auth.has_role(user['employee_id'],['IAMOperator']):
                return self.error_page('Privileged approval required','Only another IAM operator may approve privileged access.',403)
            if d['decision']=='Approved':
                import enterprise
                enterprise.active(conn,row['employee_id'])
                current=conn.execute('SELECT approved_role,facility FROM employees WHERE employee_id=?',(row['employee_id'],)).fetchone()
                conn.execute('INSERT INTO request_snapshots(request_id,role_before,facility_before) VALUES (?,?,?)',(request_id,current['approved_role'],current['facility']))
            conn.execute('UPDATE access_requests SET status=?,decision_by=?,decision_note=?,decided_at=? WHERE request_id=?',(d['decision'],user['employee_id'],note,datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds'),request_id))
            audit.record_on(conn,user['employee_id'],row['employee_id'],'REQUEST_DECIDED','PASS',{'request_id':request_id,'decision':d['decision']})
        self.redirect('/requests')

    def export_csv(self,kind,query=None):
        user=self.require_roles(GOVERNANCE,'/exports/'+kind)
        if not user:return
        queries={'employees':'SELECT employee_id,name,email,worker_type,approved_role,facility,status,start_date,end_date FROM employees ORDER BY employee_id',
        'audit':'SELECT correlation_id,actor_id,target_id,action,result,event_time FROM audit_events ORDER BY event_id DESC',
        'reviews':'SELECT employee_id,reviewer_id,decision,reason,review_date,exception_expiry,remediation_status FROM access_reviews ORDER BY review_id DESC'}
        with database.connect() as conn:
            cursor=conn.execute(queries[kind]); columns=[d[0] for d in cursor.description]; rows=cursor.fetchall()
        stream=io.StringIO(newline=''); writer=csv.writer(stream); writer.writerow(columns)
        for row in rows:
            values=[]
            for value in row:
                s='' if value is None else str(value)
                if s.lstrip().startswith(('=','+','-','@')) or s.startswith(('\t','\r','\n')):s="'"+s
                values.append(s)
            writer.writerow(values)
        raw=('\ufeff'+stream.getvalue()).encode('utf-8')
        audit.record(user['employee_id'],None,'CSV_EXPORTED','PASS',{'dataset':kind,'rows':len(rows)})
        self.send_response(200);self.send_header('Content-Type','text/csv; charset=utf-8');self.send_header('Content-Disposition',f'attachment; filename="sunhaven-{kind}.csv"');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)

    def guide_page(self,query=None):
        user=self.require_login()
        if not user:return
        items=[('1. Start with the workforce record','IAM operators create a Joiner from the workforce directory. Check the role, facility and sponsor; run a dry run before creating access.'),('2. Ask before changing access','Every worker can submit an access request. Managers or IAM operators review the business reason. A different operator must approve privileged requests. Approval records a decision; an IAM operator then uses Execute approved change.'),('3. Move with least privilege','Use the worker profile to preview Mover; execute changes through an approved request. Old roles and resident assignments are removed. The worker must sign in again after the change. Reassign residents in Security operations.'),('4. Leave a clear handover','Use Notes & handovers for induction, review decisions and offboarding context. Notes retain their original author and timestamp. Do not enter passwords or resident clinical information.'),('5. Review exceptions','Access reviews record Retain, Change, Remove or Temporary Exception. Exceptions require a future expiry. Change and Remove stay pending until remediation is handled outside this review form. Close pending reviews with evidence in Security operations.'),('6. End access promptly','The Leaver action disables the mock identity, removes roles and assignments, deletes active sessions and blocks portal access. Expired agency workers also cannot sign in.'),('7. Collect evidence','Run a compliance scan, inspect the audit log and export CSV evidence. Records labelled DEMO_FIXTURE are illustrative sample activity, not proof of actual actions.'),('8. Deployment boundary','This release is suitable for a controlled synthetic-data demonstration. Production configuration requires HTTPS, Entra sign-in, immutable account mappings and no automatic demo seed. Real Graph mutations are deliberately disabled pending integration testing.')]
        items += [
            ('How do I use the new dashboard and theme?', 'Choose a facility in Who has access? to filter the active workforce chart. Select dashboard statistics to open their related page. Use the half-circle header button to switch light/dark mode; the preference is saved in this browser.'),
            ('What can I search?', 'Use the header search or press /, then enter at least two characters. Managers, auditors and operators can search workers, notes, remediation task titles and requests. Other workers can search their own requests.'),
            ('How do notifications work?', 'Notifications are calculated when the page opens: pending requests, agency contracts due in 14 days or expired, and reviews overdue by 90 days. Mark read only changes your personal read status. It does not resolve the issue or send email.'),
            ('How do I complete onboarding?', 'Managers and operators choose an active worker on Onboarding, tick the verified steps and save with evidence. Select all steps is a convenience; save is still required. Uncheck a step to reopen it. The checklist records evidence and does not grant access.'),
            ('Where are approval history and PDF reports?', 'Open View approval history on an access request to see submission, decision and execution. Reports lets governance roles filter workforce counts by facility and status, then download an audited PDF summary.')
        ]
        cards=''.join(f'<details class="panel guide-item"><summary>{ui.e(title)}</summary><p>{ui.e(body)}</p></details>' for title,body in items)
        content=ui.page_header('HELP CENTRE','A simple guide to safer access','Practical notes for workers, managers and IAM operators.')+cards
        self.send_html(ui.layout('Help & guide',content,user,active='guide'))
