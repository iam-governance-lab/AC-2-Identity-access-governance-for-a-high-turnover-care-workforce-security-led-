from datetime import timezone
import json
import secrets
from datetime import datetime
import database


def new_correlation_id(prefix="EVT"):
    return f"{prefix}-{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"


def record_on(conn, actor_id, target_id, action, result, details=None, final_state=None, correlation_id=None):
    """Record evidence in the caller's protected business transaction."""
    correlation_id = correlation_id or new_correlation_id()
    conn.execute("""INSERT INTO audit_events(actor_id,target_id,action,event_time,result,correlation_id,details,final_state)
                    VALUES (?,?,?,?,?,?,?,?)""", (
        actor_id or "SYSTEM", target_id, action,
        datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
        result, correlation_id, json.dumps(_sanitize(details or {}),sort_keys=True),
        json.dumps(_sanitize(final_state or {}),sort_keys=True)))
    return correlation_id


def record(actor_id, target_id, action, result, details=None, final_state=None, correlation_id=None):
    with database.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        return record_on(conn,actor_id,target_id,action,result,details,final_state,correlation_id)


def _sanitize(value):
    secret_keys = {"password", "secret", "client_secret", "token", "access_token", "refresh_token", "mfa_code"}
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if str(k).lower() in secret_keys:
                result[k] = "[REDACTED]"
            else:
                result[k] = _sanitize(v)
        return result
    if isinstance(value, list):
        return [_sanitize(x) for x in value]
    return value
