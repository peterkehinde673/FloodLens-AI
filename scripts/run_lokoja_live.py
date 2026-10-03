from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes, sieve
from rasterio.io import MemoryFile
from shapely.geometry import shape

from backend.analysis import analyze_flood_extent
from backend.osm import fetch_osm_aoi
from backend.satellite.sentinel1 import process_scene, search_sentinel1, select_before_after
from backend.vision.baseline import dual_polarization_flood_mask

BBOX = [6.70, 7.75, 6.79, 7.85]
START = "2022-09-01T00:00:00Z"
END = "2022-10-20T23:59:59Z"
EVENT_TIME = "2022-10-01T00:00:00Z"
WIDTH = 512
HEIGHT = 512
MIN_PIXELS = 25
VV_THRESHOLD_DB = -3.0
VH_THRESHOLD_DB = -2.0

OUT = Path("artifacts/lokoja-2022")
OUT.mkdir(parents=True, exist_ok=True)


def read_scene(content: bytes):
    with MemoryFile(content) as mem:
        with mem.open() as ds:
            data = ds.read([1, 2, 3]).astype("float32")
            return data, ds.transform, ds.crs


def main():
    print("Searching Copernicus Data Space...")
    catalog = search_sentinel1(BBOX, START, END, limit=100)
    pair = select_before_after(catalog.get("features", []), EVENT_TIME)

    print("Before:", pair["before"]["id"])
    print("After :", pair["after"]["id"])

    before_content = process_scene(BBOX, pair["before"]["datetime"], WIDTH, HEIGHT)
    after_content = process_scene(BBOX, pair["after"]["datetime"], WIDTH, HEIGHT)

    before, transform, crs = read_scene(before_content)
    after, _, _ = read_scene(after_content)

    valid = (
        (before[2] > 0)
        & (after[2] > 0)
        & np.isfinite(before[0])
        & np.isfinite(after[0])
        & np.isfinite(before[1])
        & np.isfinite(after[1])
    )

    mask, diagnostics = dual_polarization_flood_mask(
        before[0],
        after[0],
        before[1],
        after[1],
        vv_threshold_db=VV_THRESHOLD_DB,
        vh_threshold_db=VH_THRESHOLD_DB,
        valid_mask=valid,
    )

    raw_pixels = int(mask.sum())

    mask = sieve(mask.astype("uint8"), size=MIN_PIXELS, connectivity=8).astype(bool)
    mask &= valid
    cleaned_pixels = int(mask.sum())

    profile = {
        "driver": "GTiff",
        "height": HEIGHT,
        "width": WIDTH,
        "count": 1,
        "dtype": "uint8",
        "crs": crs,
        "transform": transform,
        "nodata": 0,
        "compress": "deflate",
    }

    tif_path = OUT / "flood_candidate_cleaned.tif"
    with rasterio.open(tif_path, "w", **profile) as dst:
        dst.write(mask.astype("uint8"), 1)

    features = [
        shape(geom)
        for geom, value in shapes(mask.astype("uint8"), mask=mask, transform=transform)
        if value == 1
    ]

    flood = gpd.GeoDataFrame(
        {"class": ["candidate_flood"] * len(features)},
        geometry=features,
        crs=crs,
    )
    flood.to_file(OUT / "flood_candidate_cleaned.geojson", driver="GeoJSON")

    roads, bridges, communities = fetch_osm_aoi(BBOX)

    impact = analyze_flood_extent(
        flood,
        roads,
        communities,
        bridges,
        safe_nodes=[],
        road_threshold=0.25,
    )

    affected_roads = impact["affected_roads"]
    affected_roads.to_file(OUT / "affected_roads.geojson", driver="GeoJSON")

    # Persist the raw OSM layers used by the live analysis so the web demo can
    # render the same evidence instead of falling back to synthetic data.
    affected_bridge_ids = {
        item["id"] for item in impact["affected_bridges"] if item.get("id")
    }
    bridges_for_web = bridges.copy()
    bridges_for_web["status"] = bridges_for_web["id"].map(
        lambda value: "potentially_affected"
        if value in affected_bridge_ids
        else "unaffected"
    )
    bridges_for_web.to_file(OUT / "bridges.geojson", driver="GeoJSON")
    impact["communities"].to_file(OUT / "communities.geojson", driver="GeoJSON")

    flood_area_km2 = impact["flood_area_km2"]

    summary = {
        "event": "Lokoja, Kogi State, Nigeria — 2022 flood event",
        "aoi_bbox": BBOX,
        "before": pair["before"],
        "after": pair["after"],
        "before_datetime": pair["before"]["datetime"],
        "after_datetime": pair["after"]["datetime"],
        "gap_hours": pair["gap_hours"],
        "method": {
            "vv_threshold_db": VV_THRESHOLD_DB,
            "vh_threshold_db": VH_THRESHOLD_DB,
            "minimum_component_pixels": MIN_PIXELS,
            "note": "Candidate flood/change extent from Sentinel-1 VV/VH; not confirmed structural damage.",
        },
        "pixels": {
            "valid": int(valid.sum()),
            "raw_candidate": raw_pixels,
            "cleaned_candidate": cleaned_pixels,
            "raw_percent": round(100 * raw_pixels / valid.sum(), 2),
            "cleaned_percent": round(100 * cleaned_pixels / valid.sum(), 2),
        },
        "area_km2": flood_area_km2,
        "osm": {
            "roads": len(roads),
            "bridges": len(bridges),
            "communities": len(communities),
            "potentially_affected_roads": int(
                (affected_roads["status"] == "potentially_affected").sum()
            ) if not affected_roads.empty else 0,
            "potentially_affected_bridges": len(impact["affected_bridges"]),
        },
        "diagnostics": {
            key: float(value) if isinstance(value, (np.floating, float)) else value
            for key, value in diagnostics.items()
        },
    }

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str))

    print(json.dumps(summary, indent=2, default=str))
    print("Artifacts:", OUT)


if __name__ == "__main__":
    main()
