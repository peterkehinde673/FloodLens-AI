"""OpenStreetMap/Overpass ingestion for FloodLens AOIs."""
from __future__ import annotations

import time
from typing import Any

import geopandas as gpd
import httpx
from shapely.geometry import LineString, Point

OVERPASS_URLS = (
    "https://overpass.private.coffee/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
OVERPASS_URL = OVERPASS_URLS[0]


def _validate_bbox(bbox: list[float]):
    if len(bbox) != 4:
        raise ValueError("bbox must contain [west, south, east, north]")
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("invalid bbox")
    return west, south, east, north


def build_overpass_query(bbox: list[float]) -> str:
    west, south, east, north = _validate_bbox(bbox)
    box = f"({south},{west},{north},{east})"
    return f"""[out:json][timeout:60][maxsize:268435456];
(
  way["highway"]{box};
  node["place"]{box};
  way["man_made"="bridge"]{box};
  way["building"="bridge"]{box};
);
out body geom;"""


def _request_overpass(
    query: str,
    *,
    timeout: float,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    headers = {
        "User-Agent": "FloodLens-AI/0.1 (https://github.com/peterkehinde673/FloodLens-AI)",
        "Accept": "application/json",
    }
    transient_statuses = {429, 500, 502, 503, 504}
    last_error: Exception | None = None

    owns_client = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(timeout, connect=20.0),
        follow_redirects=True,
    )

    try:
        for endpoint in OVERPASS_URLS:
            for attempt in range(2):
                try:
                    response = client.post(
                        endpoint,
                        data={"data": query},
                        headers=headers,
                    )
                    if response.status_code in transient_statuses:
                        last_error = httpx.HTTPStatusError(
                            f"transient Overpass HTTP {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                        if attempt == 0:
                            time.sleep(2)
                            continue
                        break

                    response.raise_for_status()
                    return response.json()

                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt == 0:
                        time.sleep(2)
                        continue
                    break

                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code not in transient_statuses:
                        raise
                    last_error = exc
                    break

        raise RuntimeError(
            "All public Overpass endpoints failed. "
            f"Last error: {last_error}"
        ) from last_error
    finally:
        if owns_client:
            client.close()


def fetch_osm_aoi(bbox: list[float], *, timeout: float = 90):
    query = build_overpass_query(bbox)
    payload = _request_overpass(query, timeout=timeout)

    roads, bridges, communities = [], [], []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        eid = f"{element.get('type','osm')}/{element.get('id')}"
        geometry = element.get("geometry", [])

        if (
            element.get("type") == "way"
            and "highway" in tags
            and len(geometry) >= 2
        ):
            coords = [(p["lon"], p["lat"]) for p in geometry]
            node_sequence = element.get("nodes", [])
            roads.append(
                {
                    "id": eid,
                    "osm_id": element.get("id"),
                    "name": tags.get("name"),
                    "highway": tags.get("highway"),
                    "bridge": tags.get("bridge"),
                    "u": node_sequence[0] if node_sequence else None,
                    "v": node_sequence[-1] if node_sequence else None,
                    "node_sequence": node_sequence,
                    "geometry": LineString(coords),
                }
            )
            if tags.get("bridge") not in (None, "no"):
                bridges.append(
                    {
                        "id": eid,
                        "osm_id": element.get("id"),
                        "name": tags.get("name"),
                        "road_id": eid,
                        "bridge": tags.get("bridge"),
                        "geometry": LineString(coords),
                    }
                )

        elif (
            element.get("type") == "way"
            and (
                tags.get("man_made") == "bridge"
                or tags.get("building") == "bridge"
            )
            and len(geometry) >= 2
        ):
            bridges.append(
                {
                    "id": eid,
                    "osm_id": element.get("id"),
                    "name": tags.get("name"),
                    "road_id": None,
                    "bridge": tags.get("man_made") or tags.get("building"),
                    "geometry": LineString(
                        [(p["lon"], p["lat"]) for p in geometry]
                    ),
                }
            )

        elif (
            element.get("type") == "node"
            and tags.get("place")
            and tags.get("name")
        ):
            communities.append(
                {
                    "id": eid,
                    "osm_id": element.get("id"),
                    "name": tags["name"],
                    "place": tags["place"],
                    "geometry": Point(element["lon"], element["lat"]),
                }
            )

    def frame(rows):
        return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    return frame(roads), frame(bridges), frame(communities)
