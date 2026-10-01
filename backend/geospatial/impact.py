"""Geospatial impact primitives used after flood-mask inference."""
from __future__ import annotations
import geopandas as gpd


def affected_roads(roads: gpd.GeoDataFrame, flood: gpd.GeoDataFrame, threshold: float = 0.25) -> gpd.GeoDataFrame:
    """Mark roads whose flooded overlap exceeds a fraction of their length.

    threshold is deliberately conservative and should be calibrated against the
    selected event. Output describes potential impact, not confirmed destruction.
    """
    if roads.empty or flood.empty:
        result = roads.copy()
        result["impact_ratio"] = 0.0
        result["status"] = "unaffected"
        return result
    flood_union = flood.to_crs(roads.crs).geometry.union_all()
    result = roads.copy()
    lengths = result.geometry.length.replace(0, 1e-9)
    overlap = result.geometry.intersection(flood_union).length
    result["impact_ratio"] = (overlap / lengths).clip(0, 1)
    result["status"] = result["impact_ratio"].ge(threshold).map({True: "potentially_affected", False: "unaffected"})
    return result
