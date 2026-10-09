import database,auth,ui,governance,compliance

def options(rows,key,label):
    return ''.join(f'<option value="{ui.e(r[key])}">{ui.e(r[label])} ({ui.e(r[key])})</option>' for r in rows)

def field(label,name,opts=None):
    control=f'<select name="{name}">{opts}</select>' if opts is not None else f'<input name="{name}" required maxlength="2000">'
    return f'<div class="field"><label>{label}</label>{control}</div>'

def form(action,title,body):
    return f'<details class="panel"><summary>{title}</summary><form method="post" action="/operations" class="form-grid request-form"><input type="hidden" name="action" value="{action}">{body}{field("Reason or evidence", "reason")}<div class="form-actions full"><button class="btn btn-primary">Save operation</button></div></form></details>'

class Operations:
    def operations_page(self,query=None):
        user=self.require_roles(['Manager','Auditor','IAMOperator'],'/operations')
        if not user:return
        with database.connect() as c:
            workers=c.execute('SELECT * FROM employees ORDER BY name').fetchall()
            residents=c.execute('SELECT * FROM residents ORDER BY resident_id').fetchall()
            sessions=c.execute("SELECT e.name,e.employee_id,s.created_at,s.expires_at FROM sessions s JOIN employees e ON e.employee_id=s.employee_id WHERE expires_at>strftime('%Y-%m-%dT%H:%M:%S','now') ORDER BY expires_at").fetchall()
            tasks=c.execute('SELECT * FROM remediation_tasks ORDER BY task_id DESC LIMIT 100').fetchall()
            pending=c.execute("SELECT * FROM access_reviews WHERE remediation_status='Pending' ORDER BY review_id DESC").fetchall()
            links=c.execute('SELECT employee_id,resident_id FROM assignments WHERE active=1 ORDER BY employee_id').fetchall()
            owners=c.execute("SELECT DISTINCT e.employee_id,e.name FROM employees e JOIN employee_roles r ON r.employee_id=e.employee_id WHERE r.role IN ('Manager','IAMOperator') AND e.status='Active'").fetchall()
        findings=compliance.run_checks(store=False)
        content=ui.page_header('SECURITY OPERATIONS','Governance control centre','Track remediation, review sessions and manage resident assignments. Every operation requires a reason and creates an audit event.')
        content+='<div class="stats-grid">'+ui.stat_card('High or critical findings',sum(f['severity'] in ('High','Critical') for f in findings),'Current policy checks')+ui.stat_card('Open remediation tasks',sum(t['status']!='Resolved' for t in tasks),'Latest 100 tasks')+ui.stat_card('Unexpired sessions',len(sessions),'Local portal sessions')+ui.stat_card('Pending reviews',len(pending),'Waiting for follow-through')+'</div>'
        w=options(workers,'employee_id','name');rs=options(residents,'resident_id','fictional_name')
        operator=auth.has_role(user['employee_id'],['IAMOperator']);editor=auth.has_role(user['employee_id'],['Manager','IAMOperator'])
        if operator:
            content+=form('assign','Assign a resident',field('Worker','employee_id',w)+field('Resident','resident_id',rs))
            content+=form('unassign','Remove a resident assignment',field('Worker','employee_id',w)+field('Resident','resident_id',rs))
            content+=form('revoke','Revoke all local sessions for a worker',field('Worker','employee_id',w))
        if editor:
            content+=form('task','Create a remediation task',field('Worker','employee_id',w)+field('Title','title')+field('Priority','priority',''.join(f'<option>{p}</option>' for p in ['Low','Medium','High','Critical']))+field('Owner','owner_id',options(owners,'employee_id','name')))
            if tasks:content+=form('task_update','Update a remediation task',field('Task','task_id',options(tasks,'task_id','title'))+field('Status','status','<option>Open</option><option>In progress</option><option>Resolved</option>'))
            if pending:content+=form('close_review','Close a pending access review',field('Review','review_id',''.join(f'<option value="{r["review_id"]}">#{r["review_id"]} {ui.e(r["employee_id"])} {ui.e(r["decision"])}</option>' for r in pending)))
        for title,cols,rows in [
            ('Remediation register',['task_id','employee_id','title','priority','owner_id','status','evidence'],tasks),
            ('Unexpired local sessions',['employee_id','name','created_at','expires_at'],sessions),
            ('Active resident assignments',['employee_id','resident_id'],links)]:
            head=''.join('<th>'+ui.e(k.replace('_',' ').title())+'</th>' for k in cols)
            body=''.join('<tr>'+''.join('<td>'+ui.e(r[k])+'</td>' for k in cols)+'</tr>' for r in rows) or f'<tr><td colspan="{len(cols)}">No records yet.</td></tr>'
            content+=f'<section class="panel"><h3>{title}</h3><div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>'
        self.send_html(ui.layout('Security operations',content,user,active='operations'))

    def operations_save(self,query=None):
        user=self.require_roles(['Manager','IAMOperator'],'/operations')
        if not user:return
        try:governance.operate(self.form().get('action'),self.form(),user['employee_id'])
        except PermissionError as e:return self.error_page('Operation denied',str(e),403)
        except (ValueError,TypeError) as e:return self.error_page('Operation stopped',str(e),400)
        self.redirect('/requests' if self.form().get('action')=='execute' else '/operations')
