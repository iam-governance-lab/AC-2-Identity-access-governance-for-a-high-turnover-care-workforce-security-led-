from html import escape
from urllib.parse import quote
import config
import auth
import database


def e(value):
    return escape("" if value is None else str(value), quote=True)


def badge(text, tone="neutral"):
    # A status has the same visual meaning on every screen.
    value=str(text).lower()
    if value in {'active','current','approved','retained','retain','pass','succeeded','closed','implemented','within target'}:tone='green'
    elif value in {'expired','leaver','rejected','revoked','fail','critical','overdue','blocked'}:tone='red'
    elif value.startswith('pending') or value in {'high','suspended','due soon','in progress'}:tone='orange'
    elif value in {'cancelled','inactive'}:tone='neutral'
    return f'<span class="badge badge-{tone}">{e(text)}</span>'


def alert(text, tone="info"):
    return f'<div class="alert alert-{tone}"><strong>{e(text)}</strong></div>'


def layout(title, content, user=None, active="", flashes=None, extra_head="", extra_js=""):
    nav = ""
    roles=set()
    if user:
        items = [
            ("dashboard","/","Dashboard","◫"),
            ("application-access","/application-access","Application access","▦"),
            ("shifts","/shifts","Shifts","◷"),
            ("sponsors","/sponsors","Sponsor intake","◎"),
            ("connectors","/connectors","Connector operations","⇄"),
            ("team-services","/team-services","Team services","◇"),
            ("ai-workspace","/ai-workspace","AI workspace","✦"),
            ("help","/help","Help centre","?"),
            ("workbench","/workbench","Review workbench","▤"),
            ("saved-views","/saved-views","Saved views","☆"),
            ("hub","/hub","Unified governance","✦"),
            ("qualifications","/qualifications","Qualifications","◈"),
            ("coverage","/coverage","Cover & emergencies","⊕"),
            ("insights","/insights","Risk insights","◆"),
            ("control-centre","/control-centre","Control centre","⚙"),
            ("catalog","/catalog","Access catalogue","▦"),
            ("workforce-sync","/workforce-sync","Roster sync","⇄"),
            ("campaigns","/campaigns","Quarterly reviews","✓"),
            ("employees","/employees","Employees","◎"),
            ("residents","/residents","Residents","⌂"),
            ("reviews","/access-reviews","Access Reviews","✓"),
            ("compliance","/compliance","Compliance","◆"),
            ("audit","/audit","Audit Log","≡"),
            ("requests","/requests","Access requests","↗"),
            ("operations","/operations","Security operations","◈"),
            ("onboarding","/onboarding","Onboarding","⊕"),
            ("assurance","/security-assurance","Security assurance","◇"),
            ("automation","/automation","Automation","⟳"),
            ("policies","/policies","Policies & risks","▣"),
            ("notifications","/notifications","Notifications","◉"),
            ("reports","/reports","Reports","▥"),
            ("notes","/notes","Notes & handovers","✎"),
            ("requirements","/requirements","Readiness","☑"),
            ("guide","/guide","Help & guide","?"),
        ]
        nav = '<aside class="sidebar" id="workspace-navigation"><button class="nav-close btn btn-ghost" type="button" aria-label="Close navigation">Close menu</button><div class="brand"><div class="brand-mark">S</div><div><b>Sunhaven Care</b><small>Identity & Access</small></div></div><nav>'
        with database.connect() as c:
            roles={r[0] for r in c.execute('SELECT role FROM employee_roles WHERE employee_id=?',(user['employee_id'],))}
        governor = bool(roles & {'Manager','Auditor','IAMOperator'})
        if not governor:
            items = [item for item in items if item[0] in ('ai-workspace','catalog','dashboard','residents','requests','notifications','guide','coverage','help','shifts','application-access')]
        if 'SiteDelegate' in roles and not governor:
            items += [('qualifications','/qualifications','Qualifications','◈'),('insights','/insights','Risk insights','◆')]
        for key, href, label, icon in items:
            cls = "nav-link active" if active == key else "nav-link"
            nav += f'<a class="{cls}" href="{href}"><span class="nav-icon">{icon}</span>{e(label)}</a>'
        nav += f'</nav><div class="sidebar-foot"><div class="environment-dot"></div><strong>{"DEMO WORKSPACE" if config.AUTH_MODE == "local" else "ENTRA SIGN-IN"}</strong><small>Synthetic data · Mock directory</small><span class="version">Sunhaven / v9 Final</span></div></aside>' 

    flash_html = "".join(alert(msg, tone) for tone, msg in (flashes or []))
    user_block = ""
    if user:
        user_block = f'''<div class="user-chip"><div class="avatar">{e(user['name'][:1])}</div><div><strong>{e(user['name'])}</strong><span>{e(user['approved_role'])}</span></div></div>
        <form method="post" action="/logout" class="signout-form"><button class="btn btn-ghost btn-small" type="submit">Sign out</button></form>'''
    workspace_search = '<form action="/search" method="get" class="global-search"><span aria-hidden="true">⌕</span><input name="q" aria-label="Global search" placeholder="Search workspace…" minlength="2" maxlength="100"><kbd>/</kbd></form>' if user else ''
    theme_control = '<button id="themeToggle" class="btn btn-ghost theme-toggle" type="button" aria-label="Switch to dark mode" title="Switch theme">◐</button>'
    from help_assistant import topic_for_path
    topic=topic_for_path('/'+active,roles)
    page_help='<a class="btn btn-ghost" href="/help?topic='+e(topic)+'">Help on this page</a>' if user else ''
    assistant = ('''<button id="assistantLauncher" class="btn btn-primary assistant-launcher" type="button" aria-haspopup="dialog">Ask Sunhaven</button>
<dialog id="assistantDialog" aria-labelledby="assistantTitle" data-context="'''+e(topic)+'''">
<div class="assistant-head"><div><h2 id="assistantTitle">Sunhaven assistant</h2><small>AI when configured · Read-only tools · No access changes</small></div><form method="dialog"><button class="btn btn-ghost">Close</button></form></div>
<p>Ask where to find a feature or how to complete a task. Answers use local help and role-filtered summaries. With an API key, AI can explain them in conversation. Your question may be sent to the configured AI provider. Do not enter personal or resident information.</p>
<div id="assistantMessages" role="log" aria-live="polite" aria-relevant="additions"></div><div id="assistantSuggestions" class="buttons"><button type="button" class="btn btn-secondary" data-question="Help on this page">Explain this page</button><button type="button" class="btn btn-secondary" data-question="How do I request app access?">Request access</button></div>
<form id="assistantForm" method="post" action="/assistant/ask"><label for="assistantQuestion">What would you like to do?</label><div class="assistant-compose"><input id="assistantQuestion" name="question" maxlength="1000" required autocomplete="off" placeholder="For example: how do I onboard an agency worker?"><button class="btn btn-primary" type="submit">Ask</button></div></form>
<p id="assistantStatus" role="status"></p><button id="assistantClear" class="btn btn-ghost" type="button">Clear conversation</button><a href="/help">Browse all help</a></dialog>''') if user else ''
    shell_class = "app-shell" if user else "public-shell"
    main_class = "main" if user else "public-main"

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | {e(config.APP_NAME)}</title><link rel="stylesheet" href="/static/app.bundle.css"><script src="/static/theme.js"></script>{extra_head}</head>
<body class="{shell_class}"><a class="skip-link" href="#main-content">Skip to content</a>{nav}<button class="nav-backdrop" aria-label="Close navigation" hidden></button><main class="{main_class}">
<header class="topbar"><button class="menu-toggle btn btn-ghost" type="button" aria-label="Toggle navigation" aria-controls="workspace-navigation" aria-expanded="false">☰</button><div><h1>{e(title)}</h1><p>Workforce identity & access governance</p></div>{workspace_search}<div class="topbar-actions">{page_help}{theme_control}<button class="btn btn-ghost" id="quickNav" type="button">Go to…</button><a class="icon-link" href="/notifications" title="Notifications" aria-label="Notifications">◉</a>{user_block}</div></header>
<div class="page-body" id="main-content">{flash_html}{content}<footer class="page-footer"><span>Sunhaven Care · Workforce access portal</span><span>Synthetic data only · All times UTC</span></footer></div></main>
<dialog id="navDialog" aria-labelledby="navTitle"><h2 id="navTitle">Quick navigation</h2><form method="dialog"><button class="btn btn-ghost">Close</button></form><label for="navQuery">Find a workspace</label><input id="navQuery" type="search" autocomplete="off"><div id="navResults"></div><p id="navStatus" role="status"></p></dialog><div id="connectionStatus" role="status" hidden>You are offline. Reconnect before submitting changes.</div><script src="/static/app.js"></script><script src="/static/v11.js"></script>{assistant}<script src="/static/v12.js"></script>{extra_js}</body></html>'''


def page_header(kicker, title, text, actions=""):
    return f'''<section class="hero"><div><span class="eyebrow">{e(kicker)}</span><h2>{e(title)}</h2><p>{e(text)}</p></div><div class="hero-actions">{actions}</div></section>'''


def stat_card(label, value, meta, tone="blue", href=None):
    card = f'''<div class="stat-card tone-{tone}"><div class="stat-label">{e(label)}</div><div class="stat-value">{e(value)}</div><div class="stat-meta">{e(meta)}</div></div>'''
    return f'<a href="{e(href)}" aria-label="{e(label)}: {e(value)} — view details">{card}</a>' if href else card


def role_options(selected=""):
    return "".join(f'<option value="{e(r)}" {"selected" if r==selected else ""}>{e(r)}</option>' for r in config.ALLOWED_ROLES)


def facility_options(selected=""):
    return "".join(f'<option value="{e(r)}" {"selected" if r==selected else ""}>{e(r)}</option>' for r in config.FACILITIES)


def worker_type_options(selected=""):
    return "".join(f'<option value="{e(r)}" {"selected" if r==selected else ""}>{e(r)}</option>' for r in config.WORKER_TYPES)
