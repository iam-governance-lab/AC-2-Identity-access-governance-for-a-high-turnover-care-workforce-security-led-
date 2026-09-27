"""Database functions for the Sunhaven Manager access-review extension.

This module uses the existing SQLite connection from database.py.  It stores
review campaigns, immutable decisions, background jobs and job events.  It
does not store passwords, access tokens, client secrets or certificate data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from database import get_connection


ALLOWED_WORKFORCE_ROLES = {
    "CareWorker",
    "Nurse",
    "Manager",
    "AgencyWorker",
    "Auditor",
}

ALLOWED_DECISIONS = {
    "RETAIN",
    "CHANGE",
    "REMOVE",
    "TEMPORARY_EXCEPTION",
}

MAX_EXCEPTION_DAYS = 90


ACCESS_REVIEW_SCHEMA = """
CREATE TABLE IF NOT EXISTS access_review_campaigns (
    campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_name TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('IMPORTING', 'OPEN', 'CLOSED', 'FAILED')),
    captured_utc TEXT,
    source_hash TEXT,
    created_by_object_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_by_object_id TEXT,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS access_review_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    employee_id TEXT NOT NULL,
    user_object_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    user_principal_name TEXT NOT NULL,
    account_enabled INTEGER NOT NULL CHECK (account_enabled IN (0, 1)),
    current_role TEXT NOT NULL,
    facility TEXT NOT NULL,
    governed_groups TEXT NOT NULL,
    care_app_roles TEXT NOT NULL,
    source_captured_utc TEXT NOT NULL,
    remediation_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW'
        CHECK (
            remediation_status IN (
                'PENDING_REVIEW',
                'NOT_REQUIRED',
                'EXCEPTION_ACTIVE',
                'PENDING_PLAN',
                'PLAN_READY',
                'QUEUED_APPLY',
                'RUNNING',
                'VERIFIED',
                'NO_CHANGE',
                'BLOCKED',
                'FAILED',
                'OVERDUE'
            )
        ),
    UNIQUE (campaign_id, user_object_id),
    FOREIGN KEY (campaign_id)
        REFERENCES access_review_campaigns(campaign_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS access_review_decisions (
    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    decision_version INTEGER NOT NULL,
    decision TEXT NOT NULL
        CHECK (
            decision IN (
                'RETAIN',
                'CHANGE',
                'REMOVE',
                'TEMPORARY_EXCEPTION'
            )
        ),
    target_role TEXT,
    reason TEXT NOT NULL,
    exception_expiry TEXT,
    reviewer_object_id TEXT NOT NULL,
    reviewer_display_name TEXT NOT NULL,
    reviewed_at TEXT NOT NULL,
    UNIQUE (item_id, decision_version),
    FOREIGN KEY (item_id)
        REFERENCES access_review_items(item_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS access_review_jobs (
    job_id TEXT PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    item_id INTEGER,
    decision_id INTEGER,
    parent_job_id TEXT,
    job_type TEXT NOT NULL
        CHECK (job_type IN ('INVENTORY', 'PLAN', 'APPLY')),
    status TEXT NOT NULL
        CHECK (
            status IN (
                'QUEUED',
                'RUNNING',
                'SUCCEEDED',
                'BLOCKED',
                'FAILED'
            )
        ),
    requested_by_object_id TEXT NOT NULL,
    required_approval TEXT,
    submitted_approval TEXT,
    outcome TEXT,
    write_operations INTEGER NOT NULL DEFAULT 0,
    result_json TEXT,
    error_message TEXT,
    queued_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (campaign_id)
        REFERENCES access_review_campaigns(campaign_id)
        ON DELETE CASCADE,
    FOREIGN KEY (item_id)
        REFERENCES access_review_items(item_id)
        ON DELETE CASCADE,
    FOREIGN KEY (decision_id)
        REFERENCES access_review_decisions(decision_id)
        ON DELETE CASCADE,
    FOREIGN KEY (parent_job_id)
        REFERENCES access_review_jobs(job_id)
);

CREATE TABLE IF NOT EXISTS access_review_job_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    event_time TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY (job_id)
        REFERENCES access_review_jobs(job_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_access_review_items_campaign
    ON access_review_items(campaign_id);

CREATE INDEX IF NOT EXISTS idx_access_review_decisions_item
    ON access_review_decisions(item_id, decision_version DESC);

CREATE INDEX IF NOT EXISTS idx_access_review_jobs_status
    ON access_review_jobs(status, queued_at);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_access_review_database() -> None:
    with get_connection() as connection:
        connection.executescript(ACCESS_REVIEW_SCHEMA)


def _new_job_id() -> str:
    return f"AR-{uuid.uuid4().hex[:16].upper()}"


def append_job_event(connection, job_id: str, status: str, message: str) -> None:
    connection.execute(
        """
        INSERT INTO access_review_job_events (
            job_id,
            event_time,
            status,
            message
        )
        VALUES (?, ?, ?, ?)
        """,
        (job_id, utc_now(), status, message[:1000]),
    )


def create_campaign(
    campaign_name: str,
    due_date: str,
    created_by_object_id: str,
) -> tuple[int, str]:
    """Create an IMPORTING campaign and queue its inventory job."""

    if not campaign_name.strip():
        raise ValueError("Campaign name is required.")

    parsed_due_date = date.fromisoformat(due_date)
    if parsed_due_date < date.today():
        raise ValueError("Campaign due date cannot be in the past.")

    job_id = _new_job_id()
    now = utc_now()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO access_review_campaigns (
                campaign_name,
                due_date,
                status,
                created_by_object_id,
                created_at
            )
            VALUES (?, ?, 'IMPORTING', ?, ?)
            """,
            (
                campaign_name.strip(),
                due_date,
                created_by_object_id,
                now,
            ),
        )
        campaign_id = int(cursor.lastrowid)

        connection.execute(
            """
            INSERT INTO access_review_jobs (
                job_id,
                campaign_id,
                job_type,
                status,
                requested_by_object_id,
                queued_at
            )
            VALUES (?, ?, 'INVENTORY', 'QUEUED', ?, ?)
            """,
            (job_id, campaign_id, created_by_object_id, now),
        )
        append_job_event(
            connection,
            job_id,
            "QUEUED",
            "Read-only Entra inventory job queued.",
        )

    return campaign_id, job_id


def list_campaigns() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                c.*,
                COUNT(i.item_id) AS total_items,
                SUM(
                    CASE
                        WHEN i.remediation_status = 'PENDING_REVIEW'
                        THEN 1 ELSE 0
                    END
                ) AS pending_items,
                SUM(
                    CASE
                        WHEN i.remediation_status IN (
                            'PENDING_PLAN',
                            'PLAN_READY',
                            'QUEUED_APPLY',
                            'RUNNING'
                        )
                        THEN 1 ELSE 0
                    END
                ) AS remediation_items
            FROM access_review_campaigns AS c
            LEFT JOIN access_review_items AS i
              ON i.campaign_id = c.campaign_id
            GROUP BY c.campaign_id
            ORDER BY c.campaign_id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_campaign(campaign_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM access_review_campaigns
            WHERE campaign_id = ?
            """,
            (campaign_id,),
        ).fetchone()

    return dict(row) if row else None


def list_campaign_items(campaign_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                i.*,
                d.decision,
                d.target_role,
                d.reviewer_display_name,
                d.reviewed_at
            FROM access_review_items AS i
            LEFT JOIN access_review_decisions AS d
              ON d.decision_id = (
                  SELECT d2.decision_id
                  FROM access_review_decisions AS d2
                  WHERE d2.item_id = i.item_id
                  ORDER BY d2.decision_version DESC
                  LIMIT 1
              )
            WHERE i.campaign_id = ?
            ORDER BY i.display_name, i.employee_id
            """,
            (campaign_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_review_item(item_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                i.*,
                c.campaign_name,
                c.status AS campaign_status,
                c.due_date
            FROM access_review_items AS i
            JOIN access_review_campaigns AS c
              ON c.campaign_id = i.campaign_id
            WHERE i.item_id = ?
            """,
            (item_id,),
        ).fetchone()

    return dict(row) if row else None


def get_item_decisions(item_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM access_review_decisions
            WHERE item_id = ?
            ORDER BY decision_version DESC
            """,
            (item_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def record_decision(
    *,
    item_id: int,
    decision: str,
    target_role: str | None,
    reason: str,
    exception_expiry: str | None,
    reviewer_object_id: str,
    reviewer_display_name: str,
) -> tuple[int, str | None]:
    """Append a decision and queue a plan job when remediation is needed."""

    normalized_decision = decision.strip().upper()
    normalized_reason = reason.strip()

    if normalized_decision not in ALLOWED_DECISIONS:
        raise ValueError("Unsupported access-review decision.")

    if len(normalized_reason) < 10 or len(normalized_reason) > 500:
        raise ValueError("Reason must contain between 10 and 500 characters.")

    item = get_review_item(item_id)
    if not item:
        raise ValueError("Access-review item was not found.")
    if item["campaign_status"] != "OPEN":
        raise ValueError("Only an open campaign can accept decisions.")
    if item["user_object_id"] == reviewer_object_id:
        raise PermissionError("A reviewer cannot approve their own access.")

    normalized_target_role = None
    normalized_expiry = None

    if normalized_decision == "CHANGE":
        if target_role not in ALLOWED_WORKFORCE_ROLES:
            raise ValueError("A supported target role is required for Change.")
        if target_role == item["current_role"]:
            raise ValueError("Target role must differ from the current role.")
        normalized_target_role = target_role
    elif target_role:
        raise ValueError("Target role is allowed only for Change.")

    if normalized_decision == "TEMPORARY_EXCEPTION":
        if not exception_expiry:
            raise ValueError("An expiry date is required for an exception.")
        parsed_expiry = date.fromisoformat(exception_expiry)
        if parsed_expiry <= date.today():
            raise ValueError("Exception expiry must be in the future.")
        if parsed_expiry > date.today() + timedelta(days=MAX_EXCEPTION_DAYS):
            raise ValueError(
                f"Exception expiry cannot exceed {MAX_EXCEPTION_DAYS} days."
            )
        normalized_expiry = exception_expiry
    elif exception_expiry:
        raise ValueError("Expiry date is allowed only for a temporary exception.")

    now = utc_now()
    plan_job_id = None

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        current_version = connection.execute(
            """
            SELECT COALESCE(MAX(decision_version), 0) AS current_version
            FROM access_review_decisions
            WHERE item_id = ?
            """,
            (item_id,),
        ).fetchone()["current_version"]
        next_version = int(current_version) + 1

        cursor = connection.execute(
            """
            INSERT INTO access_review_decisions (
                item_id,
                decision_version,
                decision,
                target_role,
                reason,
                exception_expiry,
                reviewer_object_id,
                reviewer_display_name,
                reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                next_version,
                normalized_decision,
                normalized_target_role,
                normalized_reason,
                normalized_expiry,
                reviewer_object_id,
                reviewer_display_name,
                now,
            ),
        )
        decision_id = int(cursor.lastrowid)

        if normalized_decision == "RETAIN":
            remediation_status = "NOT_REQUIRED"
        elif normalized_decision == "TEMPORARY_EXCEPTION":
            remediation_status = "EXCEPTION_ACTIVE"
        else:
            remediation_status = "PENDING_PLAN"
            plan_job_id = _new_job_id()
            connection.execute(
                """
                INSERT INTO access_review_jobs (
                    job_id,
                    campaign_id,
                    item_id,
                    decision_id,
                    job_type,
                    status,
                    requested_by_object_id,
                    queued_at
                )
                VALUES (?, ?, ?, ?, 'PLAN', 'QUEUED', ?, ?)
                """,
                (
                    plan_job_id,
                    item["campaign_id"],
                    item_id,
                    decision_id,
                    reviewer_object_id,
                    now,
                ),
            )
            append_job_event(
                connection,
                plan_job_id,
                "QUEUED",
                "No-write remediation plan queued.",
            )

        connection.execute(
            """
            UPDATE access_review_items
            SET remediation_status = ?
            WHERE item_id = ?
            """,
            (remediation_status, item_id),
        )

    return decision_id, plan_job_id


def get_job(job_id: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                j.*,
                c.campaign_name,
                i.employee_id,
                i.display_name,
                i.user_object_id,
                i.current_role,
                i.facility,
                d.decision,
                d.target_role,
                d.reason,
                d.exception_expiry
            FROM access_review_jobs AS j
            JOIN access_review_campaigns AS c
              ON c.campaign_id = j.campaign_id
            LEFT JOIN access_review_items AS i
              ON i.item_id = j.item_id
            LEFT JOIN access_review_decisions AS d
              ON d.decision_id = j.decision_id
            WHERE j.job_id = ?
            """,
            (job_id,),
        ).fetchone()

    result = dict(row) if row else None
    if result and result.get("result_json"):
        result["result"] = json.loads(result["result_json"])
    return result


def get_job_events(job_id: str) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM access_review_job_events
            WHERE job_id = ?
            ORDER BY event_id
            """,
            (job_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def queue_apply_job(
    *,
    plan_job_id: str,
    approval_text: str,
    requested_by_object_id: str,
) -> str:
    """Queue Apply only after an exact, successful no-write plan."""

    plan_job = get_job(plan_job_id)
    if not plan_job:
        raise ValueError("Plan job was not found.")
    if plan_job["job_type"] != "PLAN" or plan_job["status"] != "SUCCEEDED":
        raise ValueError("A successful plan is required before Apply.")
    if plan_job.get("outcome") != "PLANNED":
        raise ValueError("The plan did not reach the PLANNED outcome.")
    if not plan_job.get("required_approval"):
        raise ValueError("The plan did not produce approval text.")
    if approval_text != plan_job["required_approval"]:
        raise ValueError("Approval text did not match exactly.")

    apply_job_id = _new_job_id()
    now = utc_now()

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        duplicate = connection.execute(
            """
            SELECT job_id
            FROM access_review_jobs
            WHERE parent_job_id = ?
              AND job_type = 'APPLY'
              AND status IN ('QUEUED', 'RUNNING', 'SUCCEEDED')
            """,
            (plan_job_id,),
        ).fetchone()
        if duplicate:
            raise ValueError("An Apply job already exists for this plan.")

        connection.execute(
            """
            INSERT INTO access_review_jobs (
                job_id,
                campaign_id,
                item_id,
                decision_id,
                parent_job_id,
                job_type,
                status,
                requested_by_object_id,
                submitted_approval,
                queued_at
            )
            VALUES (?, ?, ?, ?, ?, 'APPLY', 'QUEUED', ?, ?, ?)
            """,
            (
                apply_job_id,
                plan_job["campaign_id"],
                plan_job["item_id"],
                plan_job["decision_id"],
                plan_job_id,
                requested_by_object_id,
                approval_text,
                now,
            ),
        )
        connection.execute(
            """
            UPDATE access_review_items
            SET remediation_status = 'QUEUED_APPLY'
            WHERE item_id = ?
            """,
            (plan_job["item_id"],),
        )
        append_job_event(
            connection,
            apply_job_id,
            "QUEUED",
            "Approved remediation job queued.",
        )

    return apply_job_id


def claim_next_job() -> dict | None:
    """Atomically claim the oldest queued job for one worker process."""

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """
            SELECT job_id
            FROM access_review_jobs
            WHERE status = 'QUEUED'
            ORDER BY queued_at, job_id
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return None

        job_id = row["job_id"]
        changed = connection.execute(
            """
            UPDATE access_review_jobs
            SET status = 'RUNNING',
                started_at = ?
            WHERE job_id = ?
              AND status = 'QUEUED'
            """,
            (utc_now(), job_id),
        ).rowcount
        if changed != 1:
            return None

        job = connection.execute(
            """
            SELECT
                j.*,
                i.employee_id,
                i.display_name,
                i.user_object_id,
                i.current_role,
                i.facility,
                i.governed_groups,
                i.care_app_roles,
                d.decision,
                d.target_role,
                d.reason,
                d.exception_expiry
            FROM access_review_jobs AS j
            LEFT JOIN access_review_items AS i
              ON i.item_id = j.item_id
            LEFT JOIN access_review_decisions AS d
              ON d.decision_id = j.decision_id
            WHERE j.job_id = ?
            """,
            (job_id,),
        ).fetchone()
        append_job_event(connection, job_id, "RUNNING", "Worker claimed job.")
        if job["item_id"]:
            connection.execute(
                """
                UPDATE access_review_items
                SET remediation_status = 'RUNNING'
                WHERE item_id = ?
                """,
                (job["item_id"],),
            )

    return dict(job)


def finish_job(
    *,
    job_id: str,
    status: str,
    outcome: str,
    write_operations: int,
    result: dict | None,
    error_message: str | None = None,
    required_approval: str | None = None,
) -> None:
    if status not in {"SUCCEEDED", "BLOCKED", "FAILED"}:
        raise ValueError("Invalid terminal job status.")

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        job = connection.execute(
            """
            SELECT item_id, job_type, campaign_id
            FROM access_review_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()
        if not job:
            raise ValueError("Job was not found while completing it.")

        connection.execute(
            """
            UPDATE access_review_jobs
            SET status = ?,
                outcome = ?,
                write_operations = ?,
                result_json = ?,
                error_message = ?,
                required_approval = COALESCE(?, required_approval),
                completed_at = ?
            WHERE job_id = ?
            """,
            (
                status,
                outcome,
                int(write_operations),
                json.dumps(result or {}, sort_keys=True),
                error_message,
                required_approval,
                utc_now(),
                job_id,
            ),
        )
        append_job_event(
            connection,
            job_id,
            status,
            error_message or f"Job completed with outcome {outcome}.",
        )

        if job["job_type"] == "INVENTORY":
            campaign_status = "OPEN" if status == "SUCCEEDED" else "FAILED"
            connection.execute(
                """
                UPDATE access_review_campaigns
                SET status = ?
                WHERE campaign_id = ?
                """,
                (campaign_status, job["campaign_id"]),
            )
        elif job["item_id"]:
            if job["job_type"] == "PLAN" and status == "SUCCEEDED":
                item_status = "PLAN_READY"
            elif status == "BLOCKED":
                item_status = "BLOCKED"
            elif status == "FAILED":
                item_status = "FAILED"
            elif outcome == "NO CHANGE":
                item_status = "NO_CHANGE"
            elif job["job_type"] == "APPLY" and status == "SUCCEEDED":
                item_status = "VERIFIED"
            else:
                item_status = "FAILED"

            connection.execute(
                """
                UPDATE access_review_items
                SET remediation_status = ?
                WHERE item_id = ?
                """,
                (item_status, job["item_id"]),
            )


def import_inventory_csv(campaign_id: int, csv_path: Path) -> dict:
    """Validate and transactionally import a read-only Graph inventory."""

    csv_bytes = csv_path.read_bytes()
    source_hash = hashlib.sha256(csv_bytes).hexdigest()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    required_columns = {
        "CapturedUtc",
        "EmployeeId",
        "DisplayName",
        "UserPrincipalName",
        "ObjectId",
        "AccountEnabled",
        "JobRole",
        "Facility",
        "GovernedGroups",
        "CareAppRoles",
        "WriteOperationsExecuted",
    }

    if not rows:
        raise ValueError("The inventory CSV contained no access holders.")
    if not required_columns.issubset(rows[0]):
        missing = sorted(required_columns.difference(rows[0]))
        raise ValueError(f"Inventory CSV is missing columns: {missing}")

    object_ids = [row["ObjectId"].strip() for row in rows]
    if len(object_ids) != len(set(object_ids)):
        raise ValueError("Inventory contains duplicate Object IDs.")

    captured_values = {row["CapturedUtc"].strip() for row in rows}
    if len(captured_values) != 1:
        raise ValueError("Inventory rows do not share one capture timestamp.")
    captured_utc = captured_values.pop()
    prepared_rows = []
    inferred_role_count = 0
    placeholder_employee_id_count = 0
    missing_facility_count = 0

    for row in rows:
        if row["WriteOperationsExecuted"].strip() != "0":
            raise ValueError("Inventory export did not report zero writes.")

        object_id = row["ObjectId"].strip()
        if not object_id:
            raise ValueError("Every inventory row requires an Entra Object ID.")

        current_role = row["JobRole"].strip()

        if current_role not in ALLOWED_WORKFORCE_ROLES:
            app_roles = {
                role.strip()
                for role in row["CareAppRoles"].split(";")
                if role.strip() in ALLOWED_WORKFORCE_ROLES
            }

            if len(app_roles) == 1:
                current_role = next(iter(app_roles))
                inferred_role_count += 1
            else:
                raise ValueError(
                    "Unable to determine one supported current role for "
                    f"Object ID {object_id}."
                )

        employee_id = row["EmployeeId"].strip()
        if not employee_id or employee_id == "<missing>":
            employee_id = f"MISSING-{object_id[:8].upper()}"
            placeholder_employee_id_count += 1

        facility = row["Facility"].strip()
        if not facility or facility == "<missing>":
            facility = "Unassigned"
            missing_facility_count += 1

        prepared_rows.append(
            (
                campaign_id,
                employee_id,
                object_id,
                row["DisplayName"].strip(),
                row["UserPrincipalName"].strip(),
                1 if row["AccountEnabled"].strip().lower() == "true" else 0,
                current_role,
                facility,
                row["GovernedGroups"].strip(),
                row["CareAppRoles"].strip(),
                captured_utc,
            )
        )

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        campaign = connection.execute(
            """
            SELECT status
            FROM access_review_campaigns
            WHERE campaign_id = ?
            """,
            (campaign_id,),
        ).fetchone()
        if not campaign or campaign["status"] != "IMPORTING":
            raise ValueError("Campaign is not ready for an inventory import.")

        connection.executemany(
            """
            INSERT INTO access_review_items (
                campaign_id,
                employee_id,
                user_object_id,
                display_name,
                user_principal_name,
                account_enabled,
                current_role,
                facility,
                governed_groups,
                care_app_roles,
                source_captured_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            prepared_rows,
        )
        connection.execute(
            """
            UPDATE access_review_campaigns
            SET captured_utc = ?,
                source_hash = ?
            WHERE campaign_id = ?
            """,
            (captured_utc, source_hash, campaign_id),
        )

    return {
        "captured_utc": captured_utc,
        "source_hash": source_hash,
        "item_count": len(prepared_rows),
        "write_operations": 0,
    }


def close_campaign(campaign_id: int, closed_by_object_id: str) -> None:
    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        campaign = connection.execute(
            """
            SELECT status
            FROM access_review_campaigns
            WHERE campaign_id = ?
            """,
            (campaign_id,),
        ).fetchone()
        if not campaign or campaign["status"] != "OPEN":
            raise ValueError("Only an open campaign can be closed.")

        unresolved = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM access_review_items
            WHERE campaign_id = ?
              AND remediation_status NOT IN (
                  'NOT_REQUIRED',
                  'EXCEPTION_ACTIVE',
                  'VERIFIED',
                  'NO_CHANGE'
              )
            """,
            (campaign_id,),
        ).fetchone()["total"]
        if unresolved:
            raise ValueError(
                f"Campaign has {unresolved} unresolved review item(s)."
            )

        connection.execute(
            """
            UPDATE access_review_campaigns
            SET status = 'CLOSED',
                closed_by_object_id = ?,
                closed_at = ?
            WHERE campaign_id = ?
            """,
            (closed_by_object_id, utc_now(), campaign_id),
        )


def mark_expired_exceptions() -> int:
    """Mark expired temporary exceptions without changing Entra access."""

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE access_review_items
            SET remediation_status = 'OVERDUE'
            WHERE item_id IN (
                SELECT d.item_id
                FROM access_review_decisions AS d
                WHERE d.decision = 'TEMPORARY_EXCEPTION'
                  AND d.exception_expiry < date('now')
                  AND d.decision_version = (
                      SELECT MAX(d2.decision_version)
                      FROM access_review_decisions AS d2
                      WHERE d2.item_id = d.item_id
                  )
            )
              AND remediation_status = 'EXCEPTION_ACTIVE'
            """
        )
    return int(result.rowcount)
