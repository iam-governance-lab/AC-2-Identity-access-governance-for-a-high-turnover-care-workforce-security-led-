from copy import deepcopy

from comparison_engine import compare_scenario, set_control_state


def test_set_control_state_does_not_modify_original(real_controls):
    original = deepcopy(real_controls)
    updated = set_control_state(real_controls, ["CTRL-MFA"], True)

    assert real_controls == original
    assert updated != real_controls
    assert updated["controls"][0]["enabled"] is True


def test_compare_scenario_shows_open_then_blocked(
    real_environment,
    real_controls,
    real_risk_model,
    real_scenario_01,
):
    result = compare_scenario(
        real_environment,
        real_controls,
        real_risk_model,
        real_scenario_01,
    )

    assert result["comparison"]["baselineStatus"] == "OPEN"
    assert result["comparison"]["protectedStatus"] == "BLOCKED"
    assert result["comparison"]["pathInterrupted"] is True
    assert result["comparison"]["result"] == "CONTROL_EFFECTIVE"
