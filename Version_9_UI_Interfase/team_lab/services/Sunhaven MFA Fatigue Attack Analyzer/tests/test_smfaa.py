from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
SRC = SERVICE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from detector import (  # noqa: E402
    build_event,
    detect_findings,
    export_findings,
    load_normalized_csv,
    load_rules,
    parse_timestamp,
)
from entra_csv_adapter import _classify_entra_row, load_entra_export  # noqa: E402
from sunhaven_adapter import (  # noqa: E402
    build_worker_context,
    load_identity_map,
    load_workforce,
    resolve_employee_id,
)

RULES = load_rules(SERVICE_ROOT / "config" / "detection-rules.json")


def event(event_id, employee_id, timestamp, event_type):
    return build_event(
        {
            "event_id": event_id,
            "employee_id": employee_id,
            "timestamp": timestamp,
            "event_type": event_type,
        }
    )


def test_parse_z_timestamp():
    assert parse_timestamp("2026-09-27T10:00:00Z").isoformat() == "2026-09-27T10:00:00+00:00"


def test_parse_offset_timestamp_to_utc():
    assert parse_timestamp("2026-09-27T20:00:00+10:00").isoformat() == "2026-09-27T10:00:00+00:00"


def test_invalid_timestamp_rejected():
    with pytest.raises(ValueError):
        parse_timestamp("not-a-time")


def test_missing_event_field_rejected():
    with pytest.raises(ValueError):
        build_event({"event_id": "1", "employee_id": "SC1001", "timestamp": "2026-09-27T10:00:00Z"})


def test_unsupported_event_type_rejected():
    with pytest.raises(ValueError):
        event("1", "SC1001", "2026-09-27T10:00:00Z", "PASSWORD_FAILURE")


def test_supported_event_types_are_accepted():
    for event_type in ("MFA_PROMPT", "MFA_DENIED", "MFA_SUCCESS"):
        assert event("1", "SC1001", "2026-09-27T10:00:00Z", event_type).event_type == event_type


def test_normalized_csv_is_sorted(tmp_path):
    path = tmp_path / "events.csv"
    path.write_text(
        "event_id,employee_id,timestamp,event_type\n"
        "2,SC1001,2026-09-27T10:02:00Z,MFA_SUCCESS\n"
        "1,SC1001,2026-09-27T10:01:00Z,MFA_PROMPT\n",
        encoding="utf-8",
    )
    events = load_normalized_csv(path)
    assert [item.event_id for item in events] == ["1", "2"]


def test_prompt_burst_detects_exact_threshold():
    times = ["10:00:00", "10:00:20", "10:00:40", "10:01:00", "10:01:20"]
    events = [event(str(i), "SC1001", f"2026-09-27T{t}Z", "MFA_PROMPT") for i, t in enumerate(times)]
    findings = detect_findings(events, RULES)
    assert any(item["rule"] == "PROMPT_BURST" for item in findings)


def test_prompt_burst_below_threshold_no_finding():
    times = ["10:00:00", "10:00:20", "10:00:40", "10:01:00"]
    events = [event(str(i), "SC1001", f"2026-09-27T{t}Z", "MFA_PROMPT") for i, t in enumerate(times)]
    assert not detect_findings(events, RULES)


def test_prompt_burst_outside_window_no_finding():
    times = ["10:00:00", "10:01:00", "10:02:01", "10:03:05", "10:04:10"]
    events = [event(str(i), "SC1001", f"2026-09-27T{t}Z", "MFA_PROMPT") for i, t in enumerate(times)]
    assert not any(item["rule"] == "PROMPT_BURST" for item in detect_findings(events, RULES))


def test_repeated_denial_detects_exact_threshold():
    events = [
        event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
        event("2", "SC1001", "2026-09-27T10:02:00Z", "MFA_DENIED"),
        event("3", "SC1001", "2026-09-27T10:04:00Z", "MFA_DENIED"),
    ]
    assert any(item["rule"] == "REPEATED_DENIAL" for item in detect_findings(events, RULES))


def test_repeated_denial_below_threshold_no_finding():
    events = [
        event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
        event("2", "SC1001", "2026-09-27T10:02:00Z", "MFA_DENIED"),
    ]
    assert not detect_findings(events, RULES)


def test_repeated_denial_outside_window_no_finding():
    events = [
        event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
        event("2", "SC1001", "2026-09-27T10:06:00Z", "MFA_DENIED"),
        event("3", "SC1001", "2026-09-27T10:12:00Z", "MFA_DENIED"),
    ]
    assert not detect_findings(events, RULES)


def test_denial_to_success_detects():
    events = [
        event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
        event("2", "SC1001", "2026-09-27T10:01:00Z", "MFA_DENIED"),
        event("3", "SC1001", "2026-09-27T10:02:00Z", "MFA_DENIED"),
        event("4", "SC1001", "2026-09-27T10:05:00Z", "MFA_SUCCESS"),
    ]
    assert any(item["rule"] == "DENIAL_TO_SUCCESS" for item in detect_findings(events, RULES))


def test_denial_to_success_too_late_no_transition_finding():
    events = [
        event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
        event("2", "SC1001", "2026-09-27T10:01:00Z", "MFA_DENIED"),
        event("3", "SC1001", "2026-09-27T10:02:00Z", "MFA_DENIED"),
        event("4", "SC1001", "2026-09-27T10:20:00Z", "MFA_SUCCESS"),
    ]
    assert not any(item["rule"] == "DENIAL_TO_SUCCESS" for item in detect_findings(events, RULES))


def test_success_without_denials_no_finding():
    assert not detect_findings([event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_SUCCESS")], RULES)


def test_two_workers_are_not_mixed():
    events = [
        event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
        event("2", "SC1002", "2026-09-27T10:01:00Z", "MFA_DENIED"),
        event("3", "SC1004", "2026-09-27T10:02:00Z", "MFA_DENIED"),
    ]
    assert not detect_findings(events, RULES)


def test_out_of_order_events_are_handled():
    events = [
        event("3", "SC1001", "2026-09-27T10:02:00Z", "MFA_DENIED"),
        event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
        event("2", "SC1001", "2026-09-27T10:01:00Z", "MFA_DENIED"),
    ]
    findings = detect_findings(events, RULES)
    match = next(item for item in findings if item["rule"] == "REPEATED_DENIAL")
    assert match["supporting_event_ids"] == ["1", "2", "3"]


def test_long_burst_does_not_flood_duplicate_findings():
    events = [event(str(i), "SC1001", f"2026-09-27T10:00:{i*10:02d}Z", "MFA_PROMPT") for i in range(6)]
    findings = [item for item in detect_findings(events, RULES) if item["rule"] == "PROMPT_BURST"]
    assert len(findings) == 1


def test_workforce_loader_reads_repo_style_csv(tmp_path):
    path = tmp_path / "workforce.csv"
    path.write_text(
        "employeeId,displayName,mailAlias,jobRole,facility,status,startDate,endDate\n"
        "SC1001,Mia Carter (TEST),mia.carter,CareWorker,Sydney,Active,2026-08-10,\n",
        encoding="utf-8",
    )
    workers = load_workforce(path)
    assert workers["SC1001"]["job_role"] == "CareWorker"


def test_identity_map_resolves_by_object_id():
    rows = load_identity_map(SERVICE_ROOT / "data" / "identity-map.csv")
    employee_id = resolve_employee_id("42460e61-afc4-4bf5-bad5-c0f4b5cb0c15", "", {}, rows)
    assert employee_id == "SC1008"


def test_identity_map_resolves_by_upn():
    rows = load_identity_map(SERVICE_ROOT / "data" / "identity-map.csv")
    employee_id = resolve_employee_id("", "test.careworker01@rifat011002gmail.onmicrosoft.com", {}, rows)
    assert employee_id == "SC-TST-001"


def test_workforce_alias_can_resolve_future_entra_user(tmp_path):
    path = tmp_path / "workforce.csv"
    path.write_text(
        "employeeId,displayName,mailAlias,jobRole,facility,status,startDate,endDate\n"
        "SC1001,Mia Carter (TEST),mia.carter,CareWorker,Sydney,Active,2026-08-10,\n",
        encoding="utf-8",
    )
    workers = load_workforce(path)
    assert resolve_employee_id("", "mia.carter@example.onmicrosoft.com", workers, []) == "SC1001"


def test_worker_context_enriches_findings(tmp_path):
    path = tmp_path / "workforce.csv"
    path.write_text(
        "employeeId,displayName,mailAlias,jobRole,facility,status,startDate,endDate\n"
        "SC1001,Mia Carter (TEST),mia.carter,CareWorker,Sydney,Active,2026-08-10,\n",
        encoding="utf-8",
    )
    context = build_worker_context(load_workforce(path), [])
    findings = detect_findings(
        [
            event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
            event("2", "SC1001", "2026-09-27T10:01:00Z", "MFA_DENIED"),
            event("3", "SC1001", "2026-09-27T10:02:00Z", "MFA_DENIED"),
        ],
        RULES,
        context,
    )
    assert findings[0]["display_name"] == "Mia Carter (TEST)"
    assert findings[0]["facility"] == "Sydney"


def test_entra_50074_maps_to_prompt():
    assert _classify_entra_row({"Status": "Interrupted", "SignInErrorCode": "50074"}) == "MFA_PROMPT"


def test_entra_500121_maps_to_denied():
    assert _classify_entra_row({"Status": "Failure", "SignInErrorCode": "500121"}) == "MFA_DENIED"


def test_entra_mfa_success_maps_to_success():
    row = {"Status": "Success", "AuthenticationRequirement": "Multifactor authentication", "SignInErrorCode": ""}
    assert _classify_entra_row(row) == "MFA_SUCCESS"


@pytest.mark.parametrize("code", ["50126", "50057", "50140", "50055"])
def test_non_mfa_failure_codes_are_ignored(code):
    row = {"Status": "Failure", "SignInErrorCode": code, "AuthenticationRequirement": "Single-factor authentication"}
    assert _classify_entra_row(row) is None


def test_entra_export_loader_maps_existing_style_rows(tmp_path):
    path = tmp_path / "entra.csv"
    fieldnames = [
        "EventTimeUtc", "RequestId", "CorrelationId", "UserObjectId", "DisplayName",
        "UserPrincipalName", "Status", "SignInErrorCode", "MfaResult", "MfaMethod",
        "AuthenticationRequirement"
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "EventTimeUtc": "2026-08-11T02:27:10Z",
            "RequestId": "REQ-1",
            "UserObjectId": "42460e61-afc4-4bf5-bad5-c0f4b5cb0c15",
            "UserPrincipalName": "isabella.green@rifat011002gmail.onmicrosoft.com",
            "Status": "Failure",
            "SignInErrorCode": "500121",
            "MfaMethod": "Mobile app notification",
            "AuthenticationRequirement": "Multifactor authentication",
        })
    identity = load_identity_map(SERVICE_ROOT / "data" / "identity-map.csv")
    events, stats = load_entra_export(path, {}, identity)
    assert stats["normalized"] == 1
    assert events[0].employee_id == "SC1008"
    assert events[0].event_type == "MFA_DENIED"


def test_unmapped_entra_identity_is_counted_not_crashed(tmp_path):
    path = tmp_path / "entra.csv"
    path.write_text(
        "EventTimeUtc,RequestId,UserObjectId,UserPrincipalName,Status,SignInErrorCode,AuthenticationRequirement\n"
        "2026-08-11T02:27:10Z,REQ-1,UNKNOWN,unknown@example.com,Failure,500121,Multifactor authentication\n",
        encoding="utf-8",
    )
    events, stats = load_entra_export(path, {}, [])
    assert events == []
    assert stats["unmapped"] == 1


def test_export_findings_writes_json_and_csv(tmp_path):
    findings = detect_findings(
        [
            event("1", "SC1001", "2026-09-27T10:00:00Z", "MFA_DENIED"),
            event("2", "SC1001", "2026-09-27T10:01:00Z", "MFA_DENIED"),
            event("3", "SC1001", "2026-09-27T10:02:00Z", "MFA_DENIED"),
        ],
        RULES,
    )
    json_path, csv_path = export_findings(findings, tmp_path, "test")
    assert json_path.exists() and csv_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["rule"] == "REPEATED_DENIAL"


def test_demo_dataset_produces_expected_rules():
    events = load_normalized_csv(SERVICE_ROOT / "data" / "demo-events.csv")
    findings = detect_findings(events, RULES)
    rules = [item["rule"] for item in findings]
    assert rules.count("PROMPT_BURST") == 1
    assert rules.count("REPEATED_DENIAL") == 2
    assert rules.count("DENIAL_TO_SUCCESS") == 1
    assert len(findings) == 4
