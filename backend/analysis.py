"""Shared flood-to-infrastructure analysis used by demo and live modes."""
from __future__ import annotations

import geopandas as gpd
from shapely.geometry import Point

from backend.geospatial.impact import affected_roads
from backend.network.graph import remove_affected_edges, road_graph
from backend.network.isolation import potentially_isolated


def _nearest_road_node(communities, roads):
    if communities.empty or roads.empty:
        result = communities.copy()
        result["node"] = None
        return result

    endpoints = []
    for row in roads.itertuples():
        endpoints.append((row.u, Point(row.geometry.coords[0])))
        endpoints.append((row.v, Point(row.geometry.coords[-1])))

    nodes = gpd.GeoDataFrame(
        [{"node": node, "geometry": point} for node, point in endpoints],
        geometry="geometry",
        crs=roads.crs,
    ).drop_duplicates(subset=["node"])

    joined = gpd.sjoin_nearest(
        communities.to_crs("EPSG:3857"),
        nodes.to_crs("EPSG:3857")[["node", "geometry"]],
        how="left",
        distance_col="distance_m",
    )
    return joined.to_crs(roads.crs)


def analyze_flood_extent(
    flood,
    roads,
    communities,
    bridges,
    safe_nodes=None,
    *,
    road_threshold=0.25,
):
    safe_nodes = [] if safe_nodes is None else list(safe_nodes)

    if flood.crs is None or roads.crs is None:
        raise ValueError("flood and roads must have CRS metadata")

    flood_for_roads = flood.to_crs(roads.crs)
    impacted = affected_roads(roads, flood_for_roads, threshold=road_threshold)

    if "node" not in communities.columns or communities["node"].isna().any():
        communities = _nearest_road_node(communities, roads)

    graph = road_graph(roads)
    post_flood_graph = remove_affected_edges(graph, impacted)

    records = [
        {"id": row.id, "node": row.node}
        for row in communities.itertuples()
        if row.node is not None
    ]
    isolation = potentially_isolated(
        post_flood_graph,
        records,
        safe_nodes=safe_nodes,
    )

    flood_area_km2 = round(
        flood.to_crs("EPSG:6933").geometry.union_all().area / 1_000_000,
        4,
    )

    flood_union = flood_for_roads.geometry.union_all()
    bridges_for_flood = bridges.to_crs(roads.crs)
    affected_bridges = []
    for row in bridges_for_flood.itertuples():
        if row.geometry.intersects(flood_union):
            affected_bridges.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "road_id": row.road_id,
                    "status": "potentially_affected",
                    "reason": "bridge geometry intersects detected flood extent",
                }
            )

    return {
        "flood_area_km2": flood_area_km2,
        "affected_roads": impacted,
        "affected_bridges": affected_bridges,
        "isolated_communities": [
            item["community_id"]
            for item in isolation
            if item["potentially_isolated"]
        ],
        "community_analysis": isolation,
        "communities": communities,
    }
