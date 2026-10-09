import os,json
import ai_insights,ui
from assurance_ui import panel,table
class AIPages:
    def ai_page(self,query=None):
        user=self.require_login()
        if not user:return
        actor=user['employee_id'];roles=ai_insights.current_roles(actor)
        mine=ai_insights.access_explanations(actor)
        content=ui.page_header('EXPLAINABLE INTELLIGENCE','Understand access. Review evidence.','Read-only explanations from current local policy and workflow data. Human approval remains mandatory.')
        mode='Optional AI provider configured; live connection still requires valid credentials and network.' if os.getenv('SUNHAVEN_AI_API_KEY','').strip() else 'Local guidance active. No external model key configured.'
        content+=ui.alert(mode)
        content+=panel('Why your application access is allowed or blocked',table(['Application / permission','Available now','Reason'],[[ui.e(x['application']+' / '+x['name']),ui.badge('Allowed' if x['allowed'] else 'Blocked'),ui.e(x['reason'])] for x in mine['permissions']]))
        if roles&ai_insights.GOV:
            brief=ai_insights.governance_briefing(actor)
            content+='<div class="stats-grid">'+''.join(ui.stat_card(k.replace('_',' ').title(),v,'Active-worker qualification records') for k,v in brief['qualification_outlook'].items())+'</div>'
            content+=panel('Investigation priorities',table(['Count','Evidence signal','Human next step'],[[str(x['count']),ui.e(x['signal']),ui.e(x['next_step'])+' <a href="'+ui.e(x['path'])+'">Open workspace</a>'] for x in brief['priorities']])+'<p>'+ui.e(brief['decision_rule'])+'</p>')
            content+=panel('Governance briefing','<p>Risk bands: '+ui.e(json.dumps(brief['risk_bands']))+'</p><p>Aggregate output excludes worker names, IDs, contacts and resident details.</p><a class="btn btn-secondary" href="/ai-briefing.json">Download aggregate JSON briefing</a>')
        content+=panel('Ask Sunhaven','<p>Try: Explain my access; What qualifications expire soon?; Give me review priorities; How do I onboard an agency worker?</p><a href="/help">Open Help centre</a>')
        self.send_html(ui.layout('AI workspace',content,user,active='ai-workspace'))
    def ai_export(self,query=None):
        user=self.require_login()
        if not user:return
        self.send_json(ai_insights.governance_briefing(user['employee_id']))
