from clock import utc_today
from datetime import timezone
import sqlite3
from datetime import datetime, timedelta, date
from pathlib import Path
import config


class ClosingConnection(sqlite3.Connection):
    """Protected business transactions share a writer lock with audit checkpoints."""
    integrity = True
    _ledger_lock = False
    _ledger_state = None

    def execute(self, sql, parameters=()):
        if self.integrity and sql.strip().upper() == 'BEGIN IMMEDIATE':
            from security_workstream import ledger
            ledger.LOCK.acquire()
            self._ledger_lock = True
            try:
                result = super().execute(sql, parameters)
                self._ledger_state = ledger.begin(self)
                return result
            except Exception:
                self.rollback()
                raise
        return super().execute(sql, parameters)

    def commit(self):
        from security_workstream import ledger
        prepared = None
        try:
            if self._ledger_lock:
                prepared = ledger.prepare(self, self._ledger_state)
            super().commit()
            if prepared:
                try:ledger.finish(prepared)
                except OSError as exc:
                    raise ledger.IntegrityError("Business transaction committed; signed checkpoint recovery is pending. Reload state before retrying.") from exc
        except Exception:
            super().rollback()
            raise
        finally:
            self._release()

    def _release(self):
        if self._ledger_lock:
            from security_workstream import ledger
            self._ledger_lock = False
            self._ledger_state = None
            ledger.LOCK.release()

    def rollback(self):
        try: super().rollback()
        finally: self._release()

    def close(self):
        try: super().close()
        finally: self._release()

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None: self.commit()
            else: self.rollback()
        finally: self.close()
        return False


def connect(integrity=True):
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=15, factory=ClosingConnection)
    conn.integrity = integrity
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(reset=False):
    if reset:
        config.DB_PATH.unlink(missing_ok=True)
        # A reset starts a new independent lab ledger; preserve backups first.
        for suffix in (".ledger.key",".ledger.head",".ledger.pending"):
            Path(str(config.DB_PATH)+suffix).unlink(missing_ok=True)
    conn = connect()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    import governance
    conn.executescript(governance.SCHEMA)
    import experience
    conn.executescript(experience.SCHEMA)
    from security_workstream import ledger
    conn.executescript(ledger.SCHEMA)
    import automation
    conn.executescript(automation.SCHEMA)
    import enterprise
    conn.executescript(enterprise.SCHEMA)
    import workforce_v8
    conn.executescript(workforce_v8.SCHEMA)
    conn.commit()
    fresh = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0
    if config.SEED_DEMO and conn.execute("SELECT COUNT(*) AS c FROM employees").fetchone()["c"] == 0:
        seed_db(conn)
        from demo_data import seed_extended
        seed_extended(conn)
    import assurance
    assurance.migrate(conn)
    import release_v10
    release_v10.migrate(conn)
    import release_v11
    release_v11.migrate(conn)
    import release_v12
    release_v12.migrate(conn)
    import ai_insights
    ai_insights.migrate(conn)
    if fresh and config.SEED_DEMO and config.DEMO_PROFILE == "expanded":
        from demo_v10 import seed
        seed(conn,workers=320)
        from demo_v12 import seed as seed12
        seed12(conn)
        ai_insights.seed_examples(conn)
    conn.commit()
    conn.close()


def seed_db(conn):
    today = utc_today()
    employees = [
        ("SC1001", "Sarah Khan", "sarah.khan@sunhaven.test", "Permanent", "Nurse", "Ashford Main", "Active", "MGR-001", str(today - timedelta(days=120)), None, "mock-sc1001", 1, "Nurse", 0),
        ("SC1002", "Daniel Lee", "daniel.lee@sunhaven.test", "Permanent", "Manager", "Ashford Main", "Active", "SERVICE-OWNER", str(today - timedelta(days=300)), None, "mock-sc1002", 1, "Manager", 0),
        ("SC1003", "Mia Patel", "mia.patel@sunhaven.test", "Casual", "CareWorker", "North Wing", "Active", "SC1002", str(today - timedelta(days=60)), None, "mock-sc1003", 1, "CareWorker", 0),
        ("SC1004", "Omar Rahman", "omar.rahman@sunhaven.test", "Permanent", "Auditor", "Ashford Main", "Active", "SERVICE-OWNER", str(today - timedelta(days=180)), None, "mock-sc1004", 1, "Auditor", 0),
        ("SC1005", "Ivy Chen", "ivy.chen@sunhaven.test", "Permanent", "IAMOperator", "Ashford Main", "Active", "SERVICE-OWNER", str(today - timedelta(days=210)), None, "mock-sc1005", 1, "IAMOperator", 1),
        # Deliberate seeded compliance issue for demonstration: expired agency worker still active.
        ("SC1006", "Ali Noor", "ali.noor@agency.test", "Agency", "AgencyWorker", "South Wing", "Active", "AgencySponsor-A", str(today - timedelta(days=45)), str(today - timedelta(days=2)), "mock-sc1006", 1, "AgencyWorker", 0),
        ("SC1007", "Grace Wilson", "grace.wilson@sunhaven.test", "Permanent", "Nurse", "North Wing", "Leaver", "SC1002", str(today - timedelta(days=500)), str(today - timedelta(days=10)), "mock-sc1007", 0, None, 0),
    ]
    conn.executemany("""
        INSERT INTO employees(
            employee_id, name, email, worker_type, approved_role, facility, status,
            manager_sponsor, start_date, end_date, entra_object_id, cloud_enabled,
            cloud_role, admin_privilege
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, employees)

    conn.executemany("INSERT INTO employee_roles(employee_id, role) VALUES (?,?)", [
        ("SC1001", "Nurse"), ("SC1002", "Manager"), ("SC1003", "CareWorker"),
        ("SC1004", "Auditor"), ("SC1005", "IAMOperator"), ("SC1006", "AgencyWorker")
    ])

    residents = [
        ("R001", "Resident Alpha", "Ashford Main", "Room A12"),
        ("R002", "Resident Bravo", "Ashford Main", "Room A18"),
        ("R003", "Resident Charlie", "North Wing", "Room N07"),
        ("R004", "Resident Delta", "North Wing", "Room N11"),
        ("R005", "Resident Echo", "South Wing", "Room S04"),
        ("R006", "Resident Foxtrot", "South Wing", "Room S09"),
    ]
    conn.executemany("INSERT INTO residents(resident_id, fictional_name, facility, room) VALUES (?,?,?,?)", residents)
    conn.executemany("INSERT INTO assignments(employee_id, resident_id, active) VALUES (?,?,1)", [
        ("SC1001","R001"),("SC1001","R002"),("SC1003","R003"),("SC1006","R005"),("SC1006","R006")
    ])

    # One recent review and one old review to demonstrate the workflow.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conn.execute("""
        INSERT INTO access_reviews(employee_id, reviewer_id, decision, reason, review_date, exception_expiry, remediation_status)
        VALUES (?,?,?,?,?,?,?)
    """, ("SC1001", "SC1002", "Retain", "Role and resident assignments confirmed", (now - timedelta(days=20)).isoformat(timespec="seconds"), None, "Closed"))
    conn.execute("""
        INSERT INTO access_reviews(employee_id, reviewer_id, decision, reason, review_date, exception_expiry, remediation_status)
        VALUES (?,?,?,?,?,?,?)
    """, ("SC1003", "SC1002", "Retain", "Previous review", (now - timedelta(days=130)).isoformat(timespec="seconds"), None, "Closed"))

    # Leaver is locally blocked.
    conn.execute("INSERT INTO blocked_users(employee_id, blocked_at, reason) VALUES (?,?,?)", ("SC1007", now.isoformat(timespec="seconds"), "Employment ended"))
    conn.commit()


SCHEMA = """
CREATE TABLE IF NOT EXISTS work_notes (
 note_id INTEGER PRIMARY KEY AUTOINCREMENT,
 employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 author_id TEXT NOT NULL REFERENCES employees(employee_id),
 category TEXT NOT NULL, body TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS access_requests (
 request_id INTEGER PRIMARY KEY AUTOINCREMENT,
 employee_id TEXT NOT NULL REFERENCES employees(employee_id),
 requested_role TEXT NOT NULL, facility TEXT NOT NULL,
 reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
 decision_by TEXT, decision_note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 decided_at TEXT
);
CREATE TABLE IF NOT EXISTS oauth_flows (
 state TEXT PRIMARY KEY, flow TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notes_employee ON work_notes(employee_id);
CREATE INDEX IF NOT EXISTS idx_requests_employee ON access_requests(employee_id);

CREATE TABLE IF NOT EXISTS employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    worker_type TEXT NOT NULL,
    approved_role TEXT NOT NULL,
    facility TEXT NOT NULL,
    status TEXT NOT NULL,
    manager_sponsor TEXT,
    start_date TEXT NOT NULL,
    end_date TEXT,
    entra_object_id TEXT,
    cloud_enabled INTEGER NOT NULL DEFAULT 1,
    cloud_role TEXT,
    admin_privilege INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS employee_roles (
    employee_id TEXT NOT NULL,
    role TEXT NOT NULL,
    UNIQUE(employee_id, role),
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS residents (
    resident_id TEXT PRIMARY KEY,
    fictional_name TEXT NOT NULL,
    facility TEXT NOT NULL,
    room TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    resident_id TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(employee_id, resident_id),
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE,
    FOREIGN KEY(resident_id) REFERENCES residents(resident_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS access_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    review_date TEXT NOT NULL,
    exception_expiry TEXT,
    remediation_status TEXT NOT NULL DEFAULT 'Pending',
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS blocked_users (
    employee_id TEXT PRIMARY KEY,
    blocked_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id TEXT NOT NULL,
    target_id TEXT,
    action TEXT NOT NULL,
    event_time TEXT NOT NULL,
    result TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    details TEXT,
    final_state TEXT
);

CREATE TABLE IF NOT EXISTS compliance_findings (
    finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);
"""
