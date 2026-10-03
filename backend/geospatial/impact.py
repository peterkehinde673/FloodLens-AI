"""Geospatial impact primitives used after flood-mask inference."""
from __future__ import annotations

import geopandas as gpd


def affected_roads(
    roads: gpd.GeoDataFrame,
    flood: gpd.GeoDataFrame,
    threshold: float = 0.25,
) -> gpd.GeoDataFrame:
    """Mark roads whose flooded overlap exceeds a fraction of their length.

    Length/intersection calculations use a projected CRS so measurements are
    performed in metres rather than geographic degrees.

    The returned GeoDataFrame keeps the original road geometry and CRS.
    Results describe potential impact, not confirmed destruction.
    """
    result = roads.copy()

    if roads.empty or flood.empty:
        result["impact_ratio"] = 0.0
        result["status"] = "unaffected"
        return result

    if roads.crs is None:
        raise ValueError("roads must have a CRS")

    if flood.crs is None:
        raise ValueError("flood must have a CRS")

    flood_in_roads_crs = flood.to_crs(roads.crs)

    if roads.crs.is_projected:
        metric_crs = roads.crs
    else:
        combined = gpd.GeoSeries(
            list(roads.geometry) + list(flood_in_roads_crs.geometry),
            crs=roads.crs,
        )
        metric_crs = combined.estimate_utm_crs()

    if metric_crs is None:
        raise ValueError("could not determine a projected CRS for road impact")

    roads_metric = roads.to_crs(metric_crs)
    flood_metric = flood_in_roads_crs.to_crs(metric_crs)

    flood_union = flood_metric.geometry.union_all()

    lengths = roads_metric.geometry.length.replace(0, 1e-9)
    overlap = roads_metric.geometry.intersection(flood_union).length

    result["impact_ratio"] = (overlap / lengths).clip(0, 1)

    threshold_tolerance = 1e-3
    near_threshold = (
        (result["impact_ratio"] - threshold).abs()
        <= threshold_tolerance
    )
    result.loc[near_threshold, "impact_ratio"] = threshold

    result["status"] = result["impact_ratio"].ge(threshold).map(
        {
            True: "potentially_affected",
            False: "unaffected",
        }
    )

    return result
