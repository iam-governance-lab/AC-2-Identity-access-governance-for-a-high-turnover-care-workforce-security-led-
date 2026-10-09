def build_graph(environment):
    """
    Convert the environment relationships into a simple directed graph.
    """

    graph = {}

    for node in environment["nodes"]:
        graph[node["id"]] = []

    for relationship in environment["relationships"]:
        source = relationship["source"]
        target = relationship["target"]

        if source in graph and target in graph:
            graph[source].append(target)

    return graph


def get_node_names(environment):
    """
    Create a dictionary that maps node IDs to readable names.
    """

    names = {}

    for node in environment["nodes"]:
        names[node["id"]] = node["name"]

    return names
