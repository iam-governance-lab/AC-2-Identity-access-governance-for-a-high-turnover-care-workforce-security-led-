"""Read-only adapter between SITAS and the Sunhaven Care group project.

The adapter deliberately does not call Microsoft Graph, modify Entra ID, execute
JML actions, change Flask state, or make access decisions.  It reads approved
project artefacts and optional sanitised evidence exports and converts them into
normalised data that SITAS can analyse.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from comparison_engine import compare_scenario


SCHEMA_VERSION = "SITAS-SUNHAVEN-1"

REQUIRED_SOURCE_FILES = {
    "workforce": Path("data/workforce.csv"),
    "routeRoleMap": Path("config/route-role-map.csv"),
    "appRoleIds": Path("config/app-role-ids.json"),
    "groupObjectIds": Path("config/group-object-ids.json"),
}

OPTIONAL_CORE_FILES = {
    "joinerAutomation": Path("automation/Invoke-SunhavenJoiner.ps1"),
    "moverAutomation": Path("automation/Invoke-SunhavenMover.ps1"),
    "leaverAutomation": Path("automation/Invoke-SunhavenLeaver.ps1"),
    "workerStateExporter": Path("automation/Export-SunhavenWorkerState.ps1"),
    "flaskApplication": Path("app/app.py"),
}

WORKFORCE_REQUIRED_COLUMNS = {
    "employeeId",
    "displayName",
    "mailAlias",
    "jobRole",
    "facility",
    "status",
    "startDate",
    "endDate",
}

ROUTE_REQUIRED_COLUMNS = {
    "Route",
    "Purpose",
    "AllowedRoles",
    "UnauthorizedResult",
}

WORKER_STATE_REQUIRED_COLUMNS = {
    "CapturedUtc",
    "EmployeeId",
    "AccountEnabled",
    "JobTitle",
    "GovernedGroups",
    "CareAppRoles",
}

ROLE_TO_GROUP = {
    "CareWorker": "SG-SC-CareWorkers",
    "Nurse": "SG-SC-Nurses",
    "Manager": "SG-SC-Managers",
    "AgencyWorker": "SG-SC-AgencyWorkers",
    "Auditor": "SG-SC-Auditors",
}


class SunhavenIntegrationError(ValueError):
    """Raised when a Sunhaven project input is missing or malformed."""


def _normalise_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _read_csv_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise SunhavenIntegrationError(f"CSV file was not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = sorted(required_columns - fieldnames)
        if missing:
            raise SunhavenIntegrationError(
                f"CSV file {path.name} is missing required columns: {', '.join(missing)}"
            )

        rows = []
        for row in reader:
            cleaned = {key: _normalise_cell(value) for key, value in row.items()}
            if any(cleaned.values()):
                rows.append(cleaned)

    return rows


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SunhavenIntegrationError(f"JSON file was not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SunhavenIntegrationError(f"Unable to load JSON file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SunhavenIntegrationError(f"JSON file must contain an object: {path}")

    return data


def validate_sunhaven_root(root: str | Path) -> Path:
    """Validate a Sunhaven project root and return its resolved path."""
    root_path = Path(root).expanduser().resolve()
    missing = [
        str(relative)
        for relative in REQUIRED_SOURCE_FILES.values()
        if not (root_path / relative).is_file()
    ]

    if missing:
        raise SunhavenIntegrationError(
            "Sunhaven project root is missing required files: " + ", ".join(missing)
        )

    return root_path


def resolve_sunhaven_root(
    explicit_root: str | Path | None = None,
    project_root: str | Path | None = None,
) -> Path:
    """Find the Sunhaven root without relying on a hard-coded local path.

    When SITAS is stored directly inside the main Sunhaven repository, the
    repository root is the parent directory of the SITAS project directory.
    A standalone SITAS checkout can instead pass ``--root`` on the CLI.
    """
    if explicit_root:
        return validate_sunhaven_root(explicit_root)

    sitas_root = (
        Path(project_root).expanduser().resolve()
        if project_root
        else Path(__file__).resolve().parents[1]
    )

    candidates = [
        sitas_root.parent,
        sitas_root,
        Path.cwd().resolve(),
        Path.cwd().resolve().parent,
    ]

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return validate_sunhaven_root(candidate)
        except SunhavenIntegrationError:
            continue

    raise SunhavenIntegrationError(
        "Unable to locate the Sunhaven project root automatically. "
        "Place SITAS directly inside the main Sunhaven repository or provide "
        "the root explicitly with --root <path>."
    )


def load_workforce(root: str | Path) -> list[dict[str, str]]:
    root_path = validate_sunhaven_root(root)
    rows = _read_csv_rows(
        root_path / REQUIRED_SOURCE_FILES["workforce"],
        WORKFORCE_REQUIRED_COLUMNS,
    )

    seen: set[str] = set()
    duplicates: list[str] = []
    for row in rows:
        employee_id = row["employeeId"]
        if not employee_id:
            raise SunhavenIntegrationError("workforce.csv contains a blank employeeId")
        if employee_id in seen:
            duplicates.append(employee_id)
        seen.add(employee_id)

    if duplicates:
        raise SunhavenIntegrationError(
            "workforce.csv contains duplicate employeeId values: "
            + ", ".join(sorted(set(duplicates)))
        )

    return rows


def load_route_role_map(root: str | Path) -> list[dict[str, Any]]:
    root_path = validate_sunhaven_root(root)
    rows = _read_csv_rows(
        root_path / REQUIRED_SOURCE_FILES["routeRoleMap"],
        ROUTE_REQUIRED_COLUMNS,
    )

    result = []
    for row in rows:
        allowed_roles = [
            role.strip()
            for role in row["AllowedRoles"].split("|")
            if role.strip()
        ]
        result.append(
            {
                "route": row["Route"],
                "purpose": row["Purpose"],
                "allowedRoles": allowed_roles,
                "unauthorizedResult": row["UnauthorizedResult"],
            }
        )

    return result


def load_app_role_ids(root: str | Path) -> dict[str, str]:
    root_path = validate_sunhaven_root(root)
    data = _load_json_object(root_path / REQUIRED_SOURCE_FILES["appRoleIds"])
    return {str(key): str(value) for key, value in data.items()}


def load_group_object_ids(root: str | Path) -> dict[str, str]:
    root_path = validate_sunhaven_root(root)
    data = _load_json_object(root_path / REQUIRED_SOURCE_FILES["groupObjectIds"])
    return {str(key): str(value) for key, value in data.items()}


def load_worker_state_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load a sanitised worker-state export produced by the Sunhaven exporter."""
    csv_path = Path(path).expanduser().resolve()
    rows = _read_csv_rows(csv_path, WORKER_STATE_REQUIRED_COLUMNS)

    parsed = []
    for row in rows:
        enabled_text = row["AccountEnabled"].lower()
        if enabled_text not in {"true", "false"}:
            raise SunhavenIntegrationError(
                f"Invalid AccountEnabled value for {row['EmployeeId']}: "
                f"{row['AccountEnabled']}"
            )
        parsed.append(
            {
                **row,
                "AccountEnabled": enabled_text == "true",
                "GovernedGroupsList": _split_semicolon_value(
                    row.get("GovernedGroups", "")
                ),
                "CareAppRolesList": _split_semicolon_value(
                    row.get("CareAppRoles", "")
                ),
            }
        )

    return parsed


def load_leaver_result_json(path: str | Path) -> dict[str, Any]:
    """Load a sanitised JML leaver result without executing the JML workflow."""
    result = _load_json_object(Path(path).expanduser().resolve())

    required = {
        "EmployeeId",
        "AccountDisabled",
        "GovernedGroupsRemaining",
        "CareAppRolesRemaining",
        "LocalAppBlocked",
        "SessionsRevoked",
    }

    missing = sorted(required - set(result))
    if missing:
        raise SunhavenIntegrationError(
            "Leaver result is missing required fields: " + ", ".join(missing)
        )

    return result


def _split_semicolon_value(value: str) -> list[str]:
    text = _normalise_cell(value)
    if not text or text.lower() == "<none>":
        return []

    return [item.strip() for item in text.split(";") if item.strip()]


def build_rbac_matrix(
    route_map: list[dict[str, Any]],
    roles: list[str],
) -> list[dict[str, Any]]:
    matrix = []

    for role in sorted(roles):
        for route in route_map:
            matrix.append(
                {
                    "role": role,
                    "route": route["route"],
                    "purpose": route["purpose"],
                    "allowed": role in route["allowedRoles"],
                    "unauthorizedResult": route["unauthorizedResult"],
                }
            )

    return matrix


def _core_artifact_inventory(root: Path) -> dict[str, dict[str, Any]]:
    inventory = {}

    for name, relative in {
        **REQUIRED_SOURCE_FILES,
        **OPTIONAL_CORE_FILES,
    }.items():
        inventory[name] = {
            "path": relative.as_posix(),
            "present": (root / relative).is_file(),
        }

    return inventory


def _workforce_summary(
    workforce: list[dict[str, str]],
) -> dict[str, Any]:
    status_counts = Counter(
        row["status"] or "<blank>"
        for row in workforce
    )

    roles = sorted(
        {
            row["jobRole"]
            for row in workforce
            if row["jobRole"]
        }
    )

    facilities = sorted(
        {
            row["facility"]
            for row in workforce
            if row["facility"]
        }
    )

    leaving = [
        {
            "employeeId": row["employeeId"],
            "displayName": row["displayName"],
            "jobRole": row["jobRole"],
            "facility": row["facility"],
            "status": row["status"],
            "endDate": row["endDate"],
        }
        for row in workforce
        if row["status"].strip().lower()
        in {"leaving", "inactive", "leaver"}
    ]

    return {
        "recordCount": len(workforce),
        "statusCounts": dict(sorted(status_counts.items())),
        "roles": roles,
        "facilities": facilities,
        "leavingWorkers": leaving,
    }


def _control_mappings(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "controlId": "CTRL-MFA",
            "sunhavenArea": "Microsoft Entra strong authentication",
            "integrationStatus": "NOT_INFERRED_BY_ADAPTER",
            "note": (
                "SITAS continues to simulate MFA. The adapter does not infer live MFA "
                "enforcement from static configuration files."
            ),
        },
        {
            "controlId": "CTRL-SESSION",
            "sunhavenArea": "Shared-device/session protection",
            "integrationStatus": "SIMULATED_CONTROL",
            "note": (
                "Shared-session misuse remains a controlled SITAS scenario; the adapter "
                "does not make a live session-state claim."
            ),
        },
        {
            "controlId": "CTRL-ACCOUNT",
            "sunhavenArea": "JML leaver disablement and access removal",
            "integrationStatus": (
                "CORE_ARTIFACT_PRESENT"
                if (root / OPTIONAL_CORE_FILES["leaverAutomation"]).is_file()
                else "CORE_ARTIFACT_MISSING"
            ),
            "note": (
                "The adapter reads workforce/leaver evidence only. It never executes the "
                "leaver script or changes Entra ID."
            ),
        },
        {
            "controlId": "CTRL-RBAC",
            "sunhavenArea": "Flask route-role authorization and Entra app roles",
            "integrationStatus": "CORE_CONFIGURATION_PRESENT",
            "note": (
                "The adapter analyses route-role configuration and app-role mappings "
                "without changing authorization decisions."
            ),
        },
        {
            "controlId": "CTRL-PRIVAUTH",
            "sunhavenArea": "Privileged re-authentication",
            "integrationStatus": "SIMULATED_EXTENSION",
            "note": (
                "No live privileged re-authentication enforcement is claimed by SITAS."
            ),
        },
        {
            "controlId": "CTRL-DEVICE",
            "sunhavenArea": "Trusted/compliant device restriction",
            "integrationStatus": "FUTURE_EXTENSION",
            "note": (
                "This remains a future-production analysis scenario and does not claim "
                "that device compliance is implemented in the Sunhaven MVP."
            ),
        },
    ]


def build_sunhaven_snapshot(
    root: str | Path,
    worker_state_path: str | Path | None = None,
    leaver_result_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a normalised, read-only snapshot of the Sunhaven project artefacts."""

    root_path = validate_sunhaven_root(root)

    workforce = load_workforce(root_path)
    route_map = load_route_role_map(root_path)
    app_roles = load_app_role_ids(root_path)
    group_ids = load_group_object_ids(root_path)

    known_roles = sorted(app_roles)
    rbac_matrix = build_rbac_matrix(route_map, known_roles)

    findings: list[dict[str, Any]] = []

    workforce_roles = {
        row["jobRole"]
        for row in workforce
        if row["jobRole"]
    }

    unknown_workforce_roles = sorted(
        workforce_roles - set(known_roles)
    )

    if unknown_workforce_roles:
        findings.append(
            {
                "id": "INT-WORKFORCE-ROLE",
                "type": "INTEGRATION_WARNING",
                "message": "Workforce roles are missing from app-role configuration.",
                "values": unknown_workforce_roles,
            }
        )

    route_roles = {
        role
        for route in route_map
        for role in route["allowedRoles"]
    }

    unknown_route_roles = sorted(
        route_roles - set(known_roles)
    )

    if unknown_route_roles:
        findings.append(
            {
                "id": "INT-ROUTE-ROLE",
                "type": "INTEGRATION_WARNING",
                "message": (
                    "Route-role map references roles missing from app-role configuration."
                ),
                "values": unknown_route_roles,
            }
        )

    missing_expected_groups = sorted(
        group_name
        for role, group_name in ROLE_TO_GROUP.items()
        if role in known_roles and group_name not in group_ids
    )

    if missing_expected_groups:
        findings.append(
            {
                "id": "INT-GROUP-MAP",
                "type": "INTEGRATION_WARNING",
                "message": (
                    "Expected governed groups are missing from group-object configuration."
                ),
                "values": missing_expected_groups,
            }
        )

    operational_evidence: dict[str, Any] = {
        "workerState": None,
        "leaverResult": None,
    }

    if worker_state_path:
        worker_states = load_worker_state_csv(worker_state_path)
        operational_evidence["workerState"] = {
            "sourceFile": Path(worker_state_path).name,
            "records": worker_states,
        }

    if leaver_result_path:
        leaver_result = load_leaver_result_json(leaver_result_path)
        operational_evidence["leaverResult"] = {
            "sourceFile": Path(leaver_result_path).name,
            "record": leaver_result,
        }

    return {
        "schemaVersion": SCHEMA_VERSION,
        "mode": "READ_ONLY_PROJECT_SNAPSHOT",
        "sunhavenRootName": root_path.name,
        "sourceInventory": _core_artifact_inventory(root_path),
        "workforce": _workforce_summary(workforce),
        "authorization": {
            "appRoles": known_roles,
            "governedGroups": sorted(group_ids),
            "routes": route_map,
            "rbacMatrix": rbac_matrix,
        },
        "controlMappings": _control_mappings(root_path),
        "operationalEvidence": operational_evidence,
        "findings": findings,
    }


def select_leaving_worker(
    workforce: list[dict[str, str]],
    employee_id: str | None = None,
) -> dict[str, str]:
    if employee_id:
        matches = [
            row
            for row in workforce
            if row["employeeId"] == employee_id
        ]

        if len(matches) != 1:
            raise SunhavenIntegrationError(
                f"Expected exactly one workforce record for "
                f"{employee_id}; found {len(matches)}"
            )

        worker = matches[0]

        if (
            worker["status"].strip().lower()
            not in {"leaving", "inactive", "leaver"}
        ):
            raise SunhavenIntegrationError(
                f"Workforce record {employee_id} is not marked "
                f"as a leaving/inactive worker."
            )

        return worker

    leaving = [
        row
        for row in workforce
        if row["status"].strip().lower()
        in {"leaving", "inactive", "leaver"}
    ]

    if not leaving:
        raise SunhavenIntegrationError(
            "No Leaving/Inactive workforce record is available "
            "for the integrated leaver scenario."
        )

    return sorted(
        leaving,
        key=lambda row: row["employeeId"],
    )[0]


def build_leaver_environment(
    worker: dict[str, str],
) -> dict[str, Any]:
    """Create a small attack graph driven by a real Sunhaven workforce row."""

    employee_id = worker["employeeId"]

    # Reuse the stable SITAS node IDs so the existing CTRL-ACCOUNT simulation
    # rule remains compatible, while the readable node names carry the
    # selected Sunhaven workforce identity.
    actor_id = "former_worker"
    identity_id = "former_worker_identity"

    return {
        "environmentName": "Sunhaven Integrated Leaver Analysis",
        "description": (
            "Read-only SITAS model generated from the Sunhaven workforce record "
            f"for {employee_id}."
        ),
        "nodes": [
            {
                "id": actor_id,
                "name": f"Former Worker ({employee_id})",
                "type": "threat_actor",
            },
            {
                "id": identity_id,
                "name": f"Sunhaven Identity ({employee_id}, {worker['jobRole']})",
                "type": "identity",
            },
            {
                "id": "care_portal",
                "name": "Sunhaven Care Portal",
                "type": "application",
            },
            {
                "id": "resident_records",
                "name": "Fictional Resident Records",
                "type": "asset",
            },
        ],
        "relationships": [
            {
                "source": actor_id,
                "target": identity_id,
                "relationship": "uses_existing_identity",
            },
            {
                "source": identity_id,
                "target": "care_portal",
                "relationship": "authenticates_to",
            },
            {
                "source": "care_portal",
                "target": "resident_records",
                "relationship": "exposes",
            },
        ],
        "integrationContext": {
            "employeeId": employee_id,
            "jobRole": worker["jobRole"],
            "facility": worker["facility"],
            "workforceStatus": worker["status"],
            "endDate": worker["endDate"],
        },
    }


def build_leaver_scenario(
    worker: dict[str, str],
    environment: dict[str, Any],
) -> dict[str, Any]:
    employee_id = worker["employeeId"]

    return {
        "scenarioId": f"SITAS-INT-LEAVER-{employee_id}",
        "name": f"Integrated Former Worker Analysis - {employee_id}",
        "description": (
            "A read-only SITAS scenario generated from the Sunhaven workforce record "
            f"for {employee_id}, which is marked {worker['status']}. The baseline models "
            "the exposure if the identity remains usable; the protected run models the "
            "expected effect of account disablement."
        ),
        "startNode": environment["nodes"][0]["id"],
        "targetNode": "resident_records",
        "likelihood": 3,
        "impact": 4,
        "relatedControls": ["CTRL-ACCOUNT"],
    }


def _observed_leaver_evidence(
    employee_id: str,
    worker_state_path: str | Path | None,
    leaver_result_path: str | Path | None,
) -> dict[str, Any]:
    observed: dict[str, Any] = {
        "employeeId": employee_id,
        "assessment": "NO_OPERATIONAL_EVIDENCE_SUPPLIED",
        "accountEnabled": None,
        "leaverControlComplete": None,
        "sources": [],
    }

    if worker_state_path:
        states = load_worker_state_csv(worker_state_path)

        matches = [
            row
            for row in states
            if row["EmployeeId"] == employee_id
        ]

        if matches:
            state = matches[-1]

            observed["accountEnabled"] = state["AccountEnabled"]
            observed["sources"].append(
                Path(worker_state_path).name
            )

            observed["assessment"] = (
                "OBSERVED_ACCOUNT_ENABLED"
                if state["AccountEnabled"]
                else "OBSERVED_ACCOUNT_DISABLED"
            )

    if leaver_result_path:
        result = load_leaver_result_json(
            leaver_result_path
        )

        if str(result.get("EmployeeId")) == employee_id:
            groups_remaining = result.get(
                "GovernedGroupsRemaining"
            )

            groups_empty = (
                isinstance(groups_remaining, list)
                and len(groups_remaining) == 0
            )

            complete = bool(
                result.get("AccountDisabled") is True
                and groups_empty
                and int(
                    result.get(
                        "CareAppRolesRemaining",
                        -1,
                    )
                )
                == 0
                and result.get("LocalAppBlocked") is True
                and result.get("SessionsRevoked") is True
            )

            observed["leaverControlComplete"] = complete
            observed["sources"].append(
                Path(leaver_result_path).name
            )

            observed["assessment"] = (
                "OBSERVED_LEAVER_CONTROL_COMPLETE"
                if complete
                else "OBSERVED_LEAVER_CONTROL_INCOMPLETE"
            )

    return observed


def build_integrated_leaver_comparison(
    root: str | Path,
    controls: dict[str, Any],
    risk_model: dict[str, Any],
    employee_id: str | None = None,
    worker_state_path: str | Path | None = None,
    leaver_result_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run SITAS before/after analysis using a worker selected from workforce.csv."""

    root_path = validate_sunhaven_root(root)
    workforce = load_workforce(root_path)

    worker = select_leaving_worker(
        workforce,
        employee_id,
    )

    environment = build_leaver_environment(
        worker
    )

    scenario = build_leaver_scenario(
        worker,
        environment,
    )

    result = compare_scenario(
        environment,
        controls,
        risk_model,
        scenario,
    )

    result["integration"] = {
        "mode": "SUNHAVEN_WORKFORCE_DERIVED",
        "sourceFile": REQUIRED_SOURCE_FILES["workforce"].as_posix(),
        "employeeId": worker["employeeId"],
        "jobRole": worker["jobRole"],
        "facility": worker["facility"],
        "workforceStatus": worker["status"],
        "endDate": worker["endDate"],
        "observedEvidence": _observed_leaver_evidence(
            worker["employeeId"],
            worker_state_path,
            leaver_result_path,
        ),
        "interpretation": (
            "The OFF/ON comparison is a controlled SITAS simulation. Any operational "
            "evidence supplied is read-only supporting evidence and is not a live Entra query."
        ),
    }

    return result