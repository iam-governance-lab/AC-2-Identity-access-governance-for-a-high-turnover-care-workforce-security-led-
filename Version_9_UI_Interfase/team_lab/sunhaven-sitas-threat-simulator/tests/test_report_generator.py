import csv
import json

from comparison_engine import compare_scenario
from report_generator import (
    write_csv_summary,
    write_html_report,
    write_json_report,
)


def _result(real_environment, real_controls, real_risk_model, real_scenario_01):
    return compare_scenario(
        real_environment,
        real_controls,
        real_risk_model,
        real_scenario_01,
    )


def test_json_report_generated(
    tmp_path,
    real_environment,
    real_controls,
    real_risk_model,
    real_scenario_01,
):
    output = tmp_path / "result.json"
    result = _result(real_environment, real_controls, real_risk_model, real_scenario_01)

    write_json_report([result], output)
    loaded = json.loads(output.read_text(encoding="utf-8"))

    assert loaded[0]["scenarioId"] == "SITAS-S01"
    assert loaded[0]["comparison"]["pathInterrupted"] is True


def test_csv_summary_generated(
    tmp_path,
    real_environment,
    real_controls,
    real_risk_model,
    real_scenario_01,
):
    output = tmp_path / "summary.csv"
    result = _result(real_environment, real_controls, real_risk_model, real_scenario_01)

    write_csv_summary([result], output)

    with output.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["scenario_id"] == "SITAS-S01"
    assert rows[0]["baseline_status"] == "OPEN"
    assert rows[0]["protected_status"] == "BLOCKED"


def test_html_report_generated(
    tmp_path,
    real_environment,
    real_controls,
    real_risk_model,
    real_scenario_01,
):
    output = tmp_path / "report.html"
    result = _result(real_environment, real_controls, real_risk_model, real_scenario_01)

    write_html_report([result], output)
    content = output.read_text(encoding="utf-8")

    assert "Sunhaven SITAS Threat Assessment" in content
    assert "SITAS-S01" in content
    assert "CONTROL_EFFECTIVE" in content
    assert "does not claim production enforcement" in content
