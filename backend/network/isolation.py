"""Road-network accessibility analysis for FloodLens."""
from __future__ import annotations

import networkx as nx


def potentially_isolated(
    graph: nx.Graph,
    communities: list[dict[str, object]],
    safe_nodes: list[object] | set[object],
) -> list[dict[str, object]]:
    """Describe whether each community retains a mapped route to a safe node.

    Results are deliberately phrased as potential isolation because OSM completeness
    and flood-classification uncertainty remain outside this graph model.
    """
    result: list[dict[str, object]] = []
    safe = set(safe_nodes)

    for community in communities:
        community_id = str(community["id"])
        node = community.get("node")
        record: dict[str, object] = {
            "community_id": community_id,
            "node": node,
            "potentially_isolated": False,
            "reason": "mapped road route remains to a safe node",
        }

        if node not in graph:
            record.update(
                potentially_isolated=True,
                reason="community node is not present in the post-flood road graph",
            )
        else:
            reachable_safe = [
                target for target in safe
                if target in graph and nx.has_path(graph, node, target)
            ]
            if not reachable_safe:
                record.update(
                    potentially_isolated=True,
                    reason="no mapped road path remains to a configured safe node",
                )
            else:
                record["reachable_safe_nodes"] = reachable_safe

        result.append(record)

    return result
