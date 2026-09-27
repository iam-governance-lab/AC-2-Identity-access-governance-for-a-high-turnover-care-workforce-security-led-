from __future__ import annotations

import csv
from pathlib import Path


def find_repo_root(start: Path) -> Path | None:
    start = Path(start).resolve()
    for candidate in (start, *start.parents):
        if (candidate / "data" / "workforce.csv").exists() and (candidate / "evidence").exists():
            return candidate
    return None


def load_workforce(path: Path | None) -> dict[str, dict]:
    if not path or not Path(path).exists():
        return {}

    workers: dict[str, dict] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            employee_id = (row.get("employeeId") or "").strip()
            if not employee_id:
                continue
            workers[employee_id] = {
                "employee_id": employee_id,
                "display_name": (row.get("displayName") or "").strip(),
                "mail_alias": (row.get("mailAlias") or "").strip().lower(),
                "job_role": (row.get("jobRole") or "").strip(),
                "facility": (row.get("facility") or "").strip(),
                "status": (row.get("status") or "").strip(),
            }
    return workers


def load_identity_map(path: Path | None) -> list[dict]:
    if not path or not Path(path).exists():
        return []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def build_worker_context(workforce: dict[str, dict], identity_rows: list[dict]) -> dict[str, dict]:
    context = {employee_id: dict(value) for employee_id, value in workforce.items()}

    for row in identity_rows:
        employee_id = (row.get("employee_id") or "").strip()
        if not employee_id:
            continue
        existing = context.setdefault(employee_id, {"employee_id": employee_id})
        for source, target in (
            ("display_name", "display_name"),
            ("job_role", "job_role"),
            ("facility", "facility"),
            ("status", "status"),
        ):
            if not existing.get(target) and (row.get(source) or "").strip():
                existing[target] = row[source].strip()
    return context


def resolve_employee_id(
    user_object_id: str,
    user_principal_name: str,
    workforce: dict[str, dict],
    identity_rows: list[dict],
) -> str | None:
    object_id = (user_object_id or "").strip().lower()
    upn = (user_principal_name or "").strip().lower()

    for row in identity_rows:
        if object_id and object_id == (row.get("user_object_id") or "").strip().lower():
            return (row.get("employee_id") or "").strip() or None
        if upn and upn == (row.get("user_principal_name") or "").strip().lower():
            return (row.get("employee_id") or "").strip() or None

    if upn and "@" in upn:
        local_part = upn.split("@", 1)[0]
        for employee_id, worker in workforce.items():
            if local_part == worker.get("mail_alias", ""):
                return employee_id

    return None
