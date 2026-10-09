"""Background worker for Sunhaven access-review inventory and remediation.

Run this process separately from Flask.  The worker claims one SQLite job at a
time and launches only the fixed, allowlisted PowerShell scripts below.  Values
from the browser are passed as structured data, never as a shell command.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

from access_review_db import (
    claim_next_job,
    finish_job,
    import_inventory_csv,
    initialize_access_review_database,
)


APP_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = APP_DIRECTORY.parent
EVIDENCE_ROOT = REPOSITORY_ROOT / "evidence" / "phase8" / "access-review-jobs"

EXPORT_SCRIPT = REPOSITORY_ROOT / "automation" / "Export-SunhavenAccessReview.ps1"
REMEDIATION_SCRIPT = (
    REPOSITORY_ROOT / "automation" / "Invoke-SunhavenReviewJob.ps1"
)

SENSITIVE_PATTERN = re.compile(
    r"(?i)(access[_ -]?token|client[_ -]?secret|password|authorization:)"
)


def required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def sanitize_transcript(text: str) -> str:
    safe_lines = []
    for line in text.splitlines():
        if SENSITIVE_PATTERN.search(line):
            safe_lines.append("[REDACTED SENSITIVE OUTPUT]")
        else:
            safe_lines.append(line[:2000])
    return "\n".join(safe_lines)


def run_powershell(arguments: list[str], transcript_path: Path) -> int:
    powershell_path = os.getenv("SUNHAVEN_PWSH_PATH", "pwsh")
    completed = subprocess.run(
        [powershell_path, "-NoLogo", "-NoProfile", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=int(os.getenv("SUNHAVEN_WORKER_TIMEOUT_SECONDS", "300")),
        shell=False,
        check=False,
    )
    transcript = sanitize_transcript(
        "\n".join(
            [
                f"Exit code: {completed.returncode}",
                "STDOUT",
                completed.stdout,
                "STDERR",
                completed.stderr,
            ]
        )
    )
    transcript_path.write_text(transcript, encoding="utf-8")
    return completed.returncode


def process_inventory_job(job: dict, job_directory: Path) -> None:
    tenant_id = required_environment("SUNHAVEN_TENANT_ID")
    csv_path = job_directory / "Pre-Review-Access-Inventory.csv"
    summary_path = job_directory / "Pre-Review-Inventory-Summary.txt"
    transcript_path = job_directory / "Inventory-Transcript.txt"

    exit_code = run_powershell(
        [
            "-File",
            str(EXPORT_SCRIPT),
            "-TenantId",
            tenant_id,
            "-CsvPath",
            str(csv_path),
            "-SummaryPath",
            str(summary_path),
        ],
        transcript_path,
    )

    if exit_code != 0:
        raise RuntimeError(
            f"Inventory exporter failed with exit code {exit_code}."
        )

    import_result = import_inventory_csv(job["campaign_id"], csv_path)
    finish_job(
        job_id=job["job_id"],
        status="SUCCEEDED",
        outcome="INVENTORY_IMPORTED",
        write_operations=0,
        result={
            **import_result,
            "inventory_file": csv_path.name,
            "summary_file": summary_path.name,
            "transcript_file": transcript_path.name,
        },
    )


def build_job_payload(job: dict) -> dict:
    decision_map = {
        "CHANGE": "ChangeAccess",
        "REMOVE": "RemoveAccess",
    }
    if job.get("decision") not in decision_map:
        raise RuntimeError("Only Change or Remove can create remediation jobs.")

    payload = {
        "JobId": job["job_id"],
        "Decision": decision_map[job["decision"]],
        "EmployeeId": job["employee_id"],
        "UserObjectId": job["user_object_id"],
        "CurrentRole": job["current_role"],
        "TargetRole": job.get("target_role"),
        "Facility": job["facility"],
        "ReviewedGovernedGroups": job["governed_groups"],
        "ReviewedCareAppRoles": job["care_app_roles"],
        "ApprovalText": job.get("submitted_approval") or "",
    }
    return payload


def process_remediation_job(job: dict, job_directory: Path) -> None:
    tenant_id = required_environment("SUNHAVEN_TENANT_ID")
    auth_mode = os.getenv("SUNHAVEN_GRAPH_AUTH_MODE", "Delegated")
    if auth_mode not in {"Delegated", "Certificate"}:
        raise RuntimeError("SUNHAVEN_GRAPH_AUTH_MODE is not supported.")

    payload_path = job_directory / "Job-Payload.json"
    result_path = job_directory / "Job-Result.json"
    transcript_path = job_directory / "Job-Transcript.txt"
    payload_path.write_text(
        json.dumps(build_job_payload(job), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    mode = "Plan" if job["job_type"] == "PLAN" else "Apply"
    exit_code = run_powershell(
        [
            "-File",
            str(REMEDIATION_SCRIPT),
            "-Mode",
            mode,
            "-TenantId",
            tenant_id,
            "-AuthMode",
            auth_mode,
            "-JobPayloadPath",
            str(payload_path),
            "-ResultPath",
            str(result_path),
        ],
        transcript_path,
    )

    if not result_path.exists():
        raise RuntimeError(
            f"PowerShell returned {exit_code} without a result file."
        )

    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    outcome = str(result.get("Outcome", "FAILED"))
    writes = int(result.get("WriteOperationsExecuted", 0))
    required_approval = result.get("RequiredApproval")

    if outcome in {"PLANNED", "MOVED", "ACCESS_REMOVED", "NO CHANGE"}:
        terminal_status = "SUCCEEDED"
    elif outcome == "BLOCKED":
        terminal_status = "BLOCKED"
    else:
        terminal_status = "FAILED"

    error_message = None
    if terminal_status != "SUCCEEDED":
        error_message = str(
            result.get("ErrorMessage")
            or result.get("Message")
            or f"PowerShell exit code {exit_code}."
        )[:1000]

    finish_job(
        job_id=job["job_id"],
        status=terminal_status,
        outcome=outcome,
        write_operations=writes,
        result={
            **result,
            "result_file": result_path.name,
            "transcript_file": transcript_path.name,
        },
        error_message=error_message,
        required_approval=required_approval,
    )


def process_one_job(job: dict) -> None:
    job_directory = EVIDENCE_ROOT / job["job_id"]
    job_directory.mkdir(parents=True, exist_ok=False)

    if job["job_type"] == "INVENTORY":
        process_inventory_job(job, job_directory)
    elif job["job_type"] in {"PLAN", "APPLY"}:
        process_remediation_job(job, job_directory)
    else:
        raise RuntimeError(f"Unsupported job type: {job['job_type']}")


def main() -> int:
    load_dotenv(APP_DIRECTORY / ".env")
    initialize_access_review_database()
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)

    if not EXPORT_SCRIPT.is_file() or not REMEDIATION_SCRIPT.is_file():
        raise RuntimeError("Required PowerShell automation script is missing.")

    poll_seconds = max(
        1,
        int(os.getenv("SUNHAVEN_WORKER_POLL_SECONDS", "2")),
    )
    print("Sunhaven access-review worker started.")
    print(f"Repository: {REPOSITORY_ROOT}")
    print(f"Authentication mode: {os.getenv('SUNHAVEN_GRAPH_AUTH_MODE', 'Delegated')}")

    while True:
        job = claim_next_job()
        if not job:
            time.sleep(poll_seconds)
            continue

        print(f"Processing {job['job_id']} ({job['job_type']})")
        try:
            process_one_job(job)
        except KeyboardInterrupt:
            raise
        except Exception as error:  # Worker must record a controlled failure.
            safe_error = f"{type(error).__name__}: {error}"[:1000]
            finish_job(
                job_id=job["job_id"],
                status="FAILED",
                outcome="FAILED",
                # The worker cannot prove whether a terminated external process
                # completed a partial write, so -1 means "unknown; investigate".
                write_operations=-1,
                result={"worker_error": safe_error},
                error_message=safe_error,
            )
            print(safe_error)
            if os.getenv("SUNHAVEN_WORKER_DEBUG") == "1":
                traceback.print_exc()


if __name__ == "__main__":
    raise SystemExit(main())
