"""Shared flood-to-infrastructure analysis used by demo and live modes."""
from __future__ import annotations

import geopandas as gpd

from backend.geospatial.impact import affected_roads
from backend.network.graph import remove_affected_edges, road_graph
from backend.network.isolation import potentially_isolated


def analyze_flood_extent(
    flood: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame,
    communities: gpd.GeoDataFrame,
    bridges: gpd.GeoDataFrame,
    safe_nodes: list[object] | set[object],
    *,
    road_threshold: float = 0.25,
) -> dict:
    """Connect flood polygons to roads, bridges, and community accessibility."""
    if flood.crs is None or roads.crs is None:
        raise ValueError("flood and roads must have CRS metadata")

    flood_for_roads = flood.to_crs(roads.crs)
    impacted = affected_roads(roads, flood_for_roads, threshold=road_threshold)

    graph = road_graph(roads)
    post_flood_graph = remove_affected_edges(graph, impacted)

    community_records = [
        {"id": row.id, "node": int(row.node)}
        for row in communities.itertuples()
    ]
    isolation = potentially_isolated(
        post_flood_graph,
        community_records,
        safe_nodes=safe_nodes,
    )

    flood_union = flood_for_roads.geometry.union_all()
    flood_metric = flood.to_crs("EPSG:6933")
    flood_area_km2 = round(
        flood_metric.geometry.union_all().area / 1_000_000,
        4,
    )

    bridges_for_flood = bridges.to_crs(roads.crs)
    affected_bridge_records = []
    for row in bridges_for_flood.itertuples():
        if row.geometry.intersects(flood_union):
            affected_bridge_records.append(
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
        "affected_bridges": affected_bridge_records,
        "isolated_communities": [
            item["community_id"]
            for item in isolation
            if item["potentially_isolated"]
        ],
        "community_analysis": isolation,
    }
