"""Reviewed roster import and quarterly certification pages."""
import json,sqlite3
import auth,database,enterprise,ui,workforce_v8,audit
from enterprise_ui import form,field,hidden,panel,table

class WorkforcePages:
    def workforce_page(self,page,query=None):
        user=self.require_roles(['Manager','Auditor','IAMOperator'],'/'+page)
        if not user:return
        actor=user['employee_id'];operator=auth.has_role(actor,['IAMOperator']);reviewer=auth.has_role(actor,['Manager','IAMOperator'])
        data=workforce_v8.summary()
        if page=='workforce-sync':
            content=ui.page_header('WORKFORCE / V9','Reviewed roster reconciliation','Validate fictional staff changes, receive independent approval and apply a still-current preview. No cloud writes.')
            if reviewer:
                with database.connect() as c:
                    rs=c.execute("SELECT employee_id,email,approved_role,facility,status,end_date FROM employees WHERE employee_id IN ('SC1001','SC1006') ORDER BY employee_id").fetchall()
                example='employee_id,email,role,facility,status,end_date\n'+'\n'.join(','.join(str(v or '') for v in r) for r in rs)
                content+=panel('Stage a CSV preview',form('/workforce-action',hidden('action','stage')+f'<div class="field"><label for="rosterCsv">Fictional roster CSV (up to 100 workers)</label><textarea id="rosterCsv" name="csv" rows="7" maxlength="32000" required>{ui.e(example)}</textarea></div>','Check & stage import'))
            rows=[]
            for r in data['imports']:
                changes=json.loads(r['changes']);actions=', '.join(x['employee_id']+': '+x['action']+((' ('+str(x['from'])+' → '+str(x['to'])+')') if 'from' in x else '') for x in changes) or 'No changes'
                control=''
                if reviewer and r['status']=='Pending' and actor!=r['submitted_by']:
                    control=form('/workforce-action',hidden('action','decide')+hidden('id',r['id'])+field('decision','Decision',options=['Approved','Rejected'])+field('reason','Approval evidence','textarea'),'Record decision')
                if operator and r['status']=='Approved' and actor!=r['approved_by']:
                    control=form('/workforce-action',hidden('action','apply')+hidden('id',r['id']),'Apply checked changes')
                rows.append([ui.e(r['id']),ui.e(r['submitted_by']),ui.e(r['approved_by'] or '—'),ui.badge(r['status']),ui.e(actions),control])
            content+=panel('Review queue',table(['ID','Submitted','Approved by','State','Preview actions','Decision / apply'],rows))
            content+=ui.alert('Unmatched workers, role/facility changes and reactivation conflicts create findings only. Approved leavers are disabled locally; agency end dates are updated after a fresh snapshot check.')
        else:
            content=ui.page_header('GOVERNANCE / V9','Quarterly access certification','Capture a snapshot of active workers and review who still needs access. Removal decisions revoke local access packages and open a core-role remediation task.')
            if operator:content+=panel('Start the current quarter',form('/workforce-action',hidden('action','campaign'),'Create or open this quarter’s review'))
            rows=[]
            for r in data['campaigns']:
                count=r['pending_count']
                rows.append([ui.e(r['period']),ui.e(r['created_at']),ui.e(r['due_at']),ui.e(count)])
            content+=panel('Campaign history',table(['Quarter','Created UTC','Due UTC','Pending (full campaign)'],rows))
            items=[]
            for r in data['items']:
                control=''
                if reviewer and r['decision']=='Pending' and r['employee_id']!=actor:
                    control=form('/workforce-action',hidden('action','review')+hidden('id',r['id'])+field('decision','Decision',options=['Retain','Remove'])+field('reason','Review evidence','textarea'),'Record review')
                items.append([ui.e(r['campaign_id']),ui.e(r['employee_id']),ui.e(r['role_at_start']),ui.badge(r['decision']),ui.e(r['reviewer_id'] or '—'),control])
            content+=panel('Latest 100 worker decisions',table(['Campaign','Worker','Role at snapshot','Decision','Reviewer','Action'],items))
            content+=ui.alert('A Remove decision revokes temporary packages and opens a task; an operator must separately complete any core-role removal using approved lifecycle controls.')
        self.send_html(ui.layout('Roster & certification',content,user,active=page))

    def workforce_save(self,query=None):
        user=self.require_login()
        if not user:return
        d=self.form();actor=user['employee_id'];action=d.get('action')
        try:
            if action=='stage':workforce_v8.stage(actor,d.get('csv'));target='/workforce-sync'
            elif action=='decide':workforce_v8.decide(actor,d.get('id'),d.get('decision'),d.get('reason'));target='/workforce-sync'
            elif action=='apply':workforce_v8.apply(actor,d.get('id'));target='/workforce-sync'
            elif action=='campaign':workforce_v8.create_campaign(actor);target='/campaigns'
            elif action=='review':workforce_v8.review(actor,d.get('id'),d.get('decision'),d.get('reason'));target='/campaigns'
            else:return self.not_found()
        except PermissionError as exc:
            audit.record(actor,None,'WORKFORCE_ACTION_DENIED','DENIED',{'action':action})
            return self.error_page('Action denied',str(exc),403)
        except (ValueError,sqlite3.IntegrityError) as exc:return self.error_page('Review required',str(exc),409)
        self.redirect(target)
