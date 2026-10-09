from datetime import datetime, timezone
from pathlib import Path
import sqlite3


APP_DIRECTORY = Path(__file__).resolve().parent
INSTANCE_DIRECTORY = APP_DIRECTORY / "instance"
DATABASE_PATH = INSTANCE_DIRECTORY / "sunhaven.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS residents (
    resident_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
        CHECK (display_name LIKE '%TEST%'),
    facility TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id TEXT NOT NULL,
    user_object_id TEXT NOT NULL,
    assignment_role TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1)),
    UNIQUE (resident_id, user_object_id),
    FOREIGN KEY (resident_id)
        REFERENCES residents(resident_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS care_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id TEXT NOT NULL,
    note_text TEXT NOT NULL,
    created_by_object_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (resident_id)
        REFERENCES residents(resident_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_object_id TEXT NOT NULL,
    action TEXT NOT NULL,
    object_id TEXT,
    event_time TEXT NOT NULL,
    result TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blocked_users (
    user_object_id TEXT PRIMARY KEY,
    blocked_at TEXT NOT NULL,
    blocked_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
        CHECK (active IN (0, 1)),
    unblocked_at TEXT,
    unblocked_by TEXT
);
"""


TEST_RESIDENTS = [
    (
        "RES-TEST-001",
        "Alex Morgan TEST",
        "Sunhaven North TEST Facility",
        1,
    ),
    (
        "RES-TEST-002",
        "Bailey Taylor TEST",
        "Sunhaven North TEST Facility",
        1,
    ),
    (
        "RES-TEST-003",
        "Casey Jordan TEST",
        "Sunhaven Central TEST Facility",
        1,
    ),
    (
        "RES-TEST-004",
        "Drew Parker TEST",
        "Sunhaven Central TEST Facility",
        1,
    ),
    (
        "RES-TEST-005",
        "Ellis River TEST",
        "Sunhaven South TEST Facility",
        1,
    ),
]


def get_connection():
    """Open a database connection with useful safety settings."""

    INSTANCE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Create the tables and insert five fictional residents."""

    with get_connection() as connection:
        connection.executescript(SCHEMA)

        connection.executemany(
            """
            INSERT OR IGNORE INTO residents (
                resident_id,
                display_name,
                facility,
                active
            )
            VALUES (?, ?, ?, ?)
            """,
            TEST_RESIDENTS,
        )


def utc_now():
    """Return the current time in an unambiguous UTC format."""

    return datetime.now(timezone.utc).isoformat()


def block_user(
    user_object_id,
    blocked_by="LOCAL-IAM-ADMIN",
    reason="Leaver access removal",
):
    """Block an Entra Object ID from protected application routes."""

    if not user_object_id:
        raise ValueError("The Entra Object ID cannot be blank.")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO blocked_users (
                user_object_id,
                blocked_at,
                blocked_by,
                reason,
                active,
                unblocked_at,
                unblocked_by
            )
            VALUES (?, ?, ?, ?, 1, NULL, NULL)
            ON CONFLICT (user_object_id)
            DO UPDATE SET
                blocked_at = excluded.blocked_at,
                blocked_by = excluded.blocked_by,
                reason = excluded.reason,
                active = 1,
                unblocked_at = NULL,
                unblocked_by = NULL
            """,
            (
                user_object_id,
                utc_now(),
                blocked_by,
                reason,
            ),
        )

        connection.execute(
            """
            INSERT INTO app_audit_events (
                user_object_id,
                action,
                object_id,
                event_time,
                result
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                blocked_by,
                "BLOCK_LOCAL_APP_USER",
                user_object_id,
                utc_now(),
                "ALLOW",
            ),
        )


def unblock_user(
    user_object_id,
    unblocked_by="LOCAL-IAM-ADMIN",
):
    """Remove a lab application block from an Entra Object ID."""

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE blocked_users
            SET active = 0,
                unblocked_at = ?,
                unblocked_by = ?
            WHERE user_object_id = ?
              AND active = 1
            """,
            (
                utc_now(),
                unblocked_by,
                user_object_id,
            ),
        )

        if result.rowcount == 0:
            return False

        connection.execute(
            """
            INSERT INTO app_audit_events (
                user_object_id,
                action,
                object_id,
                event_time,
                result
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                unblocked_by,
                "UNBLOCK_LOCAL_APP_USER",
                user_object_id,
                utc_now(),
                "ALLOW",
            ),
        )

    return True


def get_blocked_user(user_object_id):
    """Return the block record for one Object ID, if it exists."""

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                user_object_id,
                blocked_at,
                blocked_by,
                reason,
                active,
                unblocked_at,
                unblocked_by
            FROM blocked_users
            WHERE user_object_id = ?
            """,
            (user_object_id,),
        ).fetchone()

    return dict(row) if row else None


def is_user_blocked(user_object_id):
    """Return True only when the Object ID has an active block."""

    record = get_blocked_user(user_object_id)

    return bool(record and record["active"] == 1)


def print_validation_report():
    """Print safe database information for project evidence."""

    with get_connection() as connection:
        table_names = [
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        ]

        resident_count = connection.execute(
            "SELECT COUNT(*) AS total FROM residents"
        ).fetchone()["total"]

        assignment_count = connection.execute(
            "SELECT COUNT(*) AS total FROM assignments"
        ).fetchone()["total"]

        care_note_count = connection.execute(
            "SELECT COUNT(*) AS total FROM care_notes"
        ).fetchone()["total"]

        audit_count = connection.execute(
            "SELECT COUNT(*) AS total FROM app_audit_events"
        ).fetchone()["total"]

        invalid_name_count = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM residents
            WHERE display_name NOT LIKE '%TEST%'
            """
        ).fetchone()["total"]

    print("Sunhaven TEST database validation")
    print("---------------------------------")
    print(f"Database location: {DATABASE_PATH}")
    print(f"Application tables: {', '.join(table_names)}")
    print(f"Residents: {resident_count}")
    print(f"Assignments: {assignment_count}")
    print(f"Care notes: {care_note_count}")
    print(f"Audit events: {audit_count}")
    print(f"All resident names contain TEST: {invalid_name_count == 0}")


if __name__ == "__main__":
    initialize_database()
    print_validation_report()