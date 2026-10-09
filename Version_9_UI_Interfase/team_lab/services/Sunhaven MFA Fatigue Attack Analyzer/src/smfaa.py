from __future__ import annotations

import argparse
import sys
from pathlib import Path

from detector import detect_findings, export_findings, load_normalized_csv, load_rules
from entra_csv_adapter import load_entra_export
from sunhaven_adapter import (
    build_worker_context,
    find_repo_root,
    load_identity_map,
    load_workforce,
)

SERVICE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SERVICE_ROOT / "config" / "detection-rules.json"
DEFAULT_DEMO = SERVICE_ROOT / "data" / "demo-events.csv"
DEFAULT_IDENTITY_MAP = SERVICE_ROOT / "data" / "identity-map.csv"
DEFAULT_REPORTS = SERVICE_ROOT / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SMFAA - Sunhaven MFA Fatigue Attack Analyzer"
    )
    parser.add_argument(
        "--source",
        choices=("demo", "repo-entra", "csv", "live-entra"),
        default="demo",
        help="Input source. 'repo-entra' uses the existing Sunhaven Phase 6 Entra CSV.",
    )
    parser.add_argument("--input", type=Path, help="Normalized CSV path when --source csv is used.")
    parser.add_argument("--repo-root", type=Path, help="Sunhaven repository root. Normally auto-detected.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_REPORTS)
    return parser.parse_args()


def _repo_root(args: argparse.Namespace) -> Path | None:
    if args.repo_root:
        return args.repo_root.resolve()
    return find_repo_root(SERVICE_ROOT)


def _print_findings(findings: list[dict]) -> None:
    if not findings:
        print("\nNo MFA-fatigue findings were produced.")
        return

    print(f"\nFindings: {len(findings)}")
    for finding in findings:
        worker = finding["employee_id"]
        if finding.get("display_name"):
            worker += f" ({finding['display_name']})"
        print(
            f"- {finding['finding_id']} | {worker} | {finding['rule']} | "
            f"{finding['severity']}"
        )
        print(f"  {finding['reason']}")
        print(f"  Evidence: {', '.join(finding['supporting_event_ids'])}")


def main() -> int:
    args = parse_args()
    repo_root = _repo_root(args)

    workforce_path = repo_root / "data" / "workforce.csv" if repo_root else None
    workforce = load_workforce(workforce_path)
    identity_rows = load_identity_map(DEFAULT_IDENTITY_MAP)
    worker_context = build_worker_context(workforce, identity_rows)
    rules = load_rules(args.config)

    print("SMFAA - Sunhaven MFA Fatigue Attack Analyzer")
    print("Mode: operational detection (read-only)")

    if args.source == "demo":
        events = load_normalized_csv(DEFAULT_DEMO)
        prefix = "demo"
        print(f"Input: {DEFAULT_DEMO}")

    elif args.source == "csv":
        if not args.input:
            print("ERROR: --input is required with --source csv", file=sys.stderr)
            return 2
        events = load_normalized_csv(args.input)
        prefix = args.input.stem.lower().replace(" ", "-")
        print(f"Input: {args.input}")

    elif args.source == "repo-entra":
        if not repo_root:
            print(
                "ERROR: Sunhaven repository root could not be found. Use --repo-root.",
                file=sys.stderr,
            )
            return 2
        entra_path = repo_root / "evidence" / "phase6" / "P6-E14_Entra-SignIn-Sanitized.csv"
        if not entra_path.exists():
            print(f"ERROR: existing Entra export not found: {entra_path}", file=sys.stderr)
            return 2
        events, stats = load_entra_export(entra_path, workforce, identity_rows)
        prefix = "repo-entra"
        print(f"Input: {entra_path}")
        print(
            "Entra adapter: "
            f"{stats['rows']} rows, {stats['normalized']} MFA events, "
            f"{stats['ignored']} ignored, {stats['unmapped']} unmapped"
        )
    else:
        print("Input: Microsoft Graph - live Entra sign-in logs")
        from entra_graph_adapter import load_graph_signins
        events, stats = load_graph_signins(workforce, identity_rows)
        prefix = "live-entra"
        print(
            "Graph adapter: "
            f"{stats['rows']} rows, {stats['normalized']} MFA events, "
            f"{stats['ignored']} ignored, {stats['unmapped']} unmapped"
        )

    print(f"Validated events: {len(events)}")
    if workforce_path and workforce_path.exists():
        print(f"Workforce context: {workforce_path} (read-only)")
    else:
        print("Workforce context: not found; detection will still run")

    findings = detect_findings(events, rules, worker_context)
    _print_findings(findings)

    json_path, csv_path = export_findings(findings, args.output_dir, prefix)
    print(f"\nJSON report: {json_path}")
    print(f"CSV report:  {csv_path}")
    print("No IAM, Entra, JML or Flask state was changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
