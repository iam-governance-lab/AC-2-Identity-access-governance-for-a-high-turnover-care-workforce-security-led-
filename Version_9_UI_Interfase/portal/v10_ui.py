"""Consistent server-rendered v10 workbench; every action rechecks authorisation."""
from urllib.parse import urlencode
import auth, database, enterprise, release_v10 as v10, ui, workforce_v8
from assurance_ui import field, panel, table

KINDS=('Access request','Site cover','Access package','Remediation','Certification','Emergency review')

def pager(path,query,page,total,size):
    buttons=''
    for label,target in [('Previous',page-1),('Next',page+1)]:
        if target<1 or (label=='Next' and page*size>=total):continue
        buttons+='<a class="btn btn-secondary" href="'+path+'?'+ui.e(urlencode({**query,'page':target}))+'">'+label+'</a>'
    return f'<nav class="pagination" aria-label="Result pages"><span>{total} results · page {page} · {size} per page</span><div class="buttons">{buttons}</div></nav>'

def action_form(action,fields,label):
    return '<form class="form-grid" method="post" action="/workbench/action"><input type="hidden" name="action" value="'+ui.e(action)+'">'+fields+'<div class="form-actions full"><button class="btn btn-primary">'+ui.e(label)+'</button></div></form>'

class V10Pages:
    def workbench(self,query=None):
        user=self.require_roles(['Manager','IAMOperator','Auditor'],'/workbench')
        if not user:return
        query=query or {};q=(query.get('q') or [''])[0][:100];kind=(query.get('kind') or [''])[0];overdue=(query.get('overdue') or [''])[0]=='1'
        try:page=int((query.get('page') or ['1'])[0])
        except ValueError:raise ValueError('Page must be a positive whole number.')
        if kind and kind not in KINDS:raise ValueError('Unknown work category.')
        with database.connect() as c:
            total,rows=v10.work_queue(c,q,kind,overdue,page)
            all_total,_=v10.work_queue(c,size=1);late,_=v10.work_queue(c,overdue=True,size=1)
            services=v10.service_health(c)
            owners=[(r[0],r[1]+' · '+r[0]) for r in c.execute("SELECT DISTINCT e.employee_id,e.name FROM employees e JOIN employee_roles r USING(employee_id) WHERE e.status='Active' AND r.role IN ('Manager','IAMOperator') ORDER BY e.name")]
        operator=auth.has_role(user['employee_id'],{'IAMOperator'});reviewer=auth.has_role(user['employee_id'],{'Manager','IAMOperator'})
        content=ui.page_header('REVIEW OPERATIONS','The right action, at the right time.','A prioritised queue of approvals, certification and remediation. Deadlines guide human review; overdue work never grants access automatically.')
        if query.get('saved'):content+=ui.alert('Action completed. Audit evidence recorded.','success')
        content+='<div class="stats-grid">'+ui.stat_card('Pending actions',all_total,'Across six workflows')+ui.stat_card('Overdue',late,'Review the oldest first','orange')+ui.stat_card('Service owner / expiry alerts',sum(bool(s['issues']) and s['status']=='Active' for s in services),'Local registry only','red')+'</div>'
        content+='<form class="panel form-grid" method="get" action="/workbench">'+field('Search worker or action','q',value=q,required=False)+field('Work category','kind',value=kind,options=[('','All categories')]+[(x,x) for x in KINDS])+field('Due date','overdue',value='1' if overdue else '',options=[('','All pending'),('1','Overdue only')])+'<button class="btn btn-primary">Apply filters</button></form>'
        items=[]
        for r in rows:
            action='<a class="btn btn-secondary btn-small" href="'+ui.e(r['href'])+'">Open workflow</a>'
            if reviewer and r['employee_id']!=user['employee_id']:
                decision=''
                if r['kind']=='Access request' and r['status']=='Pending':
                    decision=f'<form class="form-grid" method="post" action="/requests/{r["id"]}/decision">'+field('Decision','decision',options=[('Approved','Approve'),('Rejected','Reject')])+field('Decision evidence','decision_note')+'<button class="btn btn-primary">Record decision</button></form>'
                elif r['kind']=='Access request' and r['status']=='Approved' and operator:
                    decision=f'<form class="form-grid" method="post" action="/operations"><input type="hidden" name="action" value="execute"><input type="hidden" name="request_id" value="{r["id"]}"><button class="btn btn-primary">Execute approved change</button></form>'
                elif r['kind']=='Access package':
                    decision=f'<form class="form-grid" method="post" action="/console/catalog-decision"><input type="hidden" name="id" value="{r["id"]}">'+field('Decision','decision',options=[('Approved','Approve'),('Rejected','Reject')])+field('Decision evidence','reason')+'<button class="btn btn-primary">Record decision</button></form>'
                elif r['kind']=='Site cover':
                    decision=f'<form class="form-grid" method="post" action="/assurance-action/cover-decision"><input type="hidden" name="id" value="{r["id"]}">'+field('Decision','decision',options=[('Approve','Approve current stage'),('Reject','Reject')])+field('Decision evidence','reason')+'<button class="btn btn-primary">Record decision</button></form>'
                elif r['kind']=='Emergency review':
                    decision=f'<form class="form-grid" method="post" action="/assurance-action/emergency-review"><input type="hidden" name="id" value="{r["id"]}">'+field('Investigation evidence','reason')+'<button class="btn btn-primary">Close emergency review</button></form>'
                if decision:action+='<details><summary>Process this action</summary>'+decision+'</details>'
            if reviewer and r['kind']=='Remediation':
                action+=f'<details><summary>Update task</summary><form class="form-grid" method="post" action="/operations"><input type="hidden" name="action" value="task_update"><input type="hidden" name="task_id" value="{r["id"]}">'+field('Status','status',options=[(x,x) for x in ('Open','In progress','Resolved')])+field('Remediation evidence','reason')+'<button class="btn btn-primary">Update task</button></form></details>'
            if r['kind']=='Certification' and reviewer:
                action+='<details><summary>Decide this item</summary>'+action_form('review',f'<input type="hidden" name="id" value="{r["id"]}">'+field('Decision','decision',options=[('Retain','Retain'),('Remove','Remove')])+field('Decision evidence','reason'),'Record review')+'</details>'
            items.append([ui.e(r['kind'])+' #'+str(r['id']),ui.e(r['name'])+'<br>'+ui.e(r['employee_id']),ui.e(r['title']),ui.badge(r['status']),ui.e(r['due_at'])+'<br>'+ui.badge('Overdue' if r['overdue'] else 'Within target'),action])
        content+=panel('Prioritised actions',table(['Work','Worker','Context','Status','Due · UTC','Action'],items))
        from v11_ui import save_control
        content+=save_control('workbench',{'q':q,'kind':kind,'overdue':'1' if overdue else ''})
        content+=pager('/workbench',{'q':q,'kind':kind,'overdue':'1' if overdue else ''},page,total,25)
        content+=panel('Service identity ownership',table(['Identity','Owner','State','Health'],[[ui.e(s['name']),ui.e(s['owner_id']),ui.badge(s['status']),ui.e('; '.join(s['issues']) or 'No configured health issues')] for s in services]))
        if operator:
            content+='<div class="grid-2">'+panel('Reconcile a changed certification item', '<p>Use the item ID above if a role or site changed. This records the old and new snapshot and leaves the decision pending.</p>'+action_form('refresh',field('Certification item ID','id','number')+field('Reconciliation evidence','reason'),'Refresh pending snapshot'))
            if services:content+=panel('Replace a service identity owner', '<p>Assign an active manager or operator. Scopes, expiry and enabled state remain unchanged.</p>'+action_form('owner',field('Service identity','id',options=[(s['id'],s['name']) for s in services])+field('New owner','owner_id',options=owners)+field('Change evidence','reason'),'Reassign owner'))
            content+='</div>'
        self.send_html(ui.layout('Review workbench',content,user,active='workbench'))

    def workbench_action(self,query=None):
        user=self.require_login()
        if not user:return
        data=self.form();actor=user['employee_id'];action=data.get('action')
        if action=='owner':v10.reassign_owner(actor,data.get('id'),data.get('owner_id'),data.get('reason'))
        elif action=='refresh':v10.refresh_review(actor,data.get('id'),data.get('reason'))
        elif action=='review':workforce_v8.review(actor,data.get('id'),data.get('decision'),data.get('reason'))
        elif action=='cancel':
            v10.cancel_request(actor,data.get('id'),data.get('reason'))
            return self.redirect('/requests?saved=1')
        else:raise ValueError('Unknown workbench action.')
        self.redirect('/workbench?saved=1')
