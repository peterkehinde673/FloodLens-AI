from __future__ import annotations

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, box


def road_graph(roads):
    """Build an undirected graph using every OSM node along each road way."""
    graph = nx.Graph()

    for row in roads.itertuples():
        sequence = getattr(row, "node_sequence", None)
        if sequence is None:
            sequence = [getattr(row, "u", None), getattr(row, "v", None)]

        sequence = [node for node in sequence if node is not None]
        if len(sequence) < 2:
            continue

        road_id = getattr(row, "id", None)
        for u, v in zip(sequence, sequence[1:]):
            if u == v:
                continue
            if graph.has_edge(u, v):
                road_ids = set(graph[u][v].get("road_ids", []))
                if road_id is not None:
                    road_ids.add(road_id)
                graph[u][v]["road_ids"] = sorted(road_ids)
            else:
                graph.add_edge(
                    u,
                    v,
                    road_ids=[road_id] if road_id is not None else [],
                )

    return graph


def remove_affected_edges(graph: nx.Graph, affected_roads) -> nx.Graph:
    """Remove every graph segment belonging to a potentially affected road way."""
    affected_ids = {
        getattr(row, "id", None)
        for row in affected_roads.itertuples()
        if getattr(row, "status", None) == "potentially_affected"
    }
    affected_ids.discard(None)

    result = graph.copy()
    for u, v, data in list(result.edges(data=True)):
        road_ids = set(data.get("road_ids", []))
        if road_ids.intersection(affected_ids):
            result.remove_edge(u, v)

    return result


def boundary_safe_nodes(
    roads: gpd.GeoDataFrame,
    bbox: list[float],
    *,
    margin_m: float = 500.0,
) -> list[object]:
    """Return OSM road nodes near the AOI boundary as potential exits."""
    if roads.empty:
        return []

    if len(bbox) != 4:
        raise ValueError("bbox must contain [west, south, east, north]")

    if roads.crs is None:
        raise ValueError("roads must have a CRS")

    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("invalid bbox")

    nodes_with_geometry = []
    for row in roads.itertuples():
        sequence = getattr(row, "node_sequence", None)
        coords = list(row.geometry.coords)
        if sequence is None:
            sequence = [getattr(row, "u", None), getattr(row, "v", None)]
        if len(sequence) != len(coords):
            continue
        nodes_with_geometry.extend(
            (node, Point(coord))
            for node, coord in zip(sequence, coords)
            if node is not None
        )

    if not nodes_with_geometry:
        return []

    nodes = gpd.GeoDataFrame(
        [{"node": node, "geometry": point} for node, point in nodes_with_geometry],
        geometry="geometry",
        crs=roads.crs,
    ).drop_duplicates(subset=["node"])

    metric_crs = (
        nodes.estimate_utm_crs()
        if not roads.crs.is_projected
        else roads.crs
    )
    if metric_crs is None:
        raise ValueError("could not determine a projected CRS for safe-node analysis")

    nodes_metric = nodes.to_crs(metric_crs)
    boundary = gpd.GeoSeries(
        [box(west, south, east, north).boundary],
        crs="EPSG:4326",
    ).to_crs(metric_crs).iloc[0]

    distances = nodes_metric.geometry.distance(boundary)
    return nodes.loc[distances <= margin_m, "node"].tolist()
