import json
import ui,team_services
from assurance_ui import panel
def form(action,contents,button):
    return '<form method="post" action="'+ui.e(action)+'" class="form-grid">'+contents+'<div class="form-actions full"><button type="submit" class="btn btn-primary">'+ui.e(button)+'</button></div></form>'

class TeamPages:
    def team_page(self,query=None):
        user=self.require_login()
        if not user:return
        result=team_services.latest(user['employee_id'])
        content=ui.page_header('TEAM CAPABILITIES','Security services','Full teammate MFA detection, plus the preserved Entra review and automation lab.')
        content+=panel('MFA fatigue analysis','<p>Detect prompt bursts, repeated denials and denial followed by success. Findings support a human investigation; they never revoke access automatically.</p>'+form('/team-services/analyze','<input type="hidden" name="mode" value="demo">','Analyze synthetic demo')+form('/team-services/analyze','<input type="hidden" name="mode" value="csv"><div class="field full"><label for="mfa_csv">Normalized event CSV (60 KB maximum)</label><textarea class="service-input" id="mfa_csv" name="csv_text" required placeholder="event_id,employee_id,timestamp,event_type"></textarea></div><p class="full">Types: MFA_PROMPT, MFA_DENIED, MFA_SUCCESS. Use unique event IDs and ISO 8601 timestamps.</p>','Analyze CSV'))
        if result:content+=panel('Latest analysis','<a href="/team-services/result.json">Download findings JSON</a><pre class="service-output">'+ui.e(json.dumps(result,indent=2))+'</pre>')
        content+=panel('Entra access-review lab','<p>The full team lab includes Graph inventory, review campaigns, retain/change/remove/temporary-exception decisions, self-review prevention, approval-gated remediation, a job worker and evidence exports.</p><p>Start its separate interface with <code>python run.py lab</code> and its worker with <code>python run.py review-worker</code>. Follow <code>docs/OPERATING_GUIDE.md</code> to configure your own Entra tenant first. This service is not connected by default.</p>')
        content+=panel('Other included team capabilities','<p><a href="/integrations">SITAS simulation and SAIF agency validation</a> use the preserved original engines. Full PowerShell joiner/mover/leaver, Microsoft Graph and B2B scripts are included in the source package.</p>')
        self.send_html(ui.layout('Team services',content,user,active='team-services'))
    def team_analyze(self,query=None):
        user=self.require_login()
        if not user:return
        data=self.form();team_services.analyze(user['employee_id'],data.get('mode','demo'),data.get('csv_text',''))
        self.redirect('/team-services')
    def team_export(self,query=None):
        user=self.require_login()
        if not user:return
        self.send_json(team_services.latest(user['employee_id']) or {'message':'No analysis has been run.'})
