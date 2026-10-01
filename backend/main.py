from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from rasterio.features import shapes, sieve
from rasterio.io import MemoryFile
from shapely.geometry import shape

from backend.analysis import analyze_flood_extent
from backend.osm import fetch_osm_aoi
from backend.satellite.sentinel1 import (
    process_scene,
    process_sentinel1,
    search_sentinel1,
    select_before_after,
)
from backend.vision.baseline import dual_polarization_flood_mask

app = FastAPI(title="FloodLens AI API", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parents[1]
DEMO_ROOT = ROOT / "data" / "demo"


class AnalyzeRequest(BaseModel):
    event_id: str = "event-01"


class SatelliteSearchRequest(BaseModel):
    bbox: list[float]
    start: str
    end: str


class SatellitePairRequest(BaseModel):
    bbox: list[float]
    start: str
    end: str
    event_time: str


class SatelliteProcessRequest(BaseModel):
    bbox: list[float]
    start: str
    end: str
    width: int = 512
    height: int = 512


class SatelliteSceneRequest(BaseModel):
    bbox: list[float]
    acquisition_time: str
    width: int = 512
    height: int = 512


class LiveAnalyzeRequest(SatellitePairRequest):
    width: int = 512
    height: int = 512
    vv_threshold_db: float = -3.0
    vh_threshold_db: float = -2.0
    min_pixels: int = 9
    road_threshold: float = 0.25
    safe_nodes: list[int] = []


def load_demo(event_id: str):
    event_dir = DEMO_ROOT / event_id
    if not event_dir.exists():
        raise HTTPException(status_code=404, detail=f"Unknown event: {event_id}")

    with (event_dir / "event.json").open() as handle:
        metadata = json.load(handle)

    flood = gpd.read_file(event_dir / "flood.geojson")
    roads = gpd.read_file(event_dir / "roads.geojson")
    communities = gpd.read_file(event_dir / "communities.geojson")
    bridges = gpd.read_file(event_dir / "bridges.geojson")
    return metadata, flood, roads, communities, bridges


def _geojson_features_from_mask(mask, transform, crs):
    features = []
    for geometry, value in shapes(
        mask.astype("uint8"),
        mask=mask.astype(bool),
        transform=transform,
    ):
        if value == 1:
            features.append(
                {
                    "type": "Feature",
                    "properties": {"class": "flood_water"},
                    "geometry": shape(geometry).__geo_interface__,
                }
            )

    if features:
        return gpd.GeoDataFrame.from_features(features, crs=crs)

    return gpd.GeoDataFrame(
        {"class": [], "geometry": []},
        geometry="geometry",
        crs=crs,
    )


def _process_pair_to_flood(request: LiveAnalyzeRequest, pair: dict):
    before_content = process_scene(
        request.bbox,
        pair["before"]["datetime"],
        request.width,
        request.height,
    )
    after_content = process_scene(
        request.bbox,
        pair["after"]["datetime"],
        request.width,
        request.height,
    )

    with MemoryFile(before_content) as before_mem:
        with before_mem.open() as before_ds:
            if before_ds.count < 3:
                raise ValueError(
                    "Sentinel-1 response must contain VV, VH, and dataMask bands"
                )
            before = before_ds.read([1, 2, 3]).astype("float32")
            transform = before_ds.transform
            crs = before_ds.crs

    with MemoryFile(after_content) as after_mem:
        with after_mem.open() as after_ds:
            if after_ds.count < 3:
                raise ValueError(
                    "Sentinel-1 response must contain VV, VH, and dataMask bands"
                )
            after = after_ds.read([1, 2, 3]).astype("float32")

    if before.shape != after.shape:
        raise ValueError("Before and after processed rasters do not match")

    valid = (before[2] > 0) & (after[2] > 0)
    mask, diagnostics = dual_polarization_flood_mask(
        before[0],
        after[0],
        before[1],
        after[1],
        vv_threshold_db=request.vv_threshold_db,
        vh_threshold_db=request.vh_threshold_db,
        valid_mask=valid,
    )

    if request.min_pixels > 1:
        mask = sieve(
            mask.astype("uint8"),
            size=request.min_pixels,
            connectivity=8,
        ).astype(bool)
        mask &= valid

    flood = _geojson_features_from_mask(mask, transform, crs)
    diagnostics["raw_flood_pixels"] = int(mask.sum())
    diagnostics["valid_pixels"] = int(valid.sum())
    diagnostics["min_pixels"] = int(request.min_pixels)
    return flood, diagnostics


@app.get("/health")
def health():
    return {"status": "ok", "service": "floodlens-api", "version": app.version}


@app.post("/api/satellite/search")
def satellite_search(request: SatelliteSearchRequest):
    try:
        return search_sentinel1(request.bbox, request.start, request.end)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel-1 search failed: {exc}") from exc


@app.post("/api/satellite/pair")
def satellite_pair(request: SatellitePairRequest):
    try:
        results = search_sentinel1(
            request.bbox,
            request.start,
            request.end,
            limit=100,
        )
        return select_before_after(results.get("features", []), request.event_time)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Sentinel-1 pair selection failed: {exc}",
        ) from exc


@app.post("/api/satellite/process")
def satellite_process(request: SatelliteProcessRequest):
    try:
        content = process_sentinel1(
            request.bbox,
            request.start,
            request.end,
            request.width,
            request.height,
        )
        return Response(content=content, media_type="image/tiff")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Sentinel-1 processing failed: {exc}",
        ) from exc


@app.post("/api/satellite/scene")
def satellite_scene(request: SatelliteSceneRequest):
    try:
        content = process_scene(
            request.bbox,
            request.acquisition_time,
            request.width,
            request.height,
        )
        return Response(content=content, media_type="image/tiff")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Sentinel-1 scene processing failed: {exc}",
        ) from exc


@app.post("/api/satellite/flood-mask")
def satellite_flood_mask(request: LiveAnalyzeRequest):
    """Generate a dual-polarization flood extent from a selected Sentinel-1 pair."""
    try:
        results = search_sentinel1(
            request.bbox,
            request.start,
            request.end,
            limit=100,
        )
        pair = select_before_after(results.get("features", []), request.event_time)
        flood, diagnostics = _process_pair_to_flood(request, pair)

        return {
            "status": "baseline_flood_mask_complete",
            "warning": "SAR VV/VH change-detection baseline; not confirmed flood damage and not a trained segmentation model.",
            "before": pair["before"],
            "after": pair["after"],
            "gap_hours": pair["gap_hours"],
            "diagnostics": diagnostics,
            "flood": json.loads(flood.to_json()),
            "crs": str(flood.crs),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Flood mask generation failed: {exc}",
        ) from exc


@app.post("/api/osm/aoi")
def osm_aoi(request: SatelliteProcessRequest):
    try:
        roads, bridges, communities = fetch_osm_aoi(request.bbox)
        return {
            "status": "osm_aoi_complete",
            "roads": json.loads(roads.to_json()),
            "bridges": json.loads(bridges.to_json()),
            "communities": json.loads(communities.to_json()),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OSM retrieval failed: {exc}") from exc


@app.post("/api/satellite/live-analyze")
def satellite_live_analyze(request: LiveAnalyzeRequest):
    """Run live Sentinel-1 flood detection plus OSM infrastructure analysis."""
    try:
        results = search_sentinel1(
            request.bbox,
            request.start,
            request.end,
            limit=100,
        )
        pair = select_before_after(results.get("features", []), request.event_time)
        flood, diagnostics = _process_pair_to_flood(request, pair)

        if flood.empty:
            return {
                "status": "live_analysis_complete",
                "warning": "No flood pixels survived the current VV/VH thresholds and minimum-region filter.",
                "before": pair["before"],
                "after": pair["after"],
                "diagnostics": diagnostics,
                "flood": json.loads(flood.to_json()),
                "affected_roads": [],
                "affected_bridges": [],
                "isolated_communities": [],
                "community_analysis": [],
            }

        roads, bridges, communities = fetch_osm_aoi(request.bbox)

        if roads.empty:
            return {
                "status": "live_flood_detection_complete",
                "warning": "Flood extent was detected, but OSM returned no roads for this AOI.",
                "before": pair["before"],
                "after": pair["after"],
                "gap_hours": pair["gap_hours"],
                "diagnostics": diagnostics,
                "flood": json.loads(flood.to_json()),
                "roads": json.loads(roads.to_json()),
                "bridges": json.loads(bridges.to_json()),
                "communities": json.loads(communities.to_json()),
                "affected_roads": [],
                "affected_bridges": [],
                "isolated_communities": [],
                "community_analysis": [],
            }

        analysis = analyze_flood_extent(
            flood,
            roads,
            communities,
            bridges,
            safe_nodes=request.safe_nodes,
            road_threshold=request.road_threshold,
        )

        isolation_warning = (
            None
            if request.safe_nodes
            else "Potential isolation was not evaluated because no safe road nodes were configured."
        )

        return {
            "status": "live_analysis_complete",
            "warning": "Flood extent is a VV/VH change-detection baseline. OSM coverage and road connectivity are not proof of physical damage or complete isolation.",
            "isolation_warning": isolation_warning,
            "before": pair["before"],
            "after": pair["after"],
            "gap_hours": pair["gap_hours"],
            "diagnostics": diagnostics,
            "flood": json.loads(flood.to_json()),
            "roads": json.loads(analysis["affected_roads"].to_json()),
            "affected_roads": json.loads(analysis["affected_roads"].to_json())["features"],
            "bridges": json.loads(bridges.to_json()),
            "affected_bridges": analysis["affected_bridges"],
            "communities": json.loads(analysis["communities"].to_json()),
            "isolated_communities": analysis["isolated_communities"],
            "community_analysis": analysis["community_analysis"],
            "flood_area_km2": analysis["flood_area_km2"],
            "safe_nodes": request.safe_nodes,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Live analysis failed: {exc}",
        ) from exc


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    metadata, flood, roads, communities, bridges = load_demo(request.event_id)
    analysis = analyze_flood_extent(
        flood,
        roads,
        communities,
        bridges,
        safe_nodes=metadata.get("safe_nodes", []),
    )

    return {
        "event_id": request.event_id,
        "status": "demo_analysis_complete",
        "message": "Deterministic demo analysis is running end-to-end. Live Sentinel-1 detection is available separately.",
        "flood_area_km2": analysis["flood_area_km2"],
        "affected_roads": json.loads(analysis["affected_roads"].to_json())["features"],
        "affected_bridges": analysis["affected_bridges"],
        "isolated_communities": analysis["isolated_communities"],
        "community_analysis": analysis["community_analysis"],
        "flood": json.loads(flood.to_json()),
        "roads": json.loads(analysis["affected_roads"].to_json()),
        "communities": json.loads(communities.to_json()),
        "bridges": json.loads(bridges.to_json()),
        "evidence": {
            "flood_source": "demo/flood.geojson",
            "road_source": "demo/roads.geojson",
            "community_source": "demo/communities.geojson",
            "bridge_source": "demo/bridges.geojson",
            "safe_nodes": metadata.get("safe_nodes", []),
        },
    }
