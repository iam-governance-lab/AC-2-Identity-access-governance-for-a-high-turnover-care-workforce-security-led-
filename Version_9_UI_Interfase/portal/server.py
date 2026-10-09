from clock import utc_today
from datetime import timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
from pathlib import Path
from datetime import datetime, date
import json
import mimetypes
import re
import secrets
import sqlite3
import traceback

import config
import database
import auth
import audit
import lifecycle
import compliance
import ui
import security
from features import Features
from operations_ui import Operations
from experience import Experience, chart_panel
from security_workstream import ledger, threats
from automation_ui import AutomationPages
from enterprise_ui import EnterprisePages
from workforce_v8_ui import WorkforcePages
from assurance_ui import AssurancePages
from v10_ui import V10Pages, pager
from v11_ui import V11Pages, save_control
from v12_ui import V12Pages
from ai_ui import AIPages
from team_ui import TeamPages
from assets import cached_asset, accepts_gzip
import assurance

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class AppHandler(TeamPages, AIPages, V12Pages, V11Pages, V10Pages, AssurancePages, WorkforcePages, EnterprisePages, AutomationPages, Experience, Operations, Features, BaseHTTPRequestHandler):
    server_version = "SunhavenIAM/9.0-final"

    def log_message(self, fmt, *args):
        print(json.dumps({"time":self.log_date_time_string(),"method":getattr(self,"command",""),"path":urlparse(getattr(self,"path","")).path[:200],"status":str(args[1]) if len(args)>1 else "-","request_id":getattr(self,"request_id","")}))

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method):
        try:
            self.request_id=secrets.token_hex(12)
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            query = parse_qs(parsed.query)

            if path=='/login' and method=='POST' or path.startswith('/api/') or path=='/assistant/ask':
                if not security.rate_allowed(self.client_address[0], 'login' if path=='/login' else 'assistant' if path=='/assistant/ask' else 'api'):
                    return self.send_json({'error':{'code':'rate_limited','message':'Too many requests. Retry after 60 seconds.'},'request_id':self.request_id},429)
            if method == 'POST':
                try:
                    data = self.form()
                except ValueError:
                    return self.error_page("Invalid request", "Form is invalid or exceeds 64 KB.", 400)
                if not security.validate(self, data.get('_csrf', '')):
                    return self.error_page("Request expired", "Reload the page and try again.", 403)
            if path.startswith("/static/"):
                return self.serve_static(path)
            if path == "/health":
                with database.connect() as conn:
                    conn.execute("SELECT 1 FROM employees LIMIT 1")
                return self.send_json({"status":"ok","version":config.RELEASE_VERSION})

            routes = [
                ("GET", r"^/team-services$", self.team_page),
                ("POST", r"^/team-services/analyze$", self.team_analyze),
                ("GET", r"^/team-services/result.json$", self.team_export),
                ("GET", r"^/ai-workspace$", self.ai_page),
                ("GET", r"^/ai-briefing.json$", self.ai_export),
                ("GET", r"^/(application-access|shifts|sponsors|connectors)$", self.v12_page),
                ("POST", r"^/v12-action/([a-z-]+)$", self.v12_action),
                ("GET", r"^/help$", self.help_page),
                ("POST", r"^/assistant/ask$", self.assistant_ask),
                ("GET", r"^/integration-export/(ndjson|fhir)$", self.integration_export),
                ("GET", r"^/saved-views$", self.saved_views),
                ("POST", r"^/saved-views/(save|delete)$", self.saved_view_action),
                ("POST", r"^/notifications/bulk-read$", self.notification_bulk),
                ("GET", r"^/workbench$", self.workbench),
                ("POST", r"^/workbench/action$", self.workbench_action),
                ("GET", r"^/(qualifications|coverage|insights|control-centre)$", self.assurance_page),
                ("POST", r"^/assurance-action/([a-z-]+)$", self.assurance_save),
                ("GET", r"^/api/v1/(.+)$", self.assurance_api),
                ("GET", r"^/(workforce-sync|campaigns)$", self.workforce_page),
                ("POST", r"^/workforce-action$", self.workforce_save),
                ("GET", r"^/(hub|catalog|services|incidents|policy-lab|integrations)$", self.enterprise_page),
                ("POST", r"^/console/([a-z-]+)$", self.enterprise_save),
                ("GET", r"^/catalog/resource/([a-z-]+)$", self.package_resource),
                ("GET", r"^/security-assurance$", self.security_assurance),
                ("GET", r"^/automation$", self.automation_page),
                ("POST", r"^/automation$", self.automation_execute),
                ("GET", r"^/policies$", self.policy_page),
                ("GET", r"^/notifications$", self.notifications_page),
                ("POST", r"^/notifications/read$", self.notification_read),
                ("GET", r"^/search$", self.search_page),
                ("GET", r"^/requests/(\d+)$", self.request_history),
                ("GET", r"^/onboarding$", self.onboarding_page),
                ("POST", r"^/onboarding$", self.onboarding_save),
                ("GET", r"^/reports$", self.reports_page),
                ("GET", r"^/operations$", self.operations_page),
                ("POST", r"^/operations$", self.operations_save),
                ("GET", r"^/notes$", self.notes_page),
                ("POST", r"^/notes$", self.note_save),
                ("GET", r"^/requests$", self.requests_page),
                ("POST", r"^/requests$", self.request_save),
                ("POST", r"^/requests/(\d+)/decision$", self.request_decide),
                ("GET", r"^/exports/(employees|audit|reviews)$", self.export_csv),
                ("GET", r"^/guide$", self.guide_page),
                ("GET", r"^/$", self.dashboard),
                ("GET", r"^/login$", self.login_page),
                ("POST", r"^/login$", self.login_local),
                ("GET", r"^/login/entra$", self.login_entra),
                ("GET", r"^/auth/callback$", self.entra_callback),
                ("POST", r"^/logout$", self.logout),
                ("GET", r"^/employees$", self.employees),
                ("GET", r"^/employees/new$", self.employee_new),
                ("POST", r"^/employees/joiner$", self.employee_joiner),
                ("GET", r"^/employees/([^/]+)/move$", self.employee_move_page),
                ("POST", r"^/employees/([^/]+)/move$", self.employee_move),
                ("POST", r"^/employees/([^/]+)/leave$", self.employee_leave),
                ("GET", r"^/employees/([^/]+)$", self.employee_detail),
                ("GET", r"^/residents$", self.residents),
                ("GET", r"^/protected/care-notes$", self.care_notes),
                ("GET", r"^/protected/clinical$", self.clinical),
                ("GET", r"^/protected/review$", self.review_page),
                ("GET", r"^/protected/iam-admin$", self.iam_admin),
                ("GET", r"^/access-reviews$", self.access_reviews),
                ("POST", r"^/access-reviews$", self.access_review_save),
                ("GET", r"^/audit$", self.audit_log),
                ("GET", r"^/compliance$", self.compliance_page),
                ("POST", r"^/compliance/run$", self.compliance_run),
                ("GET", r"^/requirements$", self.requirements_page),
            ]
            for m, pattern, fn in routes:
                match = re.match(pattern, path)
                if m == method and match:
                    return fn(*match.groups(), query=query)
            return self.not_found()
        except ledger.IntegrityError:
            return self.error_page("Audit integrity requires attention", "No further protected changes can be made. Preserve the database, ledger key, checkpoint and pending journal; ask the operator to investigate or restore a verified backup.", 503)
        except sqlite3.OperationalError as exc:
            if 'locked' in str(exc).lower() or 'busy' in str(exc).lower():
                return self.error_page('Database is busy','Wait a few seconds, reload and check whether the change was saved before retrying.',503)
            traceback.print_exc()
            return self.error_page('Storage unavailable','Contact your administrator with the request identifier. Do not reset the database.',503)
        except sqlite3.IntegrityError:
            return self.error_page("Conflicting record", "This record conflicts with existing data. Reload and check identifiers and email addresses.", 409)
        except PermissionError as exc:
            return self.error_page("Access denied", str(exc), 403)
        except (ValueError, UnicodeError) as exc:
            return self.error_page("Check the request", str(exc), 400)
        except Exception as exc:
            traceback.print_exc()
            return self.error_page("Unexpected error", "The request could not be completed. Contact your administrator.", 500)

    # ---------- Core HTTP helpers ----------
    def form(self):
        if hasattr(self, '_form_data'):
            return dict(self._form_data)
        length = int(self.headers.get("Content-Length", 0))
        if length < 0 or length > 65536:
            raise ValueError("Body too large")
        if self.headers.get("Content-Type", "application/x-www-form-urlencoded").split(";")[0].strip() != "application/x-www-form-urlencoded":raise ValueError("Unsupported form format")
        body = self.rfile.read(length).decode("utf-8")
        data = parse_qs(body, keep_blank_values=True, max_num_fields=100)
        if any(len(v)!=1 for v in data.values()):raise ValueError("Repeated form fields are not allowed")
        self._form_data = {k: v[-1] if isinstance(v, list) else v for k, v in data.items()}
        return dict(self._form_data)

    def send_html(self, html, status=200, headers=None):
        token = security.token(self)
        html = re.sub(r'(<form\b[^>]*method=["\']post["\'][^>]*>)',
                      lambda m: m.group(1) + '<input type="hidden" name="_csrf" value="' + token + '">', html, flags=re.I)
        raw = html.encode("utf-8")
        self.send_response(status)
        if status==503:self.send_header("Retry-After","5")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Set-Cookie", security.cookie(token))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'")
        for k, v in (headers or []):
            self.send_header(k, v)
        self.end_headers(); self.wfile.write(raw)

    def send_json(self, payload, status=200):
        raw = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        if status in (429,503):self.send_header("Retry-After","60" if status==429 else "5")
        self.send_header("Cache-Control","no-store"); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def redirect(self, location, headers=None):
        self.send_response(303); self.send_header("Location", location)
        for k,v in (headers or []): self.send_header(k,v)
        self.end_headers()

    def end_headers(self):
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("X-Request-ID",getattr(self,"request_id",""))
        self.send_header("Permissions-Policy","camera=(), microphone=(), geolocation=()")
        if config.SECURE_COOKIES:self.send_header("Strict-Transport-Security","max-age=31536000")
        super().end_headers()

    def send_header(self, keyword, value):
        if keyword.lower() == 'set-cookie' and config.SECURE_COOKIES and '; Secure' not in value:
            value += '; Secure'
        super().send_header(keyword, value)

    def serve_static(self, path):
        rel = path[len("/static/"):]
        target = (STATIC_DIR / rel).resolve()
        if STATIC_DIR.resolve() not in target.parents and target != STATIC_DIR.resolve(): return self.not_found()
        if not target.exists() or not target.is_file(): return self.not_found()
        stat=target.stat()
        compressed=target.suffix in (".css",".js") and stat.st_size>1024 and accepts_gzip(self.headers.get("Accept-Encoding",""))
        raw,etag = cached_asset(str(target),stat.st_mtime_ns,stat.st_size,compressed)
        validators=[x.strip().removeprefix("W/") for x in self.headers.get("If-None-Match", "").split(",")]
        if etag in validators or "*" in validators:
            self.send_response(304); self.send_header("ETag",etag); self.send_header("Vary","Accept-Encoding"); self.send_header("Cache-Control","public, max-age=0, must-revalidate"); self.send_header("Content-Length","0"); self.end_headers(); return
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Vary","Accept-Encoding")
        if compressed:self.send_header("Content-Encoding","gzip")
        self.send_header("Content-Type", mime); self.send_header("Content-Length", str(len(raw))); self.send_header("Cache-Control", "public, max-age=0, must-revalidate"); self.send_header("ETag",etag); self.end_headers(); self.wfile.write(raw)

    def user(self):
        user = auth.current_user(self)
        if user and auth.is_blocked(user["employee_id"]):
            auth.destroy_session(self)
            return None
        return user

    def require_login(self):
        user = self.user()
        if not user:
            self.redirect("/login")
            return None
        return user

    def require_roles(self, roles, path=""):
        user = self.require_login()
        if not user: return None
        if not auth.has_role(user["employee_id"], roles):
            corr = audit.record(user["employee_id"], user["employee_id"], "ACCESS_DENIED", "PASS", {"requested_path": path, "required_roles": list(roles)})
            html = f'''<section class="empty-state danger"><div class="empty-icon">!</div><h2>Access denied</h2><p>You do not have permission to open this page.</p><div class="code-box">HTTP 403 · Correlation {ui.e(corr)}</div><a class="btn btn-primary" href="/">Return to dashboard</a></section>'''
            self.send_html(ui.layout("Access denied", html, user, active=""), 403)
            return None
        return user

    # ---------- Login ----------
    def login_page(self, query=None):
        conn = database.connect(); people = conn.execute("SELECT employee_id,name,approved_role,status FROM employees WHERE status='Active' ORDER BY approved_role,name").fetchall(); conn.close()
        options = "".join(f'<option value="{ui.e(p["employee_id"])}">{ui.e(p["name"])} — {ui.e(p["approved_role"])}</option>' for p in people)
        entra = '<a class="btn btn-secondary btn-block" href="/login/entra">Sign in with Microsoft Entra ID</a>' if config.AUTH_MODE == "entra" else '<div class="hint">Real Entra sign-in can be enabled later with environment settings.</div>'
        content = f'''<div class="login-wrap"><div class="login-panel"><div class="login-brand"><div class="brand-mark large">S</div><div><span class="eyebrow">SUNHAVEN CARE</span><h2>Workforce Access Portal</h2><p>Secure identity lifecycle, least privilege and auditable access.</p></div></div>
        <div class="security-strip"><span>Named identities</span><span>Least privilege</span><span>Audit evidence</span></div>
        <form method="post" action="/login" class="form-card"><label>Demo identity</label><select name="employee_id" required>{options}</select><button class="btn btn-primary btn-block" type="submit">Enter demo workspace</button></form>{entra}
        <p class="lab-note">Demonstration workspace · Synthetic data · Mock directory</p></div>
        <div class="login-visual"><div class="visual-orb"></div><div class="visual-card"><span class="eyebrow">CORE LIFECYCLE</span><h3>Join → Move → Leave</h3><p>Give the right worker the minimum approved access, then remove it promptly when the relationship changes.</p><div class="mini-flow"><span>Joiner</span><b>→</b><span>Mover</span><b>→</b><span>Leaver</span></div></div></div></div>'''
        if config.AUTH_MODE == 'entra':
            content = re.sub(r'<form method="post" action="/login".*?</form>', '', content, flags=re.S)
        self.send_html(ui.layout("Secure sign in", content))

    def login_local(self, query=None):
        if config.AUTH_MODE != 'local' or config.ENVIRONMENT == 'production':
            return self.error_page("Demo login disabled", "Use Microsoft sign-in.", 403)
        data = self.form(); eid = data.get("employee_id", "")
        conn = database.connect(); employee = conn.execute("SELECT * FROM employees WHERE employee_id=? AND status='Active'", (eid,)).fetchone(); conn.close()
        if not auth.employment_valid(employee) or auth.is_blocked(eid):
            return self.error_page("Sign in failed", "This identity is not active or is blocked.", 403)
        token = auth.create_session(eid)
        audit.record(eid, eid, "LOGIN_LOCAL_DEMO", "PASS", {"mode":"local-demo"})
        self.redirect("/", headers=[("Set-Cookie", f"{auth.COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={config.SESSION_MINUTES*60}")])

    def login_entra(self, query=None):
        if config.AUTH_MODE != "entra": return self.error_page("Entra login disabled", "Set SUNHAVEN_AUTH_MODE=entra to enable Microsoft sign-in.", 400)
        try:
            import msal
        except ImportError:
            return self.error_page("MSAL not installed", "Install the optional Entra dependency: pip install msal", 500)
        if not (config.TENANT_ID and config.CLIENT_ID and config.CLIENT_SECRET):
            return self.error_page("Entra configuration missing", "Configure tenant ID, client ID and client secret environment variables.", 500)
        app = self.msal_app()
        flow = app.initiate_auth_code_flow(scopes=[], redirect_uri=config.REDIRECT_URI)
        from datetime import timedelta
        expiry = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=10)).isoformat()
        with database.connect() as conn:
            conn.execute("DELETE FROM oauth_flows WHERE expires_at < ?", (datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),))
            conn.execute("INSERT INTO oauth_flows VALUES (?,?,?)", (flow['state'], json.dumps(flow), expiry))
        self.redirect(flow['auth_uri'], headers=[('Set-Cookie', f"sunhaven_oauth_state={flow['state']}; Path=/; HttpOnly; SameSite=Lax; Max-Age=600")])

    def msal_app(self):
        import msal
        return msal.ConfidentialClientApplication(config.CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{config.TENANT_ID}", client_credential=config.CLIENT_SECRET)

    def entra_callback(self, query=None):
        if config.AUTH_MODE != 'entra':
            return self.error_page("Entra disabled", "Use demo login.", 403)
        state = (query.get('state') or [''])[0]
        expected = auth.parse_cookies(self).get('sunhaven_oauth_state')
        if not expected or not secrets.compare_digest(expected.value, state):
            return self.error_page("Sign in failed", "Invalid sign-in state. Please try again.", 403)
        with database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("SELECT flow FROM oauth_flows WHERE state=? AND expires_at>?", (state, datetime.now(timezone.utc).replace(tzinfo=None).isoformat())).fetchone()
            conn.execute("DELETE FROM oauth_flows WHERE state=?", (state,))
        if not row:
            return self.error_page("Sign in expired", "Start a new Microsoft sign-in.", 403)
        try:
            result = self.msal_app().acquire_token_by_auth_code_flow(json.loads(row['flow']), {k:v[0] for k,v in query.items()})
            claims = result.get('id_token_claims', {})
            # Bind accounts to immutable tenant/object IDs, never email alone.
            if claims.get('tid') != config.TENANT_ID or not claims.get('oid'):
                raise ValueError('Identity not approved')
            with database.connect() as conn:
                employee = conn.execute("SELECT * FROM employees WHERE entra_object_id=? AND status='Active' AND cloud_enabled=1", (claims['oid'],)).fetchone()
            if not employee or auth.is_blocked(employee['employee_id']):
                raise ValueError('Identity not approved')
            if not auth.employment_valid(employee):
                raise ValueError('Expired agency identity')
            token = auth.create_session(employee['employee_id'])
            audit.record(employee['employee_id'], employee['employee_id'], 'LOGIN_ENTRA', 'PASS', {})
            self.redirect('/', headers=[('Set-Cookie', f"{auth.COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={config.SESSION_MINUTES*60}"), ('Set-Cookie', 'sunhaven_oauth_state=deleted; Path=/; HttpOnly; SameSite=Lax; Max-Age=0')])
        except Exception:
            return self.error_page("Microsoft sign-in failed", "The identity is not approved or authentication failed. Contact your administrator.", 403)

    def logout(self, query=None):
        user = self.user()
        if user: audit.record(user["employee_id"], user["employee_id"], "LOGOUT", "PASS", {})
        auth.destroy_session(self)
        self.redirect("/login", headers=[("Set-Cookie", f"{auth.COOKIE_NAME}=deleted; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")])

    # ---------- Dashboard ----------
    def dashboard(self, query=None):
        user = self.require_login()
        if not user: return
        if not auth.has_role(user['employee_id'], ['Manager','Auditor','IAMOperator']):
            content = ui.page_header('MY WORKSPACE', 'Welcome, '+user['name'].split()[0], 'Your access is limited to your approved role and care assignments.')
            content += '<div class="quick-links"><a class="quick-card" href="/residents"><b>My residents →</b><span>View your permitted care assignments</span></a><a class="quick-card" href="/requests"><b>My access requests →</b><span>Request a role or facility change</span></a><a class="quick-card" href="/guide"><b>Help & guide →</b><span>Understand your access and responsibilities</span></a></div>'
            return self.send_html(ui.layout('My workspace',content,user,active='dashboard'))
        conn = database.connect()
        active = conn.execute("SELECT COUNT(*) c FROM employees WHERE status='Active'").fetchone()["c"]
        leavers = conn.execute("SELECT COUNT(*) c FROM employees WHERE status='Leaver'").fetchone()["c"]
        agency = conn.execute("SELECT COUNT(*) c FROM employees WHERE worker_type='Agency'").fetchone()["c"]
        reviews = conn.execute("SELECT COUNT(*) c FROM access_reviews WHERE remediation_status='Pending'").fetchone()["c"]
        events = conn.execute("SELECT * FROM audit_events ORDER BY event_id DESC LIMIT 6").fetchall()
        roles = conn.execute("SELECT approved_role,COUNT(*) c FROM employees WHERE status='Active' GROUP BY approved_role ORDER BY c DESC").fetchall()
        pending = conn.execute("SELECT COUNT(*) c FROM access_requests WHERE status='Pending'").fetchone()['c']
        expiring = conn.execute("SELECT employee_id,name,end_date FROM employees WHERE worker_type='Agency' AND status='Active' AND end_date <= date('now','+14 days') ORDER BY end_date LIMIT 4").fetchall()
        note_count = conn.execute("SELECT COUNT(*) c FROM work_notes").fetchone()['c']
        conn.close()
        findings = compliance.run_checks(store=False)
        cards = ''.join([
            ui.stat_card("Active workers", active, "Approved workforce identities", "blue", "/reports?status=Active"),
            ui.stat_card("Leavers", leavers, "Access should remain disabled", "red", "/reports?status=Leaver"),
            ui.stat_card("Agency workers", agency, "Require sponsor + end date", "orange", "/employees"),
            ui.stat_card("Open findings", len(findings), "Policy checker results", "green" if not findings else "red", "/compliance"),
        ])
        event_rows = ''.join(f'<tr><td><span class="mono">{ui.e(ev["correlation_id"])}</span></td><td>{ui.e(ev["action"])}</td><td>{ui.badge(ev["result"], "green" if ev["result"]=="PASS" else "red")}</td><td>{ui.e(ev["event_time"])}</td></tr>' for ev in events) or '<tr><td colspan="4" class="muted">No audit events yet.</td></tr>'
        max_count = max([r["c"] for r in roles], default=1)
        role_bars = ''.join(f'<div class="bar-row"><span>{ui.e(r["approved_role"])}</span><div class="bar"><i style="width:{int(r["c"]/max_count*100)}%"></i></div><b>{r["c"]}</b></div>' for r in roles)
        actions = '<a class="btn btn-primary" href="/employees/new">+ New Joiner</a><a class="btn btn-secondary" href="/compliance">Run compliance</a>' if auth.has_role(user["employee_id"], ["IAMOperator"]) else '<a class="btn btn-secondary" href="/requests">Review requests</a>'
        content = ui.page_header("WORKSPACE / OVERVIEW", "Good to see you, " + user['name'].split()[0] + ".", "Here’s what needs your attention across the Sunhaven workforce.", actions)
        content += f'<div class="stats-grid">{cards}</div><div class="grid-2"><section class="panel"><div class="panel-head"><div><span class="eyebrow">LIVE ASSURANCE</span><h3>Recent audit evidence</h3></div><a href="/audit">View all</a></div><div class="table-wrap"><table><thead><tr><th>Correlation</th><th>Action</th><th>Result</th><th>UTC time</th></tr></thead><tbody>{event_rows}</tbody></table></div></section><section class="panel"><div class="panel-head"><div><span class="eyebrow">ACCESS MODEL</span><h3>Active workforce by role</h3></div></div><div class="bars">{role_bars}</div><div class="assurance-card {"ok" if not findings else "warn"}"><strong>{"No open policy violations" if not findings else str(len(findings))+" finding(s) need attention"}</strong><span>{"Current local state satisfies the compliance rules." if not findings else "Open the Compliance page to review the exact rules and affected workers."}</span></div></section></div>'
        expiry_rows = ''.join(f'<a class="attention-row" href="/employees/{ui.e(r["employee_id"])}"><div class="avatar">{ui.e(r["name"][:1])}</div><div><b>{ui.e(r["name"])}</b><span>Agency contract · {ui.e(r["end_date"])}</span></div>{ui.badge("Expired" if r['end_date'] < utc_today().isoformat() else "Due soon", "red" if r['end_date'] < utc_today().isoformat() else "orange")}<span>→</span></a>' for r in expiring) or '<p class="muted">No agency contracts expire within 14 days.</p>'
        content += f'<div class="grid-2"><section class="panel"><div class="panel-head"><div><span class="eyebrow">UPCOMING & OVERDUE</span><h3>Agency access deadlines</h3></div><a href="/employees">Directory →</a></div>{expiry_rows}</section><section class="panel next-panel"><span class="eyebrow">YOUR NEXT STEPS</span><h3>Keep access moving.</h3><a class="next-link" href="/requests"><span><b>{pending} requests waiting</b><small>Review the business reason before approval</small></span><b>↗</b></a><a class="next-link" href="/notes"><span><b>{note_count} workforce notes</b><small>Keep the next shift informed</small></span><b>↗</b></a><a class="next-link" href="/access-reviews"><span><b>{reviews} pending review actions</b><small>Follow through on access decisions</small></span><b>↗</b></a></section></div>'
        content += '<div class="quick-links"><a class="quick-card" href="/qualifications"><b>Qualification assurance</b><span>Verify expiry and renewal evidence</span></a><a class="quick-card" href="/insights"><b>Explainable risk insights</b><span>Investigate dormant and unusual access</span></a><a class="quick-card" href="/control-centre"><b>Control centre</b><span>Run jobs and configure bounded policies</span></a></div>'
        content += chart_panel()
        self.send_html(ui.layout("Overview", content, user, active="dashboard"))

    def security_assurance(self,query=None):
        user=self.require_roles(['Manager','Auditor','IAMOperator'],'/security-assurance')
        if not user:return
        try:
            # Read-only request: verification cannot replace missing or altered evidence.
            integrity=ledger.verify()
            verdict=integrity['status'];detail=f"{integrity['count']} protected events; {integrity.get('pending',0)} awaiting ingestion"
        except ledger.IntegrityError as exc:
            verdict='FAIL';detail=str(exc)
        comparison=threats.compare()
        rows=''.join(f'<tr><td>{ui.e(s["scenario"])}</td><td>{ui.e(s["control"])}</td><td>{ui.badge(s["controlled"],"green" if s["controlled"]=="BLOCKED" else "orange")}</td><td>{ui.e(s["evidence"])}</td></tr>' for s in comparison['scenarios'])
        content=ui.page_header('SECURITY WORKSTREAM','Threats and evidence','Six scenario comparisons and a verifiable ledger of committed audit events.')
        content+=f'<section class="panel"><span class="eyebrow">SALI / AUDIT INTEGRITY</span><h3>{ui.e(verdict)}</h3><p>{ui.e(detail)}</p><p class="muted">The signing key and external checkpoint must be preserved with the database.</p></section>'
        content+=f'<section class="panel"><span class="eyebrow">SITAS / CONTROL COMPARISON</span><h3>Baseline risk {comparison["baseline_risk"]} → controlled risk {comparison["controlled_risk"]}</h3><div class="table-wrap"><table><thead><tr><th>Threat</th><th>Control</th><th>Outcome</th><th>Basis</th></tr></thead><tbody>{rows}</tbody></table></div><p class="muted">This is a deterministic lab model. MFA and device trust remain open until independently configured and evidenced.</p></section>'
        with database.connect() as c:
            mfa_rows=c.execute("SELECT canonical FROM security_ledger WHERE source_id LIKE 'mfa:%' ORDER BY sequence DESC LIMIT 12").fetchall()
        findings=[]
        for entry in mfa_rows:
            try:
                event=json.loads(entry['canonical']);meta=event.get('metadata',{})
                findings.append(f'<article class="assurance-finding"><div>{ui.badge(meta.get("severity","Unknown"),"red" if meta.get("severity")=="Critical" else "orange")}<strong>{ui.e(event.get("action"))}</strong><p>{ui.e(meta.get("explanation"))}</p><small>Actor {ui.e(event.get("actor_id"))} · {ui.e(event.get("timestamp_utc"))} · Correlation {ui.e(event.get("correlation_id"))}</small></div></article>')
            except (ValueError,TypeError):pass
        content+='<section class="panel"><span class="eyebrow">SMFAA / MFA PATTERN ANALYSIS</span><h3>Recent correlated findings</h3><p class="muted">Controlled event findings are written by the CLI. No live Entra export is connected.</p>'+(''.join(findings) if findings else '<p>No findings ingested. Run the security demonstration command to generate a controlled sample.</p>')+'</section>' 
        self.send_html(ui.layout('Security assurance',content,user,active='assurance'))

    # ---------- Employees / lifecycle ----------
    def employees(self, query=None):
        user = self.require_roles(["Manager","Auditor","IAMOperator"], "/employees")
        if not user: return
        query=query or {};q=(query.get('q') or [''])[0][:100];status=(query.get('status') or [''])[0];facility=(query.get('facility') or [''])[0]
        page=int((query.get('page') or ['1'])[0])
        if not 1<=page<=1000000:raise ValueError('Use a positive page number.')
        if status and status not in config.STATUSES:raise ValueError('Unknown status.')
        if facility and facility not in config.FACILITIES:raise ValueError('Unknown facility.')
        where=' WHERE (employee_id LIKE ? OR name LIKE ? OR approved_role LIKE ?)';args=['%'+q+'%']*3
        if status:where+=' AND status=?';args.append(status)
        if facility:where+=' AND facility=?';args.append(facility)
        with database.connect() as conn:
            total=conn.execute('SELECT COUNT(*) FROM employees'+where,args).fetchone()[0]
            rows=conn.execute('SELECT * FROM employees'+where+" ORDER BY status='Active' DESC,employee_id LIMIT 25 OFFSET ?",[*args,(page-1)*25]).fetchall()
        operator=auth.has_role(user['employee_id'],['IAMOperator'])
        trs = ""
        for r in rows:
            status_tone = "green" if r["status"]=="Active" else ("red" if r["status"]=="Leaver" else "orange")
            trs += f'''<tr><td><a class="link-strong" href="/employees/{ui.e(r['employee_id'])}">{ui.e(r['employee_id'])}</a><span class="subtle">{ui.e(r['name'])}</span></td><td>{ui.badge(r['approved_role'],'blue')}</td><td>{ui.e(r['worker_type'])}</td><td>{ui.e(r['facility'])}</td><td>{ui.badge(r['status'],status_tone)}</td><td>{ui.e(r['end_date'] or '—')}</td><td class="actions"><a class="btn btn-ghost btn-small" href="/employees/{ui.e(r['employee_id'])}">View</a>{'<a class="btn btn-ghost btn-small" href="/employees/'+ui.e(r['employee_id'])+'/move">Move</a>' if r['status']=='Active' and operator else ''}</td></tr>'''
        actions = '<a class="btn btn-primary" href="/employees/new">+ New Joiner</a>' if auth.has_role(user["employee_id"],["IAMOperator"]) else ''
        actions += '<a class="btn btn-secondary" href="/exports/employees">Export CSV ↓</a>'
        content = ui.page_header("WORKFORCE DIRECTORY", "Approved identities and access", "Review worker status, approved role, facility and lifecycle dates.", actions)
        from assurance_ui import field
        content+='<form class="panel form-grid" method="get" action="/employees">'+field('Search name, ID or role','q',value=q,required=False)+field('Status','status',value=status,options=[('','All statuses')]+[(x,x) for x in config.STATUSES])+field('Site','facility',value=facility,options=[('','All sites')]+[(x,x) for x in config.FACILITIES])+'<button class="btn btn-primary">Apply filters</button></form>'
        content+=f'<section class="panel"><div class="table-wrap"><table><thead><tr><th scope="col">Employee</th><th scope="col">Role</th><th scope="col">Type</th><th scope="col">Site</th><th scope="col">Status</th><th scope="col">End date</th><th scope="col">Actions</th></tr></thead><tbody>{trs or "<tr><td colspan=7>No workers match these filters.</td></tr>"}</tbody></table></div></section>'
        content+=save_control('employees',{'q':q,'status':status,'facility':facility})
        content+=pager('/employees',{'q':q,'status':status,'facility':facility},page,total,25)
        self.send_html(ui.layout("Employees", content, user, active="employees"))

    def employee_new(self, query=None):
        user = self.require_roles(["IAMOperator"], "/employees/new")
        if not user: return
        today = utc_today().isoformat()
        form = f'''<form class="panel form-grid" method="post" action="/employees/joiner">
        <div class="field"><label>Employee ID *</label><input name="employee_id" placeholder="SC1010" required></div><div class="field"><label>Full name *</label><input name="name" required></div>
        <div class="field"><label>Email / UPN *</label><input type="email" name="email" placeholder="name@sunhaven.test" required></div><div class="field"><label>Worker type *</label><select name="worker_type">{ui.worker_type_options()}</select></div>
        <div class="field"><label>Approved role *</label><select name="approved_role">{ui.role_options()}</select></div><div class="field"><label>Facility *</label><select name="facility">{ui.facility_options()}</select></div>
        <div class="field"><label>Manager / sponsor</label><input name="manager_sponsor" placeholder="Required for agency workers"></div><div class="field"><label>Start date *</label><input type="date" name="start_date" value="{today}" required></div>
        <div class="field"><label>End date</label><input type="date" name="end_date"></div><input type="hidden" name="status" value="Active">
        <div class="form-actions full"><button class="btn btn-secondary" type="submit" name="mode" value="dry">Dry run only</button><button class="btn btn-primary" type="submit" name="mode" value="apply">Create Joiner</button></div></form>'''
        content = ui.page_header("JOINER", "Create a new approved worker", "Validate the workforce record before any access is created. Agency workers require a sponsor and end date.") + form
        self.send_html(ui.layout("New Joiner", content, user, active="employees"))

    def employee_joiner(self, query=None):
        user = self.require_roles(["IAMOperator"], "/employees/joiner")
        if not user: return
        data = self.form(); mode = data.pop("mode", "apply")
        try:
            if mode == "dry":
                plan = lifecycle.dry_run_joiner(data)
                content = self.plan_html("Joiner dry run", plan, "/employees/new")
                return self.send_html(ui.layout("Joiner dry run", content, user, active="employees"))
            state, corr = lifecycle.joiner(data, user["employee_id"])
            self.redirect(f"/employees/{state['employee_id']}?msg=Joiner+completed+successfully&corr={corr}")
        except Exception as exc:
            self.send_html(ui.layout("Joiner failed", ui.page_header("JOINER", "Validation stopped the change", str(exc)) + '<a class="btn btn-secondary" href="/employees/new">Back to form</a>', user, active="employees"), 400)

    def employee_detail(self, employee_id, query=None):
        user = self.require_roles(["Manager","Auditor","IAMOperator"], f"/employees/{employee_id}")
        if not user: return
        state = lifecycle.get_employee_state(employee_id)
        if not state: return self.not_found()
        msg = (query.get("msg") or [""])[0]; corr = (query.get("corr") or [""])[0]
        flash = ui.alert(msg + (f" · Correlation {corr}" if corr else ""), "success") if msg else ""
        role_badges = ''.join(ui.badge(r,'blue') for r in state['actual_roles']) or ui.badge('No active role','red')
        assignment_badges = ''.join(ui.badge(r,'neutral') for r in state['active_assignments']) or ui.badge('No assignments','neutral')
        status_tone = "green" if state['status']=="Active" else "red"
        buttons = ''
        if state['status']=='Active' and auth.has_role(user['employee_id'],['IAMOperator']):
            buttons = f'<a class="btn btn-secondary" href="/employees/{ui.e(employee_id)}/move">Mover</a><form method="post" action="/employees/{ui.e(employee_id)}/leave" class="inline" data-confirm="Process this worker as a Leaver?"><button class="btn btn-danger" type="submit">Process Leaver</button></form>'
        content = flash + ui.page_header("WORKFORCE IDENTITY", state['name'], f"Employee {state['employee_id']} · {state['email']}", buttons)
        content += f'''<div class="grid-2"><section class="panel"><div class="panel-head"><h3>Approved workforce record</h3></div><dl class="detail-grid"><dt>Status</dt><dd>{ui.badge(state['status'],status_tone)}</dd><dt>Approved role</dt><dd>{ui.e(state['approved_role'])}</dd><dt>Worker type</dt><dd>{ui.e(state['worker_type'])}</dd><dt>Facility</dt><dd>{ui.e(state['facility'])}</dd><dt>Manager / sponsor</dt><dd>{ui.e(state['manager_sponsor'] or '—')}</dd><dt>Start</dt><dd>{ui.e(state['start_date'])}</dd><dt>End</dt><dd>{ui.e(state['end_date'] or '—')}</dd></dl></section><section class="panel"><div class="panel-head"><h3>Current access state</h3></div><dl class="detail-grid"><dt>Cloud enabled</dt><dd>{ui.badge('Yes' if state['cloud_enabled'] else 'No','green' if state['cloud_enabled'] else 'red')}</dd><dt>Cloud role</dt><dd>{ui.e(state['cloud_role'] or 'None')}</dd><dt>Portal blocked</dt><dd>{ui.badge('Yes' if state['blocked'] else 'No','red' if state['blocked'] else 'green')}</dd><dt>Actual roles</dt><dd>{role_badges}</dd><dt>Resident assignments</dt><dd>{assignment_badges}</dd><dt>Entra object</dt><dd><span class="mono">{ui.e(state['entra_object_id'] or 'Not synced')}</span></dd></dl></section></div>'''
        with database.connect() as conn:
            timeline=conn.execute("SELECT category,body,created_at FROM work_notes WHERE employee_id=? ORDER BY note_id DESC LIMIT 5",(employee_id,)).fetchall()
        notes=''.join(f'<div class="timeline-item"><b>{ui.e(n["category"])}</b><small>{ui.e(n["created_at"])}</small><p class="note-body">{ui.e(n["body"])}</p></div>' for n in timeline) or '<p class="muted">No workforce notes recorded yet.</p>'
        content+=f'<section class="panel"><div class="panel-head"><h3>Workforce notes</h3><a href="/notes?employee={ui.e(employee_id)}">Add a note →</a></div>{notes}</section>'
        self.send_html(ui.layout(f"Employee {employee_id}", content, user, active="employees"))

    def employee_move_page(self, employee_id, query=None):
        user = self.require_roles(["IAMOperator"], f"/employees/{employee_id}/move")
        if not user: return
        state = lifecycle.get_employee_state(employee_id)
        if not state: return self.not_found()
        content = ui.page_header("MOVER", f"Change access for {state['name']}", "The system removes obsolete access before adding the new approved role.")
        content += f'''<form class="panel form-grid" method="post" action="/employees/{ui.e(employee_id)}/move"><div class="field"><label>Current role</label><input value="{ui.e(state['approved_role'])}" disabled></div><div class="field"><label>New role *</label><select name="new_role">{ui.role_options(state['approved_role'])}</select></div><div class="field"><label>Current facility</label><input value="{ui.e(state['facility'])}" disabled></div><div class="field"><label>New facility *</label><select name="new_facility">{ui.facility_options(state['facility'])}</select></div><div class="form-actions full"><button class="btn btn-secondary" name="mode" value="dry">Dry run only</button><a class="btn btn-primary" href="/requests">Open access requests</a></div></form>'''
        self.send_html(ui.layout("Mover", content, user, active="employees"))

    def employee_move(self, employee_id, query=None):
        user = self.require_roles(["IAMOperator"], f"/employees/{employee_id}/move")
        if not user: return
        data = self.form(); mode=data.get("mode","apply")
        try:
            if mode=="dry":
                plan=lifecycle.dry_run_mover(employee_id,data.get("new_role"),data.get("new_facility")); content=self.plan_html("Mover dry run",plan,f"/employees/{employee_id}/move"); return self.send_html(ui.layout("Mover dry run",content,user,active="employees"))
            return self.error_page("Approval required", "Submit and approve an access request, then use Execute approved change on the Access requests page.", 409, user=user)
        except ledger.IntegrityError:raise
        except Exception as exc:
            self.error_page("Mover failed",str(exc),400,user=user)

    def employee_leave(self, employee_id, query=None):
        user=self.require_roles(["IAMOperator"],f"/employees/{employee_id}/leave")
        if not user:return
        try:
            state,corr=lifecycle.leaver(employee_id,user["employee_id"]); self.redirect(f"/employees/{employee_id}?msg=Leaver+completed+-+access+removed&corr={corr}")
        except ledger.IntegrityError:raise
        except Exception as exc:self.error_page("Leaver failed",str(exc),400,user=user)

    def plan_html(self,title,plan,back):
        items=''.join(f'<li>{ui.e(x)}</li>' for x in plan['changes'])
        return ui.page_header("DRY RUN",title,"No identity or access changes were made.")+f'<section class="panel"><div class="plan-banner"><span>✓</span><div><strong>Validation passed</strong><p>Review the planned actions before applying the lifecycle change.</p></div></div><ol class="plan-list">{items}</ol><a class="btn btn-secondary" href="{ui.e(back)}">Back</a></section>'

    # ---------- Residents / protected pages ----------
    def residents(self, query=None):
        user=self.require_login()
        if not user:return
        conn=database.connect()
        rows=assurance.permitted_residents(conn,user)
        conn.close()
        cards=''.join(f'<div class="resident-card"><div class="resident-icon">R</div><div><strong>{ui.e(r["fictional_name"])}</strong><span>{ui.e(r["resident_id"])} · {ui.e(r["room"])}</span><small>{ui.e(r["facility"])}</small></div></div>' for r in rows) or '<div class="empty-state"><div class="empty-icon">—</div><h3>No permitted resident records</h3><p>Your current role or assignment does not provide resident-data access.</p></div>'
        content=ui.page_header("SYNTHETIC CARE DATA","Permitted resident view","Only fictional resident records are shown. Access is limited by role, facility and assignment.")+f'<div class="resident-grid">{cards}</div><div class="quick-links"><a class="quick-card" href="/protected/care-notes"><b>Care Notes</b><span>Role-protected page</span></a><a class="quick-card" href="/protected/clinical"><b>Clinical</b><span>Nurse / Manager only</span></a><a class="quick-card" href="/protected/review"><b>Review</b><span>Manager / Auditor only</span></a></div>'
        self.send_html(ui.layout("Residents",content,user,active="residents"))

    def qualified_resource(self,user,clinical=False):
        with database.connect() as c:
            if assurance.qualified(c,user["employee_id"],clinical):return True
        audit.record(user["employee_id"],user["employee_id"],"ACCESS_DENIED","PASS",{"reason":"Required qualification missing or expired"})
        self.error_page("Qualification required","Current verified qualifications are required for care access. Contact your manager.",403,user)
        return False

    def protected_content(self,user,kicker,title,text,active=""):
        audit.record(user["employee_id"],None,"ACCESS_ALLOWED","PASS",{"resource":title})
        return ui.page_header(kicker,title,text)+f'<section class="panel"><div class="security-allowed"><span>✓</span><div><strong>Access permitted</strong><p>Signed in as {ui.e(user["name"])} · Trusted role: {ui.e(user["approved_role"])}</p></div></div><p class="muted">This page demonstrates server-side authorisation. Direct URL requests are also checked before content is returned.</p></section>'

    def care_notes(self,query=None):
        user=self.require_roles(["CareWorker","Nurse","AgencyWorker","Manager"],"/protected/care-notes");
        if user and self.qualified_resource(user):self.send_html(ui.layout("Care Notes",self.protected_content(user,"PROTECTED RESOURCE","Care Notes","Synthetic demonstration area for permitted care workers."),user,active="residents"))
    def clinical(self,query=None):
        user=self.require_roles(["Nurse","Manager"],"/protected/clinical");
        if user and self.qualified_resource(user,clinical=user["approved_role"]=="Nurse"):self.send_html(ui.layout("Clinical",self.protected_content(user,"PROTECTED RESOURCE","Clinical view","Restricted to Nurse and Manager roles."),user,active="residents"))
    def review_page(self,query=None):
        user=self.require_roles(["Manager","Auditor"],"/protected/review");
        if user:self.send_html(ui.layout("Review",self.protected_content(user,"PROTECTED RESOURCE","Assurance review","Restricted to Manager and Auditor roles."),user,active="reviews"))
    def iam_admin(self,query=None):
        user=self.require_roles(["IAMOperator"],"/protected/iam-admin");
        if user:self.send_html(ui.layout("IAM Admin",self.protected_content(user,"PRIVILEGED RESOURCE","IAM administration","Separate privileged access for approved IAM operators."),user,active="employees"))

    # ---------- Access reviews ----------
    def access_reviews(self,query=None):
        user=self.require_roles(["Manager","Auditor","IAMOperator"],"/access-reviews")
        if not user:return
        conn=database.connect(); employees=conn.execute("SELECT employee_id,name,approved_role,status FROM employees ORDER BY name").fetchall(); reviews=conn.execute("SELECT ar.*,e.name FROM access_reviews ar JOIN employees e ON e.employee_id=ar.employee_id ORDER BY ar.review_id DESC LIMIT 25").fetchall(); conn.close()
        opts=''.join(f'<option value="{ui.e(e["employee_id"])}">{ui.e(e["name"])} — {ui.e(e["approved_role"])}</option>' for e in employees)
        rows=''.join(f'<tr><td>{ui.e(r["name"])}</td><td>{ui.badge(r["decision"],"blue")}</td><td>{ui.e(r["reviewer_id"])}</td><td>{ui.e(r["review_date"])}</td><td>{ui.e(r["reason"])}</td><td>{ui.badge(r["remediation_status"],"green" if r["remediation_status"]=="Closed" else "orange")}</td></tr>' for r in reviews)
        form=f'''<section class="panel"><div class="panel-head"><div><span class="eyebrow">MANAGER / AUDITOR</span><h3>Record access review</h3></div></div><form method="post" action="/access-reviews" class="form-grid"><div class="field"><label>Worker</label><select name="employee_id">{opts}</select></div><div class="field"><label>Decision</label><select name="decision"><option>Retain</option><option>Change</option><option>Remove</option><option>Temporary Exception</option></select></div><div class="field full"><label>Reason *</label><input name="reason" required placeholder="Why is this access decision appropriate?"></div><div class="field"><label>Exception expiry</label><input type="date" name="exception_expiry"></div><div class="field"><label>Remediation status</label><select name="remediation_status"><option>Closed</option><option>Pending</option></select></div><div class="form-actions full"><button class="btn btn-primary">Save review</button></div></form></section>'''
        content=ui.page_header("ACCESS GOVERNANCE","Periodic access reviews","Record whether access should be retained, changed, removed or temporarily accepted as an exception.", '<a class="btn btn-secondary" href="/exports/reviews">Export CSV ↓</a>')+form+f'<section class="panel"><div class="panel-head"><h3>Recent review evidence</h3></div><div class="table-wrap"><table><thead><tr><th>Worker</th><th>Decision</th><th>Reviewer</th><th>Date</th><th>Reason</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
        self.send_html(ui.layout("Access Reviews",content,user,active="reviews"))

    def access_review_save(self,query=None):
        user=self.require_roles(["Manager","Auditor","IAMOperator"],"/access-reviews")
        if not user:return
        d=self.form();
        if d.get("employee_id")==user["employee_id"]:return self.error_page("Independent review required","Ask another reviewer to attest your access.",403,user)
        if d.get('decision') not in ['Retain','Change','Remove','Temporary Exception'] or not d.get('reason'):
            return self.error_page("Invalid access review","Decision and reason are required.",400,user=user)
        if len(d['reason'].strip()) < 5 or len(d['reason']) > 2000 or d.get('remediation_status') not in ('Closed','Pending'):
            return self.error_page("Invalid review", "Use a reason of 5–2,000 characters and a valid status.", 400)
        if d['decision'] == 'Temporary Exception':
            try:
                if date.fromisoformat(d.get('exception_expiry','')) <= utc_today():
                    raise ValueError()
            except ValueError:
                return self.error_page("Invalid exception", "An exception needs a future expiry date.", 400)
        if d['decision'] in ('Change','Remove'):
            d['remediation_status'] = 'Pending'
        import governance
        with database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE');governance.require(conn,user['employee_id'],{'Manager','Auditor','IAMOperator'})
            exists=conn.execute("SELECT 1 FROM employees WHERE employee_id=?",(d.get('employee_id'),)).fetchone()
            if not exists:return self.error_page("Invalid access review","Employee was not found.",400,user=user)
            conn.execute("INSERT INTO access_reviews(employee_id,reviewer_id,decision,reason,review_date,exception_expiry,remediation_status) VALUES (?,?,?,?,?,?,?)",(d['employee_id'],user['employee_id'],d['decision'],d['reason'],datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='seconds')+'Z',d.get('exception_expiry') or None,d.get('remediation_status') or 'Pending'))
            audit.record_on(conn,user['employee_id'],d['employee_id'],'ACCESS_REVIEW','PASS',{'decision':d['decision'],'reason':d['reason'],'remediation_status':d.get('remediation_status')})
        self.redirect('/access-reviews')

    # ---------- Audit / compliance ----------
    def audit_log(self,query=None):
        return AssurancePages.audit_log(self,query)

    def compliance_page(self,query=None):
        user=self.require_roles(["Manager","Auditor","IAMOperator"],"/compliance")
        if not user:return
        findings=compliance.run_checks(store=False)
        cards=''.join(f'<article class="finding severity-{ui.e(f["severity"].lower())}"><div class="finding-top"><span class="rule">{ui.e(f["rule_id"])}</span>{ui.badge(f["severity"],"red" if f["severity"] in ("Critical","High") else "orange")}</div><h3>{ui.e(f["title"])}</h3><p>{ui.e(f["details"])}</p><a href="/employees/{ui.e(f["employee_id"])}">Affected worker: {ui.e(f["employee_id"])}</a></article>' for f in findings)
        if not cards: cards='<div class="empty-state success"><div class="empty-icon">✓</div><h3>No current violations</h3><p>The local workforce state passes the configured policy rules.</p></div>'
        actions='<form method="post" action="/compliance/run"><button class="btn btn-primary">Run & store scan</button></form>'
        rules='''<div class="rules-grid"><span>C01 Enabled leaver</span><span>C02 Expired agency</span><span>C03 Missing sponsor/end date</span><span>C04 Role mismatch</span><span>C05 Conflicting roles</span><span>C06 Disabled user with access</span><span>C07 Unexpected admin privilege</span><span>C08 Review overdue</span></div>'''
        content=ui.page_header("POLICY AS CODE","Compliance checker","Read-only deterministic checks compare approved workforce rules with the current access state.",actions)+rules+f'<div class="findings-grid">{cards}</div>'
        self.send_html(ui.layout("Compliance",content,user,active="compliance"))

    def compliance_run(self,query=None):
        user=self.require_roles(["Manager","Auditor","IAMOperator"],"/compliance/run")
        if not user:return
        findings=compliance.run_checks(store=True,actor=user['employee_id'])
        self.redirect('/compliance')

    # ---------- Requirements ----------
    def requirements_page(self,query=None):
        user=self.require_login()
        if not user:return
        checks=[
            ("Employee records and workforce fields","Working","Employees page + SQLite workforce table"),
            ("Approved roles","Working","CareWorker, Nurse, Manager, AgencyWorker, Auditor, IAMOperator"),
            ("Secure login","Local demo works","Enable Entra mode for live tenant sign-in"),
            ("MFA","Tenant-controlled","Demonstrate through Entra Conditional Access / security defaults in live tenant"),
            ("Server-side RBAC","Working","Protected care/clinical/review/admin routes"),
            ("Joiner lifecycle","Working","Validation + dry run + local/Graph adapter + evidence"),
            ("Mover lifecycle","Working","Old role removed before new role is assigned"),
            ("Leaver lifecycle","Working","Disable + revoke + remove roles/assignments + block + evidence"),
            ("Agency sponsor/end date validation","Working","Joiner validation + compliance rules"),
            ("Synthetic resident access","Working","Role/facility/assignment filtered resident page"),
            ("Access reviews","Working","Retain / Change / Remove / Temporary Exception"),
            ("Sanitised audit evidence","Working","Audit log redacts secret fields"),
            ("Compliance checker","Working","C01-C08 deterministic read-only rules"),
            ("GitHub / version control","Ready","Add this project folder to the team repository"),
            ("Microsoft Entra sign-in","Needs tenant test","Configure immutable tenant/object IDs and verify real sign-in/MFA"),
            ("Live Graph changes","Disabled","Integration and partial-failure tests required before enabling"),
            ("Requests, notes and CSV exports","Working","Role-aware workflows with audit metadata"),
            ("Approved Mover execution","Working","Seven-day validity, role snapshot and atomic local audit"),
            ("Operations administration","Working","Assignments, sessions, remediation tasks and review closure"),
            ("Deployment configuration","Ready","WSGI server, Docker, TLS proxy and persistent data volume"),
        ]
        rows=''.join(f'<tr><td>{ui.e(a)}</td><td>{ui.badge(b,"green" if b=="Working" else ("orange" if "Needs" in b or "Tenant" in b or "Local" in b else "blue"))}</td><td>{ui.e(c)}</td></tr>' for a,b,c in checks)
        content=ui.page_header("ASSESSMENT READINESS","Requirement checklist","Use this page before the final demo. Green items are implemented locally; orange items require live Entra/tenant evidence.")+f'<section class="panel"><div class="table-wrap"><table><thead><tr><th>Requirement</th><th>Status</th><th>Evidence / next step</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
        self.send_html(ui.layout("Requirements",content,user,active="requirements"))

    # ---------- Error ----------
    def not_found(self):
        user=self.user(); self.send_html(ui.layout("Not found",'<section class="empty-state"><div class="empty-icon">?</div><h2>Page not found</h2><p>The requested page does not exist.</p><a class="btn btn-primary" href="/">Return home</a></section>',user),404)
    def error_page(self,title,message,status=500,user=None):
        if self.path.split('?')[0]=='/assistant/ask':
            return self.send_json({'error':{'code':str(status),'message':message},'request_id':getattr(self,'request_id','')},status)
        user=(user or self.user()) if status!=503 else None; self.send_html(ui.layout(title,f'<section class="empty-state danger"><div class="empty-icon">!</div><h2>{ui.e(title)}</h2><p>{ui.e(message)}</p><p class="muted">Request: {ui.e(getattr(self, 'request_id', ''))}</p><a href="/help?topic=errors">Get help with this error</a><a class="btn btn-primary" href="/">Return home</a></section>',user),status)


def run():
    config.validate_config()
    database.init_db()
    import queue_worker
    queue_stop=queue_worker.start()
    server=ThreadingHTTPServer((config.HOST,config.PORT),AppHandler)
    print(f"Sunhaven Care IAM running at http://{config.HOST}:{config.PORT}")
    print(f"Auth mode: {config.AUTH_MODE} | Graph mode: {config.GRAPH_MODE}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        if queue_stop:queue_stop.set()
        server.server_close()
