"""Operator workflow for reviewed mock-directory expiry enforcement."""
import automation,auth,ui,policy_catalog

class AutomationPages:
    def automation_page(self,query=None):
        user=self.require_roles(['Manager','Auditor','IAMOperator'],'/automation')
        if not user:return
        plan=automation.preview()
        content=ui.page_header('AUTOMATION / REVIEW','Agency contract expiry',
          'Preview expired contracts, then run one atomic local access shutdown as an IAM operator. The directory remains simulated.')
        content+='<div class="stats-grid">'+ui.stat_card('Expired active contracts',len(plan['expired']),'Require immediate access removal','red')+ui.stat_card('Due within 14 days',len(plan['upcoming']),'Sponsor follow-up','orange')+'</div>'
        for title,entries in [('Expired contracts awaiting action',plan['expired']),('Contracts due soon',plan['upcoming'])]:
            body=''.join(f'<tr><td><a href="/employees/{ui.e(r["employee_id"])}">{ui.e(r["name"])}</a></td><td>{ui.e(r["employee_id"])}</td><td>{ui.e(r["facility"])}</td><td>{ui.e(r["end_date"])}</td></tr>' for r in entries) or '<tr><td colspan="4">No matching contracts.</td></tr>'
            content+=f'<section class="panel"><h3>{ui.e(title)}</h3><div class="table-wrap"><table><thead><tr><th>Worker</th><th>ID</th><th>Facility</th><th>End date</th></tr></thead><tbody>{body}</tbody></table></div></section>'
        if auth.has_role(user['employee_id'],['IAMOperator']):
            content+=f'''<section class="panel"><span class="eyebrow">REVIEWED RUN</span><h3>Enforce local expiry</h3><p>For each listed expired worker: suspend the identity, disable simulated directory access, remove roles and assignments, revoke sessions, block portal access and create audit evidence. The displayed list is checked again when you submit.</p>
<form method="post" action="/automation"><input type="hidden" name="fingerprint" value="{ui.e(plan['fingerprint'])}"><div class="field"><label for="expiryReason">Operator reason</label><textarea id="expiryReason" name="reason" minlength="10" maxlength="2000" required rows="3" placeholder="Explain the scheduled expiry run…"></textarea></div><div class="form-actions"><button class="btn btn-danger" type="submit">Enforce expired contracts</button></div></form></section>'''
        history=''.join(f'<tr><td>{ui.e(r["run_at"])}</td><td>{ui.e(r["actor_id"])}</td><td>{ui.e(r["target_count"])}</td><td>{ui.e(r["target_ids"])}</td><td>{ui.e(r["reason"])}</td></tr>' for r in plan['history']) or '<tr><td colspan="5">No runs recorded.</td></tr>'
        content+=f'<section class="panel"><h3>Run history</h3><div class="table-wrap"><table><thead><tr><th>UTC time</th><th>Operator</th><th>Workers disabled</th><th>IDs</th><th>Reason</th></tr></thead><tbody>{history}</tbody></table></div></section>'
        self.send_html(ui.layout('Automation',content,user,active='automation'))

    def automation_execute(self,query=None):
        user=self.require_roles(['IAMOperator'],'/automation')
        if not user:return
        data=self.form()
        try:automation.execute(user['employee_id'],data.get('fingerprint'),data.get('reason'))
        except PermissionError as exc:return self.error_page('Run denied',str(exc),403)
        except (ValueError,RuntimeError) as exc:return self.error_page('Run stopped',str(exc),409)
        self.redirect('/automation')

    def policy_page(self,query=None):
        user=self.require_roles(['Manager','Auditor','IAMOperator'],'/policies')
        if not user:return
        content=ui.page_header('GOVERNANCE / VERSION '+policy_catalog.POLICY_VERSION,'Policy and risk catalogue',
          'A mapped lab control baseline: each policy identifies an owner, related software evidence and a regression test.')
        rows=''.join('<tr>'+''.join(f'<td>{ui.e(x)}</td>' for x in row)+'</tr>' for row in policy_catalog.CONTROLS)
        content+=f'<section class="panel"><h3>Controls</h3><div class="table-wrap"><table><thead><tr><th>ID</th><th>Control</th><th>Required behaviour</th><th>Owner</th><th>Evidence</th><th>Test</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
        risks=''.join('<tr>'+''.join(f'<td>{ui.e(x)}</td>' for x in row)+'</tr>' for row in policy_catalog.RISKS)
        content+=f'<section class="panel"><h3>Risk and control traceability</h3><div class="table-wrap"><table><thead><tr><th>ID</th><th>Risk</th><th>Severity</th><th>Policies</th><th>Local mitigation</th><th>Residual limit</th></tr></thead><tbody>{risks}</tbody></table></div></section>'
        self.send_html(ui.layout('Policies',content,user,active='policies'))
