"""Core scenario analysis used by the SITAS CLI and reporting features."""

from graph_engine import build_graph, get_node_names
from pathfinder import find_path_bfs
from risk_engine import assess_risk
from control_engine import assess_control


def analyse_scenario(environment, controls, risk_model, scenario):
    """
    Analyse one SITAS scenario and return a structured result.

    The function does not modify the supplied environment, controls, risk model,
    or scenario. It is intentionally deterministic so the same inputs produce
    the same result.
    """
    graph = build_graph(environment)
    node_names = get_node_names(environment)

    start_node = scenario["startNode"]
    target_node = scenario["targetNode"]
    path = find_path_bfs(graph, start_node, target_node)

    risk = assess_risk(
        scenario["likelihood"],
        scenario["impact"],
        risk_model,
    )

    result = {
        "scenarioId": scenario["scenarioId"],
        "scenarioName": scenario["name"],
        "description": scenario["description"],
        "startNode": start_node,
        "targetNode": target_node,
        "pathFound": bool(path),
        "pathNodeIds": path or [],
        "pathNodeNames": [node_names[node_id] for node_id in path] if path else [],
        "risk": risk,
        "controls": [],
        "finalStatus": "NO_PATH" if not path else "OPEN",
    }

    if not path:
        return result

    any_blocked = False

    for control_id in scenario.get("relatedControls", []):
        blocked, reason = assess_control(path, controls, control_id)
        result["controls"].append(
            {
                "controlId": control_id,
                "blocked": blocked,
                "status": "BLOCKED" if blocked else "OPEN",
                "reason": reason,
            }
        )
        if blocked:
            any_blocked = True

    if any_blocked:
        result["finalStatus"] = "BLOCKED"

    return result
