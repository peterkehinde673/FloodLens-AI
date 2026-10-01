from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from backend.geospatial.impact import affected_roads
from backend.network.graph import remove_affected_edges, road_graph
from backend.network.isolation import potentially_isolated
from backend.satellite.sentinel1 import process_sentinel1, search_sentinel1

app = FastAPI(title="FloodLens AI API", version="0.3.0")

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
    before: str | None = None
    after: str | None = None
    bbox: list[float] | None = None


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


@app.get("/health")
def health():
    return {"status": "ok", "service": "floodlens-api", "version": app.version}


@app.post("/api/satellite/search")
def satellite_search(request: AnalyzeRequest):
    if not request.bbox or not request.before or not request.after:
        raise HTTPException(
            status_code=400,
            detail="bbox, before, and after are required for satellite search.",
        )
    try:
        return search_sentinel1(request.bbox, request.before, request.after)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel-1 search failed: {exc}") from exc


@app.post("/api/satellite/process")
def satellite_process(request: AnalyzeRequest):
    if not request.bbox or not request.before or not request.after:
        raise HTTPException(
            status_code=400,
            detail="bbox, before, and after are required for satellite processing.",
        )
    try:
        content = process_sentinel1(request.bbox, request.before, request.after)
        return Response(content=content, media_type="image/tiff")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sentinel-1 processing failed: {exc}") from exc


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    metadata, flood, roads, communities, bridges = load_demo(request.event_id)

    impacted = affected_roads(roads, flood, threshold=0.25)

    graph = road_graph(roads)
    post_flood_graph = remove_affected_edges(graph, impacted)

    community_records = [
        {"id": row.id, "node": int(row.node)}
        for row in communities.itertuples()
    ]
    isolation = potentially_isolated(
        post_flood_graph,
        community_records,
        safe_nodes=metadata.get("safe_nodes", []),
    )

    flood_union = flood.to_crs(roads.crs).geometry.union_all()
    flood_area_km2 = round(
        flood.to_crs("EPSG:6933").geometry.union_all().area / 1_000_000,
        4,
    )

    affected_bridge_records = []
    for row in bridges.itertuples():
        if row.geometry.intersects(flood_union):
            affected_bridge_records.append({
                "id": row.id,
                "name": row.name,
                "road_id": row.road_id,
                "status": "potentially_affected",
                "reason": "bridge geometry intersects detected flood extent",
            })

    isolated_ids = [
        item["community_id"]
        for item in isolation
        if item["potentially_isolated"]
    ]

    return {
        "event_id": request.event_id,
        "status": "demo_analysis_complete",
        "message": "Deterministic demo analysis is running end-to-end. Live satellite ingestion and learned flood segmentation are next.",
        "flood_area_km2": flood_area_km2,
        "affected_roads": json.loads(impacted.to_json())["features"],
        "affected_bridges": affected_bridge_records,
        "isolated_communities": isolated_ids,
        "community_analysis": isolation,
        "flood": json.loads(flood.to_json()),
        "roads": json.loads(impacted.to_json()),
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
