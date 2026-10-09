from datetime import timezone
import secrets
import hashlib
from datetime import date, datetime, timedelta
from http.cookies import SimpleCookie
from urllib.parse import urlencode
import database
import config

COOKIE_NAME = "sunhaven_session"


def parse_cookies(handler):
    cookie = SimpleCookie()
    if handler.headers.get("Cookie"):
        cookie.load(handler.headers.get("Cookie"))
    return cookie


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def employment_valid(row):
    if not row or row["status"] != "Active" or not row["cloud_enabled"]: return False
    try:
        today=datetime.now(timezone.utc).date()
        if date.fromisoformat(row['start_date']) > today: return False
        if row['end_date'] and date.fromisoformat(row['end_date']) < today: return False
        if row['worker_type']=='Agency' and not row['end_date']: return False
        return True
    except (ValueError, TypeError):
        return False


def current_user(handler):
    cookie = parse_cookies(handler)
    morsel = cookie.get(COOKIE_NAME)
    if not morsel:
        return None
    token = morsel.value
    conn = database.connect()
    row = conn.execute("""
        SELECT e.* FROM sessions s JOIN employees e ON e.employee_id=s.employee_id
        WHERE s.token=? AND s.expires_at>?
    """, (token_digest(token), datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"))).fetchone()
    conn.close()
    if not employment_valid(row):
        return None
    return dict(row)


def create_session(employee_id):
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires = now + timedelta(minutes=config.SESSION_MINUTES)
    with database.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row=conn.execute("SELECT * FROM employees WHERE employee_id=?",(employee_id,)).fetchone()
        if not employment_valid(row) or conn.execute("SELECT 1 FROM blocked_users WHERE employee_id=?",(employee_id,)).fetchone():
            raise PermissionError("Worker is inactive, not yet started, blocked or expired.")
        conn.execute("DELETE FROM sessions WHERE employee_id=?", (employee_id,))
        conn.execute("INSERT INTO sessions(token,employee_id,expires_at,created_at) VALUES (?,?,?,?)",
                     (token_digest(token), employee_id, expires.isoformat(timespec="seconds"), now.isoformat(timespec="seconds")))
        conn.execute("INSERT INTO login_activity VALUES (?,?) ON CONFLICT(employee_id) DO UPDATE SET last_login=excluded.last_login", (employee_id,now.isoformat(timespec="seconds")))
    return token


def destroy_session(handler):
    cookie = parse_cookies(handler)
    morsel = cookie.get(COOKIE_NAME)
    if morsel:
        conn = database.connect(); conn.execute("DELETE FROM sessions WHERE token=?", (token_digest(morsel.value),)); conn.commit(); conn.close()


def is_blocked(employee_id):
    conn = database.connect(); row = conn.execute("SELECT 1 FROM blocked_users WHERE employee_id=?", (employee_id,)).fetchone(); conn.close()
    return row is not None


def has_role(employee_id, allowed_roles):
    conn = database.connect()
    roles = {r["role"] for r in conn.execute("SELECT role FROM employee_roles WHERE employee_id=?", (employee_id,)).fetchall()}
    conn.close()
    return bool(roles.intersection(set(allowed_roles)))


def set_session_cookie(handler, token):
    handler.send_header("Set-Cookie", f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={config.SESSION_MINUTES*60}")


def clear_session_cookie(handler):
    handler.send_header("Set-Cookie", f"{COOKIE_NAME}=deleted; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")
