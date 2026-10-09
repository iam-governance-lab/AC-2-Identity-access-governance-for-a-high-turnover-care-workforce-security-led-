from urllib.parse import urlencode
import auth,database,ui,release_v11 as v11
from assurance_ui import field,panel,table
from v10_ui import pager

class V11Pages:
    def notifications_page(self,query=None):
        user=self.require_login()
        if not user:return
        query=query or {};q=(query.get('q') or [''])[0][:100];category=(query.get('category') or [''])[0];state=(query.get('state') or ['all'])[0];page=int((query.get('page') or ['1'])[0])
        with database.connect() as c:stats,items=v11.inbox(c,user['employee_id'],q,category,state,page)
        content=ui.page_header('YOUR INBOX','A clearer view of what needs attention',f'{stats["unread"]} unread reminders across {stats["total"]} matching items. Marking read does not resolve the underlying issue.')
        content+='<form class="panel form-grid" method="get" action="/notifications">'+field('Search all reminders','q',value=q,required=False)+field('Read state','state',value=state,options=[('all','All reminders'),('unread','Unread only'),('read','Read only')])+field('Category','category',value=category,options=[('','All categories')]+[(x,x) for x in ('Requests','Contracts','Reviews','System')])+'<button class="btn btn-primary">Filter inbox</button></form>'
        unread=[a['key'] for a in items if not a['read']]
        if unread:content+='<form method="post" action="/notifications/bulk-read" class="bulk-toolbar"><input type="hidden" name="keys" value="'+ui.e('|'.join(unread))+'"><button class="btn btn-secondary">Mark '+str(len(unread))+' displayed reminders read</button><span class="muted">Only this page is affected.</span></form>'
        cards=''
        for a in items:
            action=ui.badge('Read') if a['read'] else f'<form method="post" action="/notifications/read"><input type="hidden" name="key" value="{ui.e(a["key"])}"><button class="btn btn-small btn-secondary">Mark read</button></form>'
            cards+=f'<article class="panel notification-card {"is-read" if a["read"] else ""}"><span class="notification-dot badge-{a["tone"]}"></span><div><span class="eyebrow">{ui.e(a["title"])}</span><h3><a href="{ui.e(a["href"])}">{ui.e(a["text"])}</a></h3><small>{ui.e(a["category"])} · Current reminder</small></div>{action}</article>'
        content+=cards or '<section class="empty-state"><h3>No matching reminders</h3><p>Try another category or read-state filter.</p></section>'
        content+=pager('/notifications',{'q':q,'category':category,'state':state},page,stats['total'],25)
        self.send_html(ui.layout('Notifications',content,user,active='notifications'))

    def notification_read(self,query=None):
        user=self.require_login()
        if not user:return
        try:v11.mark_read(user['employee_id'],[self.form().get('key','')])
        except LookupError as exc:return self.error_page('Reminder unavailable',str(exc),404,user)
        self.redirect('/notifications')

    def notification_bulk(self,query=None):
        user=self.require_login()
        if not user:return
        try:v11.mark_read(user['employee_id'],self.form().get('keys','').split('|'))
        except LookupError as exc:return self.error_page('Reminder unavailable',str(exc),404,user)
        self.redirect('/notifications?saved=1')

    def saved_views(self,query=None):
        user=self.require_roles(['Manager','IAMOperator','Auditor'],'/saved-views')
        if not user:return
        with database.connect() as c:rows=c.execute('SELECT * FROM saved_views WHERE employee_id=? ORDER BY name',(user['employee_id'],)).fetchall()
        content=ui.page_header('PERSONAL WORKSPACE','Saved views','Return to the filters you use most. Views are private to your account; opening one always rechecks current access.')
        content+=panel('Your views',table(['Name','Workspace','Actions'],[[ui.e(r['name']),ui.e(r['module']),'<a class="btn btn-secondary" href="'+ui.e(v11.view_url(r))+'">Open view</a><form method="post" action="/saved-views/delete"><input type="hidden" name="id" value="'+str(r['id'])+'"><button class="btn btn-ghost">Delete view</button></form>'] for r in rows]))
        content+='<p>Apply filters in <a href="/employees">Employees</a>, <a href="/notes">Notes</a> or <a href="/workbench">Review workbench</a>, then use Save current view. Up to 20 views per account.</p>'
        self.send_html(ui.layout('Saved views',content,user,active='saved-views'))

    def saved_view_action(self,action,query=None):
        user=self.require_login()
        if not user:return
        data=self.form()
        if action=='save':v11.save_view(user['employee_id'],data.get('name'),data.get('module'),data)
        elif action=='delete':v11.remove_view(user['employee_id'],data.get('id'))
        else:raise ValueError('Unknown saved-view action.')
        self.redirect('/saved-views?saved=1')

def save_control(module,filters):
    fields=''.join('<input type="hidden" name="'+ui.e(k)+'" value="'+ui.e(v)+'">' for k,v in {'module':module,**filters}.items())
    return '<details class="save-view"><summary>Save current view</summary><form class="form-grid" method="post" action="/saved-views/save">'+fields+field('View name','name',required=True)+'<button class="btn btn-secondary">Save to my workspace</button></form></details>'
