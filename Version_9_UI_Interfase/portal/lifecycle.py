from clock import utc_today
from datetime import timezone
from datetime import date, datetime
import sqlite3
import re
import config
import database
import audit
import governance
from graph_service import GraphService, GraphError


graph = GraphService()


class ValidationError(ValueError):
    pass


def _row_dict(row):
    return dict(row) if row else None


def validate_employee(data, existing_id=None):
    required = ["employee_id", "name", "email", "worker_type", "approved_role", "facility", "status", "start_date"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        raise ValidationError("Missing required fields: " + ", ".join(missing))
    if data["approved_role"] not in config.ALLOWED_ROLES:
        raise ValidationError("Unknown role.")
    if data["worker_type"] not in config.WORKER_TYPES:
        raise ValidationError("Unknown worker type.")
    if data["status"] not in config.STATUSES:
        raise ValidationError("Unknown status.")
    if data["facility"] not in config.FACILITIES:
        raise ValidationError("Unknown facility.")
    if data["worker_type"] == "Agency":
        if not str(data.get("manager_sponsor", "")).strip():
            raise ValidationError("Agency workers must have a named sponsor.")
        if not str(data.get("end_date", "")).strip():
            raise ValidationError("Agency workers must have an end date.")
    for field in ("start_date", "end_date"):
        if data.get(field):
            try:
                date.fromisoformat(data[field])
            except Exception as exc:
                raise ValidationError(f"{field.replace('_',' ').title()} must be a valid date.") from exc
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,32}", data['employee_id']):
        raise ValidationError("Employee ID must be 2–32 letters, numbers, underscores or hyphens.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", data['email']) or len(data['email']) > 254:
        raise ValidationError("Enter a valid email address.")
    if len(data['name']) > 100 or len(data.get('manager_sponsor','')) > 100:
        raise ValidationError("Name and sponsor are limited to 100 characters.")
    if data.get('end_date') and data['end_date'] < data['start_date']:
        raise ValidationError("End date must not be before start date.")
    if data['worker_type'] == 'Agency' and data['end_date'] < utc_today().isoformat():
        raise ValidationError("An agency Joiner must have a current or future end date.")
    conn = database.connect()
    try:
        duplicate = conn.execute("SELECT employee_id FROM employees WHERE lower(email)=lower(?) AND employee_id<>?", (data["email"], existing_id or "")).fetchone()
        if duplicate:
            raise ValidationError("Email/UPN is already assigned to another employee.")
    finally:
        conn.close()


def dry_run_joiner(data):
    validate_employee(data)
    conn = database.connect()
    exists = conn.execute("SELECT employee_id FROM employees WHERE employee_id=?", (data["employee_id"],)).fetchone()
    conn.close()
    if exists:
        raise ValidationError("Employee ID already exists. Use Mover/Edit instead.")
    return {
        "action": "JOINER",
        "changes": [
            f"Create local workforce record {data['employee_id']}",
            f"Create/reconcile Entra identity {data['email']}",
            f"Assign approved role {data['approved_role']}",
            f"Set facility {data['facility']}",
            "Create audit evidence and verify final state",
        ]
    }


def joiner(data, actor_id):
    if data.get("status")!="Active":raise ValidationError("Joiner status must be Active; use termination/suspension workflows for existing staff.")
    data=dict(data);data["email"]=str(data.get("email", "")).strip().lower()
    plan = dry_run_joiner(data)
    correlation = audit.new_correlation_id("JNR")
    conn = database.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        governance.require(conn,actor_id,{"IAMOperator"})
        conn.execute("""
            INSERT INTO employees(employee_id,name,email,worker_type,approved_role,facility,status,manager_sponsor,start_date,end_date,cloud_enabled,cloud_role,admin_privilege)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data["employee_id"], data["name"], data["email"], data["worker_type"], data["approved_role"], data["facility"],
            "Active", data.get("manager_sponsor") or None, data["start_date"], data.get("end_date") or None, 1, data["approved_role"],
            1 if data["approved_role"] == "IAMOperator" else 0
        ))
        conn.execute("INSERT INTO employee_roles(employee_id,role) VALUES (?,?)", (data["employee_id"], data["approved_role"]))
        employee = dict(conn.execute("SELECT * FROM employees WHERE employee_id=?", (data["employee_id"],)).fetchone())
        graph_result = graph.create_or_reconcile_user(employee)
        object_id = graph_result.get("id")
        graph.replace_role_group(object_id, data["approved_role"])
        conn.execute("UPDATE employees SET entra_object_id=?, cloud_enabled=1, cloud_role=?, updated_at=CURRENT_TIMESTAMP WHERE employee_id=?", (object_id, data["approved_role"], data["employee_id"]))
        import assurance
        current=conn.execute("SELECT facility FROM employees WHERE employee_id=?",(data["employee_id"],)).fetchone()
        assurance.sync_team(conn,data["employee_id"],current[0])
        final_state = get_employee_state(data["employee_id"],conn)
        audit.record_on(conn,actor_id,data["employee_id"],"JOINER","PASS",{"plan":plan["changes"]},final_state,correlation)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        from security_workstream.ledger import IntegrityError
        if isinstance(exc,IntegrityError):raise
        audit.record(actor_id, data.get("employee_id"), "JOINER", "FAIL", {"reason": str(exc)}, correlation_id=correlation)
        raise
    finally:
        conn.close()
    return final_state, correlation


def dry_run_mover(employee_id, new_role, new_facility):
    if new_role not in config.ALLOWED_ROLES:
        raise ValidationError("Unknown target role.")
    if new_facility not in config.FACILITIES:
        raise ValidationError("Unknown target facility.")
    state = get_employee_state(employee_id)
    if not state:
        raise ValidationError("Employee not found.")
    if state['status'] != 'Active' or state['blocked'] or not state['cloud_enabled']:
        raise ValidationError("Only active, unblocked workers can be moved.")
    if state['worker_type'] == 'Agency' and (not state['end_date'] or state['end_date'] < utc_today().isoformat()):
        raise ValidationError("Expired agency workers cannot be moved.")
    return {
        "action": "MOVER",
        "changes": [
            f"Remove old role {state['approved_role']}",
            f"Assign new role {new_role}",
            f"Change facility {state['facility']} -> {new_facility}",
            "Clear old resident assignments if facility/role changed",
            "Require fresh sign-in for changed claims where supported",
            "Verify old access no longer works and record evidence",
        ]
    }


def mover(employee_id, new_role, new_facility, actor_id):
    plan = dry_run_mover(employee_id, new_role, new_facility)
    correlation = audit.new_correlation_id("MVR")
    conn = database.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        governance.require(conn,actor_id,{"IAMOperator"})
        employee = conn.execute("SELECT * FROM employees WHERE employee_id=?", (employee_id,)).fetchone()
        if plan["action"]=="MOVER":
            import enterprise
            enterprise.active(conn,employee_id)
        object_id = employee["entra_object_id"] or f"mock-{employee_id.lower()}"
        import assurance
        if new_role != "IAMOperator":assurance.protect_operator(conn,actor_id,employee_id)
        # Safer order: remove governed access before adding new role.
        conn.execute("DELETE FROM employee_roles WHERE employee_id=?", (employee_id,))
        conn.execute("UPDATE assignments SET active=0 WHERE employee_id=?", (employee_id,))
        graph.replace_role_group(object_id, None)
        conn.execute("UPDATE employees SET approved_role=?, facility=?, cloud_role=NULL, updated_at=CURRENT_TIMESTAMP WHERE employee_id=?", (new_role, new_facility, employee_id))
        conn.execute("INSERT INTO employee_roles(employee_id,role) VALUES (?,?)", (employee_id, new_role))
        updated = dict(conn.execute("SELECT * FROM employees WHERE employee_id=?", (employee_id,)).fetchone())
        conn.execute("DELETE FROM sessions WHERE employee_id=?", (employee_id,))
        graph.update_profile(object_id, updated)
        graph.replace_role_group(object_id, new_role)
        conn.execute("UPDATE employees SET cloud_role=?, cloud_enabled=1, admin_privilege=?, status='Active' WHERE employee_id=?", (new_role, 1 if new_role == "IAMOperator" else 0, employee_id))
        import assurance
        current=conn.execute("SELECT facility FROM employees WHERE employee_id=?",(employee_id,)).fetchone()
        assurance.sync_team(conn,employee_id,current[0])
        final_state = get_employee_state(employee_id,conn)
        audit.record_on(conn,actor_id,employee_id,"MOVER","PASS",{"plan":plan["changes"]},final_state,correlation)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        from security_workstream.ledger import IntegrityError
        if isinstance(exc,IntegrityError):raise
        audit.record(actor_id, employee_id, "MOVER", "FAIL", {"reason": str(exc)}, correlation_id=correlation)
        raise
    finally:
        conn.close()
    return final_state, correlation


def dry_run_leaver(employee_id):
    state = get_employee_state(employee_id)
    if not state:
        raise ValidationError("Employee not found.")
    return {
        "action": "LEAVER",
        "changes": [
            "Disable Entra/local cloud identity",
            "Revoke available sessions",
            "Remove Sunhaven role/group access",
            "Remove resident/facility assignments",
            "Add identity to portal blocked-user list",
            "Verify new and existing protected access is denied",
            "Keep audit evidence instead of deleting the identity",
        ]
    }


def leaver(employee_id, actor_id, reason="Employment ended"):
    with database.connect() as c:
        import assurance
        assurance.protect_operator(c,actor_id,employee_id)
    plan = dry_run_leaver(employee_id)
    correlation = audit.new_correlation_id("LVR")
    conn = database.connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        governance.require(conn,actor_id,{"IAMOperator"})
        employee = conn.execute("SELECT * FROM employees WHERE employee_id=?", (employee_id,)).fetchone()
        if plan["action"]=="MOVER":
            import enterprise
            enterprise.active(conn,employee_id)
        object_id = employee["entra_object_id"] or f"mock-{employee_id.lower()}"
        import assurance
        assurance.protect_operator(conn,actor_id,employee_id)
        graph.disable_user(object_id)
        graph.revoke_sessions(object_id)
        graph.replace_role_group(object_id, None)
        conn.execute("DELETE FROM employee_roles WHERE employee_id=?", (employee_id,))
        conn.execute("UPDATE assignments SET active=0 WHERE employee_id=?", (employee_id,))
        conn.execute("DELETE FROM sessions WHERE employee_id=?", (employee_id,))
        conn.execute("""
            UPDATE employees SET status='Leaver', end_date=COALESCE(end_date,?), cloud_enabled=0, cloud_role=NULL,
            admin_privilege=0, updated_at=CURRENT_TIMESTAMP WHERE employee_id=?
        """, (str(utc_today()), employee_id))
        conn.execute("INSERT OR REPLACE INTO blocked_users(employee_id, blocked_at, reason) VALUES (?,?,?)", (employee_id, datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")+"Z", reason))
        import assurance
        current=conn.execute("SELECT facility FROM employees WHERE employee_id=?",(employee_id,)).fetchone()
        assurance.sync_team(conn,employee_id,current[0])
        final_state = get_employee_state(employee_id,conn)
        audit.record_on(conn,actor_id,employee_id,"LEAVER","PASS",{"plan":plan["changes"]},final_state,correlation)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        from security_workstream.ledger import IntegrityError
        if isinstance(exc,IntegrityError):raise
        audit.record(actor_id, employee_id, "LEAVER", "FAIL", {"reason": str(exc)}, correlation_id=correlation)
        raise
    finally:
        conn.close()
    return final_state, correlation


def get_employee_state(employee_id, conn=None):
    owned = conn is None
    conn = conn or database.connect()
    employee = conn.execute("SELECT * FROM employees WHERE employee_id=?", (employee_id,)).fetchone()
    if not employee:
        if owned: conn.close()
        return None
    roles = [r["role"] for r in conn.execute("SELECT role FROM employee_roles WHERE employee_id=?", (employee_id,)).fetchall()]
    assignments = [r["resident_id"] for r in conn.execute("SELECT resident_id FROM assignments WHERE employee_id=? AND active=1", (employee_id,)).fetchall()]
    blocked = conn.execute("SELECT 1 FROM blocked_users WHERE employee_id=?", (employee_id,)).fetchone() is not None
    state = dict(employee)
    state.update({"actual_roles": roles, "active_assignments": assignments, "blocked": blocked})
    if owned: conn.close()
    return state
