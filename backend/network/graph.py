from __future__ import annotations

import networkx as nx


def road_graph(roads):
    """Build an undirected graph from road features with u/v node properties."""
    graph = nx.Graph()
    for row in roads.itertuples():
        props = row._asdict()
        u = props.get("u")
        v = props.get("v")
        if u is None or v is None:
            continue
        graph.add_edge(u, v, road_id=props.get("id"))
    return graph


def remove_affected_edges(graph: nx.Graph, affected_roads) -> nx.Graph:
    """Return a copy with roads marked potentially affected removed."""
    result = graph.copy()
    for row in affected_roads.itertuples():
        if getattr(row, "status", None) != "potentially_affected":
            continue
        u = getattr(row, "u", None)
        v = getattr(row, "v", None)
        if u is not None and v is not None and result.has_edge(u, v):
            result.remove_edge(u, v)
    return result
