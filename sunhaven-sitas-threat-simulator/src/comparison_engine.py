"""Automatic before/after control comparison for SITAS scenarios."""

from copy import deepcopy

from analysis_engine import analyse_scenario


def set_control_state(controls, control_ids, enabled):
    """Return a copy of the control configuration with selected controls set."""
    updated = deepcopy(controls)
    selected = set(control_ids)

    for control in updated.get("controls", []):
        if control.get("id") in selected:
            control["enabled"] = enabled

    return updated


def compare_scenario(environment, controls, risk_model, scenario):
    """
    Compare one scenario with its related controls disabled and enabled.

    This satisfies the SITAS requirement for one automatic before/after
    comparison without changing the on-disk control configuration.
    """
    related_controls = scenario.get("relatedControls", [])

    baseline_controls = set_control_state(
        controls,
        related_controls,
        False,
    )
    protected_controls = set_control_state(
        controls,
        related_controls,
        True,
    )

    baseline = analyse_scenario(
        environment,
        baseline_controls,
        risk_model,
        scenario,
    )
    protected = analyse_scenario(
        environment,
        protected_controls,
        risk_model,
        scenario,
    )

    path_interrupted = (
        baseline["finalStatus"] == "OPEN"
        and protected["finalStatus"] == "BLOCKED"
    )

    return {
        "scenarioId": scenario["scenarioId"],
        "scenarioName": scenario["name"],
        "relatedControls": related_controls,
        "baseline": baseline,
        "protected": protected,
        "comparison": {
            "baselineStatus": baseline["finalStatus"],
            "protectedStatus": protected["finalStatus"],
            "pathInterrupted": path_interrupted,
            "result": (
                "CONTROL_EFFECTIVE"
                if path_interrupted
                else "NO_BLOCKING_CHANGE"
            ),
        },
    }
