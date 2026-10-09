from clock import utc_today
from datetime import timezone
from datetime import date, datetime, timedelta
import database
import config


def run_checks(store=True, actor=None):
    conn = database.connect()
    if store:
        conn.execute("BEGIN IMMEDIATE")
        if actor:
            import governance
            governance.require(conn,actor,{"Manager","Auditor","IAMOperator"})
    employees = conn.execute("SELECT * FROM employees ORDER BY employee_id").fetchall()
    findings = []
    today = utc_today()

    roles_by={}
    for r in conn.execute('SELECT employee_id,role FROM employee_roles'):roles_by.setdefault(r[0],[]).append(r[1])
    assignments_by=dict(conn.execute('SELECT employee_id,COUNT(*) FROM assignments WHERE active=1 GROUP BY employee_id'))
    latest_reviews=dict(conn.execute('SELECT employee_id,MAX(review_date) FROM access_reviews GROUP BY employee_id'))
    for e in employees:
        eid = e["employee_id"]
        roles=roles_by.get(eid,[])
        assignment_count=assignments_by.get(eid,0)

        if e["status"] in ("Leaver", "Inactive", "Suspended") and e["cloud_enabled"]:
            findings.append(_f(eid, "C01", "Critical", "Enabled leaver/inactive identity", "Cloud identity is still enabled after employment/access ended."))
        if e["worker_type"] == "Agency" and e["end_date"]:
            try:
                if date.fromisoformat(e["end_date"]) < today and e["cloud_enabled"]:
                    findings.append(_f(eid, "C02", "High", "Expired agency access", "Agency end date has passed but cloud access remains enabled."))
            except ValueError:
                findings.append(_f(eid,"C03","High","Invalid agency record","Agency end date is invalid; access is denied until corrected."))
        if e["worker_type"] == "Agency" and (not e["manager_sponsor"] or not e["end_date"]):
            findings.append(_f(eid, "C03", "High", "Incomplete agency record", "Agency worker must have a sponsor and end date."))
        if e["cloud_role"] and e["cloud_role"] != e["approved_role"]:
            findings.append(_f(eid, "C04", "High", "Role mismatch", f"Approved role is {e['approved_role']} but cloud role is {e['cloud_role']}."))
        normal = [r for r in roles if r in config.NORMAL_CARE_ROLES]
        if len(normal) > 1:
            findings.append(_f(eid, "C05", "High", "Conflicting normal roles", "Worker has more than one normal care role without an approved exception."))
        if e["status"] in ("Leaver", "Inactive", "Suspended") and (roles or assignment_count > 0):
            findings.append(_f(eid, "C06", "High", "Disabled worker still has access", "Governed roles or resident assignments remain after access should be disabled."))
        if e["approved_role"] != "IAMOperator" and e["admin_privilege"]:
            findings.append(_f(eid, "C07", "Critical", "Unexpected administrative privilege", "A normal worker has IAM/admin privilege."))

        if e["status"] == "Active":
            latest = {"review_date":latest_reviews[eid]} if eid in latest_reviews else None
            start = None
            try: start = date.fromisoformat(e["start_date"])
            except Exception: pass
            if start and (today - start).days > 90:
                overdue = not latest
                if latest:
                    try:
                        reviewed = datetime.fromisoformat(latest["review_date"].replace("Z", "")).date()
                        overdue = (today - reviewed).days > 90
                    except Exception:
                        overdue = True
                if overdue:
                    findings.append(_f(eid, "C08", "Medium", "Access review overdue", "No current access review was found within the expected 90-day lab period."))

    if store:
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
        current={(f['employee_id'],f['rule_id']):f for f in findings}
        existing={}
        for old in conn.execute("SELECT * FROM compliance_findings WHERE status='Open' ORDER BY finding_id").fetchall():
            key=(old['employee_id'],old['rule_id'])
            if key not in current or key in existing:
                conn.execute("UPDATE compliance_findings SET status='Resolved',resolved_at=? WHERE finding_id=?",(now,old['finding_id']))
            else:existing[key]=old['finding_id']
        for key,f in current.items():
            if key in existing:
                conn.execute('UPDATE compliance_findings SET severity=?,details=? WHERE finding_id=?',(f['severity'],f['details'],existing[key]))
            else:
                conn.execute("INSERT INTO compliance_findings(employee_id,rule_id,severity,status,details,detected_at) VALUES (?,?,?,'Open',?,?)",(f['employee_id'],f['rule_id'],f['severity'],f['details'],now))
        import audit
        audit.record_on(conn,actor or "SYSTEM",None,"COMPLIANCE_SCAN","PASS",{"finding_count":len(findings)})
        conn.commit()
    conn.close()
    return findings


def _f(employee_id, rule_id, severity, title, details):
    return {"employee_id": employee_id, "rule_id": rule_id, "severity": severity, "title": title, "details": details}
