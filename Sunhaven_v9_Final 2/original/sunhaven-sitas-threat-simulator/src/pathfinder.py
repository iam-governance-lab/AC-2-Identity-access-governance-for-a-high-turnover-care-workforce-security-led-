from collections import deque


def find_path_bfs(graph, start, target):
    """
    Find the shortest path between two nodes using Breadth-First Search.
    """

    queue = deque()

    queue.append([start])

    visited = set()

    while queue:
        path = queue.popleft()

        current_node = path[-1]

        if current_node == target:
            return path

        if current_node not in visited:
            visited.add(current_node)

            for neighbour in graph.get(current_node, []):
                new_path = list(path)
                new_path.append(neighbour)
                queue.append(new_path)

    return None
