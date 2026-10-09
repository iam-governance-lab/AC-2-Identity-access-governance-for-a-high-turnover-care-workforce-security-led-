import json
from pathlib import Path

from model_loader import (
    load_environment,
    load_json_file
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_valid_environment_loads(tmp_path):
    """
    A valid environment file should load successfully.
    """

    test_file = tmp_path / "environment.json"

    data = {
        "nodes": [
            {
                "id": "attacker",
                "name": "Attacker"
            },
            {
                "id": "asset",
                "name": "Asset"
            }
        ],
        "relationships": [
            {
                "source": "attacker",
                "target": "asset"
            }
        ]
    }

    test_file.write_text(
        json.dumps(data),
        encoding="utf-8"
    )

    result = load_environment(
        test_file
    )

    assert result is not None
    assert "nodes" in result
    assert "relationships" in result


def test_environment_missing_nodes_is_rejected(tmp_path):
    """
    An environment without nodes should not load.
    """

    test_file = tmp_path / "environment.json"

    data = {
        "relationships": []
    }

    test_file.write_text(
        json.dumps(data),
        encoding="utf-8"
    )

    result = load_environment(
        test_file
    )

    assert result is None


def test_environment_missing_relationships_is_rejected(tmp_path):
    """
    An environment without relationships should not load.
    """

    test_file = tmp_path / "environment.json"

    data = {
        "nodes": []
    }

    test_file.write_text(
        json.dumps(data),
        encoding="utf-8"
    )

    result = load_environment(
        test_file
    )

    assert result is None


def test_invalid_json_is_rejected(tmp_path):
    """
    Invalid JSON should return None.
    """

    test_file = tmp_path / "invalid.json"

    test_file.write_text(
        "{ invalid json",
        encoding="utf-8"
    )

    result = load_json_file(
        test_file
    )

    assert result is None


def test_missing_json_file_is_rejected(tmp_path):
    """
    A missing file should return None.
    """

    missing_file = (
        tmp_path
        / "does-not-exist.json"
    )

    result = load_json_file(
        missing_file
    )

    assert result is None


def test_real_environment_file_loads():
    """
    The real SITAS environment file should load.
    """

    environment_file = (
        PROJECT_ROOT
        / "config"
        / "environment.json"
    )

    result = load_environment(
        environment_file
    )

    assert result is not None
    assert len(result["nodes"]) > 0
    assert len(result["relationships"]) > 0


def test_real_controls_file_loads():
    """
    The real SITAS controls file should load.
    """

    controls_file = (
        PROJECT_ROOT
        / "config"
        / "controls.json"
    )

    result = load_json_file(
        controls_file
    )

    assert result is not None
    assert "controls" in result
    assert len(result["controls"]) == 6


def test_real_risk_model_loads():
    """
    The real SITAS risk model should load.
    """

    risk_file = (
        PROJECT_ROOT
        / "config"
        / "risk-model.json"
    )

    result = load_json_file(
        risk_file
    )

    assert result is not None
    assert "scale" in result
    assert "severityBands" in result


def test_all_six_scenario_files_load():
    """
    All six SITAS scenario files should load successfully.
    """

    scenario_directory = (
        PROJECT_ROOT
        / "scenarios"
    )

    scenario_files = sorted(
        scenario_directory.glob(
            "scenario-*.json"
        )
    )

    assert len(scenario_files) == 6

    for scenario_file in scenario_files:

        scenario = load_json_file(
            scenario_file
        )

        assert scenario is not None

        assert "scenarioId" in scenario
        assert "name" in scenario
        assert "startNode" in scenario
        assert "targetNode" in scenario
        assert "likelihood" in scenario
        assert "impact" in scenario
        assert "relatedControls" in scenario
