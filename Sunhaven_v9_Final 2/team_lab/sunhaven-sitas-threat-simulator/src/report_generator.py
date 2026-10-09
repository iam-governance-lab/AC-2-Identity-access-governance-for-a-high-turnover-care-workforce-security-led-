"""JSON, CSV and static HTML reporting for SITAS results."""

import csv
import html
import json
from pathlib import Path


def write_json_report(results, output_path):
    """Write structured SITAS results as UTF-8 JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def write_csv_summary(results, output_path):
    """Write one row per scenario comparison."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "scenario_id",
        "scenario_name",
        "controls",
        "likelihood",
        "impact",
        "risk_score",
        "severity",
        "baseline_status",
        "protected_status",
        "path_interrupted",
        "comparison_result",
    ]

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for item in results:
            risk = item["baseline"]["risk"]
            comparison = item["comparison"]
            writer.writerow(
                {
                    "scenario_id": item["scenarioId"],
                    "scenario_name": item["scenarioName"],
                    "controls": ";".join(item["relatedControls"]),
                    "likelihood": risk["likelihood"],
                    "impact": risk["impact"],
                    "risk_score": risk["riskScore"],
                    "severity": risk["severity"],
                    "baseline_status": comparison["baselineStatus"],
                    "protected_status": comparison["protectedStatus"],
                    "path_interrupted": comparison["pathInterrupted"],
                    "comparison_result": comparison["result"],
                }
            )

    return path


def _path_text(result):
    names = result.get("pathNodeNames", [])
    return " → ".join(names) if names else "No path found"


def write_html_report(results, output_path, title="Sunhaven SITAS Threat Assessment"):
    """Generate a dependency-free static HTML report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    details = []

    for item in results:
        comparison = item["comparison"]
        risk = item["baseline"]["risk"]
        controls = ", ".join(item["relatedControls"]) or "None"

        rows.append(
            "<tr>"
            f"<td>{html.escape(item['scenarioId'])}</td>"
            f"<td>{html.escape(item['scenarioName'])}</td>"
            f"<td>{html.escape(controls)}</td>"
            f"<td>{risk['riskScore']}/25 ({html.escape(risk['severity'])})</td>"
            f"<td>{html.escape(comparison['baselineStatus'])}</td>"
            f"<td>{html.escape(comparison['protectedStatus'])}</td>"
            f"<td>{'Yes' if comparison['pathInterrupted'] else 'No'}</td>"
            "</tr>"
        )

        details.append(
            "<section>"
            f"<h2>{html.escape(item['scenarioId'])} — {html.escape(item['scenarioName'])}</h2>"
            f"<p><strong>Baseline path:</strong> {html.escape(_path_text(item['baseline']))}</p>"
            f"<p><strong>Baseline status:</strong> {html.escape(comparison['baselineStatus'])}</p>"
            f"<p><strong>Protected status:</strong> {html.escape(comparison['protectedStatus'])}</p>"
            f"<p><strong>Comparison result:</strong> {html.escape(comparison['result'])}</p>"
            "</section>"
        )

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; line-height: 1.45; }}
h1, h2 {{ margin-bottom: 0.4rem; }}
table {{ border-collapse: collapse; width: 100%; margin: 1.5rem 0; }}
th, td {{ border: 1px solid #999; padding: 0.55rem; text-align: left; vertical-align: top; }}
th {{ font-weight: 700; }}
.notice {{ padding: 0.8rem; border: 1px solid #999; }}
section {{ margin-top: 1.6rem; padding-top: 0.5rem; border-top: 1px solid #bbb; }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<p class="notice">SITAS is a controlled laboratory threat-analysis tool. A BLOCKED result models the expected effect of a configured control and does not claim production enforcement.</p>
<table>
<thead>
<tr><th>ID</th><th>Scenario</th><th>Control</th><th>Risk</th><th>Baseline</th><th>Protected</th><th>Path interrupted</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
{''.join(details)}
</body>
</html>
"""

    path.write_text(document, encoding="utf-8")
    return path
