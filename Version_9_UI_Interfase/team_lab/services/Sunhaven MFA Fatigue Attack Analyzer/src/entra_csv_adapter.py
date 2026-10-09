from __future__ import annotations

import csv
from pathlib import Path

from detector import MFAEvent, build_event
from sunhaven_adapter import resolve_employee_id


PROMPT_ERROR_CODES = {"50074"}
DENIAL_ERROR_CODES = {"500121"}


def _classify_entra_row(row: dict) -> str | None:
    status = (row.get("Status") or "").strip().lower()
    error_code = str(row.get("SignInErrorCode") or "").strip()
    auth_requirement = (row.get("AuthenticationRequirement") or "").strip().lower()
    mfa_result = (row.get("MfaResult") or "").strip().lower()
    mfa_method = (row.get("MfaMethod") or "").strip().lower()

    if error_code in PROMPT_ERROR_CODES:
        return "MFA_PROMPT"
    if error_code in DENIAL_ERROR_CODES:
        return "MFA_DENIED"

    is_mfa_related = (
        "multifactor" in auth_requirement
        or "mfa" in mfa_result
        or bool(mfa_method)
    )
    if status == "success" and is_mfa_related:
        return "MFA_SUCCESS"

    return None


def load_entra_export(
    path: Path,
    workforce: dict[str, dict],
    identity_rows: list[dict],
) -> tuple[list[MFAEvent], dict]:
    events: list[MFAEvent] = []
    stats = {"rows": 0, "normalized": 0, "ignored": 0, "unmapped": 0}

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stats["rows"] += 1
            event_type = _classify_entra_row(row)
            if not event_type:
                stats["ignored"] += 1
                continue

            employee_id = resolve_employee_id(
                row.get("UserObjectId", ""),
                row.get("UserPrincipalName", ""),
                workforce,
                identity_rows,
            )
            if not employee_id:
                stats["unmapped"] += 1
                continue

            event_id = (row.get("RequestId") or row.get("CorrelationId") or "").strip()
            if not event_id:
                event_id = f"ENTRA-{stats['rows']:04d}"

            event = build_event(
                {
                    "event_id": event_id,
                    "employee_id": employee_id,
                    "timestamp": row.get("EventTimeUtc", ""),
                    "event_type": event_type,
                },
                source="ENTRA_CSV",
            )
            events.append(event)
            stats["normalized"] += 1

    events.sort(key=lambda item: item.timestamp)
    return events, stats
