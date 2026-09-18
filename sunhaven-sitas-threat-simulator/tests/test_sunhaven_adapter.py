import csv
import json
from pathlib import Path

import pytest

from sunhaven_adapter import (
    SunhavenIntegrationError,
    build_integrated_leaver_comparison,
    build_leaver_environment,
    build_rbac_matrix,
    build_sunhaven_snapshot,
    load_worker_state_csv,
    load_workforce,
    resolve_sunhaven_root,
    validate_sunhaven_root,
)
from sunhaven_report_generator import (
    write_integration_html,
    write_integration_json,
    write_rbac_matrix_csv,
)


def _write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _make_sunhaven_root(tmp_path):
    root = tmp_path / "core"
    (root / "data").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "automation").mkdir(parents=True)
    (root / "app").mkdir(parents=True)

    _write_csv(
        root / "data/workforce.csv",
        [
            "employeeId",
            "displayName",
            "mailAlias",
            "jobRole",
            "facility",
            "status",
            "startDate",
            "endDate",
        ],
        [
            {
                "employeeId": "SC1001",
                "displayName": "Mia Carter (TEST)",
                "mailAlias": "mia.carter",
                "jobRole": "CareWorker",
                "facility": "Sydney",
                "status": "Active",
                "startDate": "2026-08-10",
                "endDate": "",
            },
            {
                "employeeId": "SC1006",
                "displayName": "Ethan Khan (TEST)",
                "mailAlias": "ethan.khan",
                "jobRole": "CareWorker",
                "facility": "Sydney",
                "status": "Leaving",
                "startDate": "2026-07-01",
                "endDate": "2026-08-05",
            },
        ],
    )

    _write_csv(
        root / "config/route-role-map.csv",
        ["Route", "Purpose", "AllowedRoles", "UnauthorizedResult"],
        [
            {
                "Route": "/residents",
                "Purpose": "List permitted TEST residents",
                "AllowedRoles": "CareWorker|Nurse|Manager|AgencyWorker",
                "UnauthorizedResult": "HTTP 403",
            },
            {
                "Route": "/clinical",
                "Purpose": "Open clinical workspace",
                "AllowedRoles": "Nurse|Manager",
                "UnauthorizedResult": "HTTP 403",
            },
            {
                "Route": "/review",
                "Purpose": "Open manager review workspace",
                "AllowedRoles": "Manager",
                "UnauthorizedResult": "HTTP 403",
            },
        ],
    )

    (root / "config/app-role-ids.json").write_text(
        json.dumps(
            {
                "CareWorker": "role-1",
                "Nurse": "role-2",
                "Manager": "role-3",
                "AgencyWorker": "role-4",
                "Auditor": "role-5",
            }
        ),
        encoding="utf-8",
    )

    (root / "config/group-object-ids.json").write_text(
        json.dumps(
            {
                "SG-SC-CareWorkers": "group-1",
                "SG-SC-Nurses": "group-2",
                "SG-SC-Managers": "group-3",
                "SG-SC-AgencyWorkers": "group-4",
                "SG-SC-Auditors": "group-5",
            }
        ),
        encoding="utf-8",
    )

    for relative in [
        "automation/Invoke-SunhavenJoiner.ps1",
        "automation/Invoke-SunhavenMover.ps1",
        "automation/Invoke-SunhavenLeaver.ps1",
        "automation/Export-SunhavenWorkerState.ps1",
        "app/app.py",
    ]:
        path = root / relative
        path.write_text("# fixture", encoding="utf-8")

    return root


def _make_worker_state(
    tmp_path,
    account_enabled=True,
    employee_id="SC1006",
):
    path = tmp_path / "worker-state.csv"

    _write_csv(
        path,
        [
            "CapturedUtc",
            "EmployeeId",
            "DisplayName",
            "UserPrincipalName",
            "ObjectId",
            "AccountEnabled",
            "JobTitle",
            "Department",
            "Facility",
            "GovernedGroups",
            "GovernedGroupCount",
            "CareApplication",
            "CareApplicationServiceId",
            "CareAppRoles",
            "CareAppRoleAssignmentCount",
            "WriteOperationsExecuted",
        ],
        [
            {
                "CapturedUtc": "2026-08-13T00:00:00Z",
                "EmployeeId": employee_id,
                "DisplayName": "Test Worker",
                "UserPrincipalName": "test@example.invalid",
                "ObjectId": "object-1",
                "AccountEnabled": str(account_enabled),
                "JobTitle": "CareWorker",
                "Department": "Sydney",
                "Facility": "Sydney",
                "GovernedGroups": (
                    "SG-SC-CareWorkers"
                    if account_enabled
                    else "<none>"
                ),
                "GovernedGroupCount": (
                    "1"
                    if account_enabled
                    else "0"
                ),
                "CareApplication": "Sunhaven Care Portal - LAB",
                "CareApplicationServiceId": "sp-1",
                "CareAppRoles": (
                    "CareWorker"
                    if account_enabled
                    else "<none>"
                ),
                "CareAppRoleAssignmentCount": (
                    "1"
                    if account_enabled
                    else "0"
                ),
                "WriteOperationsExecuted": "0",
            }
        ],
    )

    return path


def _make_leaver_result(
    tmp_path,
    complete=True,
    employee_id="SC1006",
):
    path = tmp_path / "leaver-result.json"

    payload = {
        "EmployeeId": employee_id,
        "AccountDisabled": complete,
        "GovernedGroupsRemaining": (
            []
            if complete
            else ["SG-SC-CareWorkers"]
        ),
        "CareAppRolesRemaining": (
            0
            if complete
            else 1
        ),
        "LocalAppBlocked": complete,
        "SessionsRevoked": complete,
    }

    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    return path


def test_validate_sunhaven_root_accepts_valid_fixture(tmp_path):
    root = _make_sunhaven_root(tmp_path)

    assert validate_sunhaven_root(root) == root.resolve()


def test_validate_sunhaven_root_rejects_missing_required_file(
    tmp_path,
):
    root = _make_sunhaven_root(tmp_path)

    (root / "config/route-role-map.csv").unlink()

    with pytest.raises(SunhavenIntegrationError):
        validate_sunhaven_root(root)


def test_resolve_sunhaven_root_detects_parent_of_sitas(
    tmp_path,
):
    root = _make_sunhaven_root(tmp_path)

    sitas_root = root / "sunhaven-sitas-threat-simulator"
    sitas_root.mkdir()

    assert (
        resolve_sunhaven_root(project_root=sitas_root)
        == root.resolve()
    )


def test_workforce_loads_and_contains_leaver(tmp_path):
    root = _make_sunhaven_root(tmp_path)

    rows = load_workforce(root)

    assert len(rows) == 2
    assert rows[1]["employeeId"] == "SC1006"
    assert rows[1]["status"] == "Leaving"


def test_duplicate_workforce_employee_id_is_rejected(
    tmp_path,
):
    root = _make_sunhaven_root(tmp_path)

    workforce = root / "data/workforce.csv"

    with workforce.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            "SC1006,Duplicate,dup,CareWorker,"
            "Sydney,Leaving,2026-07-01,2026-08-05\n"
        )

    with pytest.raises(SunhavenIntegrationError):
        load_workforce(root)


def test_snapshot_maps_actual_project_sources(tmp_path):
    root = _make_sunhaven_root(tmp_path)

    snapshot = build_sunhaven_snapshot(root)

    assert (
        snapshot["mode"]
        == "READ_ONLY_PROJECT_SNAPSHOT"
    )

    assert snapshot["workforce"]["recordCount"] == 2

    assert (
        snapshot["workforce"]["leavingWorkers"][0][
            "employeeId"
        ]
        == "SC1006"
    )

    assert (
        snapshot["sourceInventory"][
            "leaverAutomation"
        ]["present"]
        is True
    )

    assert snapshot["findings"] == []


def test_rbac_matrix_denies_careworker_from_clinical(
    tmp_path,
):
    root = _make_sunhaven_root(tmp_path)

    snapshot = build_sunhaven_snapshot(root)

    match = next(
        row
        for row in snapshot["authorization"]["rbacMatrix"]
        if (
            row["role"] == "CareWorker"
            and row["route"] == "/clinical"
        )
    )

    assert match["allowed"] is False
    assert match["unauthorizedResult"] == "HTTP 403"


def test_rbac_matrix_allows_nurse_to_clinical(
    tmp_path,
):
    root = _make_sunhaven_root(tmp_path)

    snapshot = build_sunhaven_snapshot(root)

    match = next(
        row
        for row in snapshot["authorization"]["rbacMatrix"]
        if (
            row["role"] == "Nurse"
            and row["route"] == "/clinical"
        )
    )

    assert match["allowed"] is True


def test_build_rbac_matrix_is_deterministic():
    routes = [
        {
            "route": "/x",
            "purpose": "X",
            "allowedRoles": ["Nurse"],
            "unauthorizedResult": "HTTP 403",
        }
    ]

    first = build_rbac_matrix(
        routes,
        ["Nurse", "CareWorker"],
    )

    second = build_rbac_matrix(
        routes,
        ["Nurse", "CareWorker"],
    )

    assert first == second


def test_dynamic_leaver_environment_uses_real_employee_context(
    tmp_path,
):
    root = _make_sunhaven_root(tmp_path)

    worker = load_workforce(root)[1]

    environment = build_leaver_environment(worker)

    assert (
        environment["integrationContext"]["employeeId"]
        == "SC1006"
    )

    assert (
        environment["integrationContext"]["jobRole"]
        == "CareWorker"
    )

    names = [
        node["name"]
        for node in environment["nodes"]
    ]

    assert "Former Worker (SC1006)" in names


def test_integrated_leaver_comparison_open_then_blocked(
    tmp_path,
    real_controls,
    real_risk_model,
):
    root = _make_sunhaven_root(tmp_path)

    result = build_integrated_leaver_comparison(
        root,
        real_controls,
        real_risk_model,
    )

    assert (
        result["integration"]["employeeId"]
        == "SC1006"
    )

    assert (
        result["comparison"]["baselineStatus"]
        == "OPEN"
    )

    assert (
        result["comparison"]["protectedStatus"]
        == "BLOCKED"
    )

    assert (
        result["comparison"]["pathInterrupted"]
        is True
    )


def test_worker_state_parser_converts_boolean_and_lists(
    tmp_path,
):
    state_path = _make_worker_state(
        tmp_path,
        account_enabled=True,
    )

    rows = load_worker_state_csv(state_path)

    assert rows[0]["AccountEnabled"] is True

    assert rows[0]["GovernedGroupsList"] == [
        "SG-SC-CareWorkers"
    ]

    assert rows[0]["CareAppRolesList"] == [
        "CareWorker"
    ]


def test_invalid_worker_state_boolean_is_rejected(
    tmp_path,
):
    state_path = _make_worker_state(
        tmp_path,
        account_enabled=True,
    )

    text = state_path.read_text(
        encoding="utf-8"
    ).replace(
        "True",
        "Maybe",
    )

    state_path.write_text(
        text,
        encoding="utf-8",
    )

    with pytest.raises(SunhavenIntegrationError):
        load_worker_state_csv(state_path)


def test_operational_worker_state_can_show_potential_exposure(
    tmp_path,
    real_controls,
    real_risk_model,
):
    root = _make_sunhaven_root(tmp_path)

    state_path = _make_worker_state(
        tmp_path,
        account_enabled=True,
    )

    result = build_integrated_leaver_comparison(
        root,
        real_controls,
        real_risk_model,
        worker_state_path=state_path,
    )

    observed = result["integration"]["observedEvidence"]

    assert (
        observed["assessment"]
        == "OBSERVED_ACCOUNT_ENABLED"
    )

    assert observed["accountEnabled"] is True


def test_complete_leaver_result_is_recognised_as_supporting_evidence(
    tmp_path,
    real_controls,
    real_risk_model,
):
    root = _make_sunhaven_root(tmp_path)

    result_path = _make_leaver_result(
        tmp_path,
        complete=True,
    )

    result = build_integrated_leaver_comparison(
        root,
        real_controls,
        real_risk_model,
        leaver_result_path=result_path,
    )

    observed = result["integration"]["observedEvidence"]

    assert (
        observed["assessment"]
        == "OBSERVED_LEAVER_CONTROL_COMPLETE"
    )

    assert observed["leaverControlComplete"] is True


def test_integration_reports_are_generated(
    tmp_path,
    real_controls,
    real_risk_model,
):
    root = _make_sunhaven_root(tmp_path)

    snapshot = build_sunhaven_snapshot(root)

    leaver = build_integrated_leaver_comparison(
        root,
        real_controls,
        real_risk_model,
    )

    json_path = write_integration_json(
        snapshot,
        leaver,
        tmp_path / "integration.json",
    )

    csv_path = write_rbac_matrix_csv(
        snapshot,
        tmp_path / "rbac.csv",
    )

    html_path = write_integration_html(
        snapshot,
        leaver,
        tmp_path / "integration.html",
    )

    assert json_path.is_file()
    assert csv_path.is_file()
    assert html_path.is_file()

    html_text = html_path.read_text(
        encoding="utf-8",
    )

    assert (
        "Sunhaven SITAS Integrated Security Analysis"
        in html_text
    )

    assert "SC1006" in html_text

    assert (
        "config/route-role-map.csv"
        in html_text
    )

    assert (
        "does not query or modify live Microsoft Entra ID"
        in html_text
    )