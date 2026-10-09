from __future__ import annotations

import csv
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

SUPPORTED_EVENT_TYPES = {"MFA_PROMPT", "MFA_DENIED", "MFA_SUCCESS"}


@dataclass(frozen=True)
class MFAEvent:
    event_id: str
    employee_id: str
    timestamp: datetime
    event_type: str
    source: str = "SMFAA"


def parse_timestamp(value: str) -> datetime:
    text = (value or "").strip()
    if not text:
        raise ValueError("timestamp is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_event(row: dict, source: str = "SMFAA") -> MFAEvent:
    required = ("event_id", "employee_id", "timestamp", "event_type")
    missing = [name for name in required if not str(row.get(name, "")).strip()]
    if missing:
        raise ValueError(f"missing required field(s): {', '.join(missing)}")

    event_type = str(row["event_type"]).strip().upper()
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type}")

    return MFAEvent(
        event_id=str(row["event_id"]).strip(),
        employee_id=str(row["employee_id"]).strip(),
        timestamp=parse_timestamp(str(row["timestamp"])),
        event_type=event_type,
        source=source,
    )


def load_normalized_csv(path: Path) -> list[MFAEvent]:
    events: list[MFAEvent] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        for line_number, row in enumerate(reader, start=2):
            try:
                events.append(build_event(row, source="NORMALIZED_CSV"))
            except ValueError as exc:
                raise ValueError(f"{path.name} line {line_number}: {exc}") from exc
    return sorted(events, key=lambda event: event.timestamp)


def load_rules(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        rules = json.load(handle)

    required = ("prompt_burst", "repeated_denial", "denial_to_success")
    for name in required:
        if name not in rules:
            raise ValueError(f"missing rule configuration: {name}")
    for name in required:
        rule=rules[name]
        if not isinstance(rule,dict):raise ValueError(f'invalid rule configuration: {name}')
        for key in ('window_minutes', 'denial_count' if name=='denial_to_success' else 'count'):
            if type(rule.get(key)) is not int or not 1 <= rule[key] <= 10000:raise ValueError(f'{name}.{key} must be an integer from 1 to 10000')
        if rule.get('severity') not in {'LOW','MEDIUM','HIGH','CRITICAL'}:raise ValueError(f'invalid severity: {name}')
    return rules


def _threshold_findings(
    employee_id: str,
    events: list[MFAEvent],
    event_type: str,
    count: int,
    window_minutes: int,
    rule_name: str,
    severity: str,
) -> list[dict]:
    findings: list[dict] = []
    window: deque[MFAEvent] = deque()
    max_age = timedelta(minutes=window_minutes)

    for event in events:
        if event.event_type != event_type:
            continue
        window.append(event)
        while window and event.timestamp - window[0].timestamp > max_age:
            window.popleft()

        if len(window) >= count:
            supporting = list(window)[-count:]
            if rule_name == "PROMPT_BURST":
                reason = f"{count} MFA prompts occurred within {window_minutes} minutes."
            else:
                reason = f"{count} MFA denials occurred within {window_minutes} minutes."
            findings.append(
                _base_finding(
                    employee_id,
                    rule_name,
                    severity,
                    supporting,
                    reason,
                )
            )
            # Reset after a match so one burst does not create many duplicate findings.
            window.clear()

    return findings


def _denial_to_success_findings(
    employee_id: str,
    events: list[MFAEvent],
    denial_count: int,
    window_minutes: int,
    severity: str,
) -> list[dict]:
    findings: list[dict] = []
    denials: deque[MFAEvent] = deque()
    max_age = timedelta(minutes=window_minutes)

    for event in events:
        while denials and event.timestamp - denials[0].timestamp > max_age:
            denials.popleft()

        if event.event_type == "MFA_DENIED":
            denials.append(event)
            continue

        if event.event_type == "MFA_SUCCESS" and len(denials) >= denial_count:
            supporting = list(denials)[-denial_count:] + [event]
            findings.append(
                _base_finding(
                    employee_id,
                    "DENIAL_TO_SUCCESS",
                    severity,
                    supporting,
                    f"{denial_count} MFA denials were followed by an MFA success within {window_minutes} minutes.",
                )
            )
            denials.clear()

    return findings


def _base_finding(
    employee_id: str,
    rule: str,
    severity: str,
    supporting: list[MFAEvent],
    reason: str,
) -> dict:
    return {
        "employee_id": employee_id,
        "rule": rule,
        "severity": severity.upper(),
        "window_start": supporting[0].timestamp.isoformat().replace("+00:00", "Z"),
        "window_end": supporting[-1].timestamp.isoformat().replace("+00:00", "Z"),
        "event_count": len(supporting),
        "supporting_event_ids": [event.event_id for event in supporting],
        "reason": reason,
    }


def detect_findings(
    events: Iterable[MFAEvent],
    rules: dict,
    worker_context: dict[str, dict] | None = None,
) -> list[dict]:
    grouped: dict[str, list[MFAEvent]] = defaultdict(list)
    for event in events:
        grouped[event.employee_id].append(event)

    raw_findings: list[dict] = []
    for employee_id, worker_events in grouped.items():
        worker_events.sort(key=lambda event: event.timestamp)

        prompt = rules["prompt_burst"]
        raw_findings.extend(
            _threshold_findings(
                employee_id,
                worker_events,
                "MFA_PROMPT",
                int(prompt["count"]),
                int(prompt["window_minutes"]),
                "PROMPT_BURST",
                prompt.get("severity", "MEDIUM"),
            )
        )

        denial = rules["repeated_denial"]
        raw_findings.extend(
            _threshold_findings(
                employee_id,
                worker_events,
                "MFA_DENIED",
                int(denial["count"]),
                int(denial["window_minutes"]),
                "REPEATED_DENIAL",
                denial.get("severity", "MEDIUM"),
            )
        )

        transition = rules["denial_to_success"]
        raw_findings.extend(
            _denial_to_success_findings(
                employee_id,
                worker_events,
                int(transition["denial_count"]),
                int(transition["window_minutes"]),
                transition.get("severity", "HIGH"),
            )
        )

    raw_findings.sort(key=lambda item: (item["window_start"], item["employee_id"], item["rule"]))
    worker_context = worker_context or {}

    findings: list[dict] = []
    for index, finding in enumerate(raw_findings, start=1):
        context = worker_context.get(finding["employee_id"], {})
        finding = {
            "finding_id": f"SMFAA-F{index:03d}",
            **finding,
            "display_name": context.get("display_name", ""),
            "job_role": context.get("job_role", ""),
            "facility": context.get("facility", ""),
            "workforce_status": context.get("status", ""),
        }
        findings.append(finding)

    return findings


def export_findings(findings: list[dict], output_dir: Path, prefix: str) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{prefix}-findings.json"
    csv_path = output_dir / f"{prefix}-findings.csv"

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(findings, handle, indent=2)

    fieldnames = [
        "finding_id",
        "employee_id",
        "display_name",
        "job_role",
        "facility",
        "workforce_status",
        "rule",
        "severity",
        "window_start",
        "window_end",
        "event_count",
        "supporting_event_ids",
        "reason",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for finding in findings:
            row = dict(finding)
            row["supporting_event_ids"] = "|".join(finding["supporting_event_ids"])
            writer.writerow(row)

    return json_path, csv_path
