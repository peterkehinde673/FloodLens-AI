from __future__ import annotations

import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, box


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


def boundary_safe_nodes(
    roads: gpd.GeoDataFrame,
    bbox: list[float],
    *,
    margin_m: float = 500.0,
) -> list[object]:
    """Return road endpoint nodes near the AOI boundary.

    These nodes represent potential exit/entry points for accessibility
    analysis. They are not guaranteed safe in the real world; they simply
    provide graph destinations outside the flood-impact analysis area.
    """
    if roads.empty:
        return []

    if len(bbox) != 4:
        raise ValueError("bbox must contain [west, south, east, north]")

    if roads.crs is None:
        raise ValueError("roads must have a CRS")

    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("invalid bbox")

    endpoints = []
    for row in roads.itertuples():
        coords = list(row.geometry.coords)
        if len(coords) < 2:
            continue
        endpoints.append((row.u, Point(coords[0])))
        endpoints.append((row.v, Point(coords[-1])))

    if not endpoints:
        return []

    nodes = gpd.GeoDataFrame(
        [{"node": node, "geometry": point} for node, point in endpoints],
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
