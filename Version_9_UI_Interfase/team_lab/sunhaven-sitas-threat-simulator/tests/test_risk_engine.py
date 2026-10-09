import json
from pathlib import Path

import pytest

from risk_engine import (
    assess_risk,
    calculate_risk,
    classify_risk
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RISK_MODEL_FILE = (
    PROJECT_ROOT
    / "config"
    / "risk-model.json"
)


def load_test_risk_model():
    """
    Load the real SITAS risk model for testing.
    """

    with open(
        RISK_MODEL_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def test_scenario_1_risk():
    """
    Scenario 1 should produce a Critical risk score of 20.
    """

    risk_model = load_test_risk_model()

    result = assess_risk(
        4,
        5,
        risk_model
    )

    assert result["likelihood"] == 4
    assert result["likelihoodLabel"] == "Likely"

    assert result["impact"] == 5
    assert result["impactLabel"] == "Severe"

    assert result["riskScore"] == 20
    assert result["severity"] == "Critical"


def test_scenario_2_risk():
    """
    Scenario 2 should produce a High risk score of 15.
    """

    risk_model = load_test_risk_model()

    result = assess_risk(
        3,
        5,
        risk_model
    )

    assert result["likelihood"] == 3
    assert result["likelihoodLabel"] == "Possible"

    assert result["impact"] == 5
    assert result["impactLabel"] == "Severe"

    assert result["riskScore"] == 15
    assert result["severity"] == "High"


def test_scenario_3_risk():
    """
    Scenario 3 should produce a High risk score of 12.
    """

    risk_model = load_test_risk_model()

    result = assess_risk(
        3,
        4,
        risk_model
    )

    assert result["riskScore"] == 12
    assert result["severity"] == "High"


@pytest.mark.parametrize(
    "score, expected_severity",
    [
        (1, "Low"),
        (4, "Low"),
        (5, "Medium"),
        (9, "Medium"),
        (10, "High"),
        (16, "High"),
        (17, "Critical"),
        (25, "Critical")
    ]
)
def test_risk_severity_boundaries(
    score,
    expected_severity
):
    """
    Check the boundaries between each risk severity level.
    """

    risk_model = load_test_risk_model()

    severity = classify_risk(
        score,
        risk_model
    )

    assert severity == expected_severity


def test_invalid_likelihood_is_rejected():
    """
    Likelihood values below 1 should not be accepted.
    """

    risk_model = load_test_risk_model()

    with pytest.raises(ValueError):
        calculate_risk(
            0,
            5,
            risk_model
        )


def test_invalid_impact_is_rejected():
    """
    Impact values above 5 should not be accepted.
    """

    risk_model = load_test_risk_model()

    with pytest.raises(ValueError):
        calculate_risk(
            3,
            6,
            risk_model
        )


def test_non_integer_rating_is_rejected():
    """
    Risk ratings must be whole numbers.
    """

    risk_model = load_test_risk_model()

    with pytest.raises(ValueError):
        calculate_risk(
            3.5,
            5,
            risk_model
        )

