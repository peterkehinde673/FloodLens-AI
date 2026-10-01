import networkx as nx

from network.isolation import potentially_isolated

def test_isolation_after_affected_edge_is_removed():
    graph = nx.Graph()
    graph.add_edges_from([(1, 2), (2, 3)])
    communities = [{"id": "C1", "node": 3}]
    result = potentially_isolated(graph, communities, safe_nodes=[1])
    assert result[0]["community_id"] == "C1"
    assert result[0]["potentially_isolated"] is False

    graph.remove_edge(2, 3)
    result = potentially_isolated(graph, communities, safe_nodes=[1])
    assert result[0]["potentially_isolated"] is True
