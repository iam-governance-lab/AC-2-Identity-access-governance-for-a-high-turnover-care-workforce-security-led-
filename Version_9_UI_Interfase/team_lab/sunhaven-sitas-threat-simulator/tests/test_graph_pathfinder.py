import json
from pathlib import Path

from graph_engine import (
    build_graph,
    get_node_names
)

from pathfinder import find_path_bfs


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ENVIRONMENT_FILE = (
    PROJECT_ROOT
    / "config"
    / "environment.json"
)


def test_graph_creates_all_nodes():
    """
    The graph should contain every node from the environment.
    """

    environment = {
        "nodes": [
            {
                "id": "attacker",
                "name": "Attacker"
            },
            {
                "id": "identity",
                "name": "Identity"
            },
            {
                "id": "asset",
                "name": "Asset"
            }
        ],
        "relationships": []
    }

    graph = build_graph(environment)

    assert "attacker" in graph
    assert "identity" in graph
    assert "asset" in graph


def test_graph_creates_directed_relationships():
    """
    Relationships should be added in the correct direction.
    """

    environment = {
        "nodes": [
            {
                "id": "attacker",
                "name": "Attacker"
            },
            {
                "id": "identity",
                "name": "Identity"
            },
            {
                "id": "asset",
                "name": "Asset"
            }
        ],

        "relationships": [
            {
                "source": "attacker",
                "target": "identity"
            },
            {
                "source": "identity",
                "target": "asset"
            }
        ]
    }

    graph = build_graph(environment)

    assert graph["attacker"] == [
        "identity"
    ]

    assert graph["identity"] == [
        "asset"
    ]

    assert graph["asset"] == []


def test_node_names_are_created():
    """
    Node IDs should map to readable names.
    """

    environment = {
        "nodes": [
            {
                "id": "attacker",
                "name": "External Attacker"
            },
            {
                "id": "asset",
                "name": "Protected Asset"
            }
        ],

        "relationships": []
    }

    names = get_node_names(
        environment
    )

    assert names["attacker"] == (
        "External Attacker"
    )

    assert names["asset"] == (
        "Protected Asset"
    )


def test_bfs_finds_attack_path():
    """
    BFS should find a reachable attack path.
    """

    graph = {
        "attacker": [
            "credential"
        ],

        "credential": [
            "identity"
        ],

        "identity": [
            "application"
        ],

        "application": [
            "asset"
        ],

        "asset": []
    }

    path = find_path_bfs(
        graph,
        "attacker",
        "asset"
    )

    assert path == [
        "attacker",
        "credential",
        "identity",
        "application",
        "asset"
    ]


def test_bfs_returns_shortest_path():
    """
    BFS should return the shortest reachable path.
    """

    graph = {
        "attacker": [
            "route_a",
            "route_b"
        ],

        "route_a": [
            "middle"
        ],

        "middle": [
            "asset"
        ],

        "route_b": [
            "asset"
        ],

        "asset": []
    }

    path = find_path_bfs(
        graph,
        "attacker",
        "asset"
    )

    assert path == [
        "attacker",
        "route_b",
        "asset"
    ]


def test_bfs_returns_none_when_no_path_exists():
    """
    BFS should return None when the target
    cannot be reached.
    """

    graph = {
        "attacker": [
            "identity"
        ],

        "identity": [],

        "asset": []
    }

    path = find_path_bfs(
        graph,
        "attacker",
        "asset"
    )

    assert path is None


def test_bfs_handles_graph_cycle():
    """
    BFS should not loop forever when the graph
    contains a cycle.
    """

    graph = {
        "attacker": [
            "node_a"
        ],

        "node_a": [
            "node_b"
        ],

        "node_b": [
            "node_a",
            "asset"
        ],

        "asset": []
    }

    path = find_path_bfs(
        graph,
        "attacker",
        "asset"
    )

    assert path == [
        "attacker",
        "node_a",
        "node_b",
        "asset"
    ]


def test_bfs_start_equals_target():
    """
    If the start node is already the target,
    BFS should return that node immediately.
    """

    graph = {
        "asset": []
    }

    path = find_path_bfs(
        graph,
        "asset",
        "asset"
    )

    assert path == [
        "asset"
    ]


def test_real_scenario_6_path():
    """
    The current Sunhaven environment should
    produce the intended Scenario 6 path.
    """

    with open(
        ENVIRONMENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        environment = json.load(file)

    graph = build_graph(
        environment
    )

    path = find_path_bfs(
        graph,
        "device_attacker",
        "resident_records"
    )

    assert path == [
        "device_attacker",
        "stolen_care_worker_credential",
        "remote_care_worker_identity",
        "unmanaged_device_session",
        "care_portal",
        "resident_records"
    ]
