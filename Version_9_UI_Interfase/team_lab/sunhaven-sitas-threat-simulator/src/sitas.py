import sys
from pathlib import Path

from analysis_engine import analyse_scenario
from comparison_engine import compare_scenario
from model_loader import load_environment, load_json_file
from report_generator import (
    write_csv_summary,
    write_html_report,
    write_json_report,
)
from sunhaven_adapter import (
    SunhavenIntegrationError,
    build_integrated_leaver_comparison,
    build_sunhaven_snapshot,
    resolve_sunhaven_root,
)
from sunhaven_report_generator import (
    write_integration_html,
    write_integration_json,
    write_rbac_matrix_csv,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = PROJECT_ROOT / "scenarios/scenario-01-stolen-nurse-credential.json"
ENVIRONMENT_PATH = PROJECT_ROOT / "config/environment.json"
CONTROLS_PATH = PROJECT_ROOT / "config/controls.json"
RISK_MODEL_PATH = PROJECT_ROOT / "config/risk-model.json"


def load_core_files():
    environment = load_environment(ENVIRONMENT_PATH)
    controls = load_json_file(CONTROLS_PATH)
    risk_model = load_json_file(RISK_MODEL_PATH)

    if environment is None or controls is None or risk_model is None:
        return None

    return environment, controls, risk_model


def print_path(result):
    if not result["pathFound"]:
        print("No attack path found.")
        return

    for index, name in enumerate(result["pathNodeNames"]):
        print(name)
        if index < len(result["pathNodeNames"]) - 1:
            print("   ↓")


def print_analysis(result):
    print()
    print(f"Scenario ID:   {result['scenarioId']}")
    print(f"Scenario Name: {result['scenarioName']}")
    print(f"Description:   {result['description']}")

    print("\nAttack Path")
    print("-" * 30)
    print_path(result)

    risk = result["risk"]
    print("\nRisk Assessment")
    print("-" * 30)
    print(f"Likelihood: {risk['likelihood']}/5 ({risk['likelihoodLabel']})")
    print(f"Impact:     {risk['impact']}/5 ({risk['impactLabel']})")
    print(f"Risk Score: {risk['riskScore']}/25")
    print(f"Severity:   {risk['severity']}")

    print("\nSecurity Control Assessment")
    print("-" * 30)

    if not result["controls"]:
        print("No security controls are assigned to this scenario.")

    for control in result["controls"]:
        print(f"Control: {control['controlId']}")
        print(f"Status:  {control['status']}")
        print(f"Reason:  {control['reason']}")
        print()

    print(f"Final Attack Path Status: {result['finalStatus']}")


def print_comparison(result):
    comparison = result["comparison"]
    risk = result["baseline"]["risk"]

    print()
    print(f"Scenario ID:   {result['scenarioId']}")
    print(f"Scenario Name: {result['scenarioName']}")
    print(f"Controls:      {', '.join(result['relatedControls']) or 'None'}")

    print("\nRisk Assessment")
    print("-" * 30)
    print(f"Risk Score: {risk['riskScore']}/25")
    print(f"Severity:   {risk['severity']}")

    print("\nAutomatic Before / After Comparison")
    print("-" * 40)
    print(f"Baseline (control OFF): {comparison['baselineStatus']}")
    print(f"Protected (control ON): {comparison['protectedStatus']}")
    print(f"Path interrupted:       {'YES' if comparison['pathInterrupted'] else 'NO'}")
    print(f"Result:                 {comparison['result']}")


def get_scenario_files():
    return sorted((PROJECT_ROOT / "scenarios").glob("scenario-*.json"))


def compare_all(core):
    environment, controls, risk_model = core
    results = []

    for scenario_path in get_scenario_files():
        scenario = load_json_file(str(scenario_path))
        if scenario is None:
            raise ValueError(f"Unable to load scenario: {scenario_path}")
        results.append(compare_scenario(environment, controls, risk_model, scenario))

    return results


def _display_path(path):
    path = Path(path)
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        return path


def generate_reports(results):
    reports_dir = PROJECT_ROOT / "reports"
    json_path = write_json_report(results, reports_dir / "sitas-analysis.json")
    csv_path = write_csv_summary(results, reports_dir / "sitas-summary.csv")
    html_path = write_html_report(results, reports_dir / "sitas-threat-report.html")

    print("\nReports generated")
    print("-" * 30)
    print(_display_path(json_path))
    print(_display_path(csv_path))
    print(_display_path(html_path))


def _parse_sunhaven_options(arguments):
    """Parse lightweight integration options while preserving the old CLI."""
    options = {
        "root": None,
        "employee_id": None,
        "worker_state": None,
        "leaver_result": None,
    }

    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token in {"--root", "--employee-id", "--worker-state", "--leaver-result"}:
            if index + 1 >= len(arguments):
                raise SunhavenIntegrationError(f"Missing value after {token}")
            value = arguments[index + 1]
            key = token[2:].replace("-", "_")
            options[key] = value
            index += 2
            continue
        raise SunhavenIntegrationError(f"Unknown integration option: {token}")

    return options


def _resolve_integration_root(options):
    return resolve_sunhaven_root(options["root"], PROJECT_ROOT)


def print_sunhaven_status(snapshot, root):
    print("\nSunhaven Integration Status")
    print("-" * 60)
    print(f"Root:              {root.name} (validated)")
    print(f"Mode:              {snapshot['mode']}")
    print(f"Workforce records: {snapshot['workforce']['recordCount']}")
    print(f"Roles:             {', '.join(snapshot['workforce']['roles']) or 'None'}")
    print(f"Facilities:        {', '.join(snapshot['workforce']['facilities']) or 'None'}")

    leaving = snapshot["workforce"]["leavingWorkers"]
    print(f"Leaving records:   {len(leaving)}")
    for worker in leaving:
        print(
            f"  - {worker['employeeId']} | {worker['jobRole']} | "
            f"{worker['status']} | endDate={worker['endDate'] or '-'}"
        )

    print("\nCore source validation")
    print("-" * 60)
    for name, source in snapshot["sourceInventory"].items():
        state = "OK" if source["present"] else "MISSING"
        print(f"{state:8} {name:20} {source['path']}")

    print("\nRBAC configuration")
    print("-" * 60)
    print(f"Configured app roles: {', '.join(snapshot['authorization']['appRoles'])}")
    print(f"Configured routes:    {len(snapshot['authorization']['routes'])}")

    print("\nIntegration findings")
    print("-" * 60)
    if not snapshot["findings"]:
        print("No configuration warnings found in the analysed files.")
    else:
        for finding in snapshot["findings"]:
            print(f"{finding['id']}: {finding['message']}")


def run_sunhaven_command(command, arguments, core):
    options = _parse_sunhaven_options(arguments)
    root = _resolve_integration_root(options)
    _environment, controls, risk_model = core

    snapshot = build_sunhaven_snapshot(
        root,
        worker_state_path=options["worker_state"],
        leaver_result_path=options["leaver_result"],
    )

    if command == "sunhaven-status":
        print_sunhaven_status(snapshot, root)
        return

    leaver_result = build_integrated_leaver_comparison(
        root,
        controls,
        risk_model,
        employee_id=options["employee_id"],
        worker_state_path=options["worker_state"],
        leaver_result_path=options["leaver_result"],
    )

    if command == "sunhaven-leaver":
        integration = leaver_result["integration"]
        print("\nSunhaven-derived input")
        print("-" * 40)
        print(f"Employee ID:      {integration['employeeId']}")
        print(f"Role:             {integration['jobRole']}")
        print(f"Facility:         {integration['facility']}")
        print(f"Workforce status: {integration['workforceStatus']}")
        print(f"End date:         {integration['endDate'] or '-'}")
        print_comparison(leaver_result)
        observed = integration["observedEvidence"]
        print("\nRead-only operational evidence")
        print("-" * 40)
        print(f"Assessment: {observed['assessment']}")
        print("This is not a live Entra query or enforcement action.")
        return

    if command == "sunhaven-report":
        reports_dir = PROJECT_ROOT / "reports"
        json_path = write_integration_json(
            snapshot,
            leaver_result,
            reports_dir / "sunhaven-integration-analysis.json",
        )
        csv_path = write_rbac_matrix_csv(
            snapshot,
            reports_dir / "sunhaven-rbac-matrix.csv",
        )
        html_path = write_integration_html(
            snapshot,
            leaver_result,
            reports_dir / "sunhaven-integration-report.html",
        )
        print_sunhaven_status(snapshot, root)
        print_comparison(leaver_result)
        print("\nIntegrated reports generated")
        print("-" * 40)
        print(_display_path(json_path))
        print(_display_path(csv_path))
        print(_display_path(html_path))
        return

    raise SunhavenIntegrationError(f"Unknown Sunhaven command: {command}")


def main():
    print("SITAS - Sunhaven Identity Threat and Attack-Path Simulator")
    print("-" * 60)

    core = load_core_files()
    if core is None:
        print("Unable to continue.")
        return 1

    environment, controls, risk_model = core
    command = sys.argv[1] if len(sys.argv) > 1 else "run"

    try:
        if command in {"sunhaven-status", "sunhaven-leaver", "sunhaven-report"}:
            run_sunhaven_command(command, sys.argv[2:], core)
            return 0

        if command == "compare-all":
            results = compare_all(core)
            for result in results:
                print_comparison(result)
            return 0

        if command == "report-all":
            results = compare_all(core)
            generate_reports(results)
            return 0

        if command == "compare":
            scenario_file = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_SCENARIO
            scenario = load_json_file(scenario_file)
            if scenario is None:
                print("Unable to continue.")
                return 1
            result = compare_scenario(environment, controls, risk_model, scenario)
            print_comparison(result)
            return 0

        # Backward-compatible behaviour:
        #   python src/sitas.py
        #   python src/sitas.py scenarios/scenario-03-former-worker.json
        scenario_file = DEFAULT_SCENARIO if command == "run" else Path(command)
        scenario = load_json_file(scenario_file)
        if scenario is None:
            print("Unable to continue.")
            return 1

        result = analyse_scenario(environment, controls, risk_model, scenario)
        print_analysis(result)
        return 0

    except SunhavenIntegrationError as exc:
        print(f"Sunhaven integration error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
