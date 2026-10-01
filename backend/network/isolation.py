"""Road-network accessibility analysis for FloodLens."""
from __future__ import annotations
import networkx as nx


def potentially_isolated(graph: nx.Graph, communities: dict[str, object], safe_nodes: set[object]) -> list[str]:
    """Return communities with no route to any safe node.

    communities maps an ID to its nearest graph node. This function intentionally
    reports *potential* isolation: mapped-road completeness and flood classification
    uncertainty remain outside the graph model.
    """
    result: list[str] = []
    safe = set(safe_nodes)
    for community_id, node in communities.items():
        if node not in graph:
            result.append(community_id)
            continue
        if not any(nx.has_path(graph, node, target) for target in safe if target in graph):
            result.append(community_id)
    return result
