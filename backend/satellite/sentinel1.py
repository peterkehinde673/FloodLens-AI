"""Sentinel-1 acquisition and processing helpers for FloodLens AI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import os
import time

import httpx

CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"
COLLECTION = "sentinel-1-grd"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def utc_interval(start: str, end: str) -> str:
    """Return an RFC3339 UTC interval for Catalog/Process API queries."""

    def normalize(value: str) -> str:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return f"{normalize(start)}/{normalize(end)}"


def build_catalog_query(
    bbox: list[float], start: str, end: str, limit: int = 10
) -> dict[str, Any]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain [west, south, east, north]")
    if not (-180 <= bbox[0] <= bbox[2] <= 180 and -90 <= bbox[1] <= bbox[3] <= 90):
        raise ValueError("bbox coordinates are invalid")
    return {
        "bbox": bbox,
        "datetime": utc_interval(start, end),
        "collections": [COLLECTION],
        "limit": max(1, min(limit, 100)),
    }


def _access_token() -> str:
    now = time.time()
    cached = _token_cache.get("access_token")
    if cached and now < float(_token_cache.get("expires_at", 0)) - 60:
        return str(cached)

    client_id = os.getenv("CDSE_CLIENT_ID")
    client_secret = os.getenv("CDSE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "CDSE_CLIENT_ID and CDSE_CLIENT_SECRET are required for live Sentinel-1 access."
        )

    response = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Copernicus authentication response did not contain access_token.")

    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + int(payload.get("expires_in", 3600))
    return str(token)


def search_sentinel1(
    bbox: list[float], start: str, end: str, limit: int = 10
) -> dict[str, Any]:
    query = build_catalog_query(bbox, start, end, limit)
    response = httpx.post(
        CATALOG_URL,
        json=query,
        headers={"Authorization": f"Bearer {_access_token()}"},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def _item_datetime(item: dict[str, Any]) -> datetime:
    properties = item.get("properties", {})
    value = properties.get("datetime") or properties.get("start_datetime")
    if not value:
        raise ValueError("Sentinel-1 catalog item has no acquisition datetime")
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _property(item: dict[str, Any], name: str) -> Any:
    return item.get("properties", {}).get(name)


def _pair_compatibility_score(
    before: dict[str, Any], after: dict[str, Any]
) -> tuple[int, float]:
    """Prefer compatible acquisitions, then minimize temporal separation."""

    bp = before.get("properties", {})
    ap = after.get("properties", {})
    score = 0

    for key in ("s1:polarization", "sar:instrument_mode", "sat:orbit_state"):
        if bp.get(key) and bp.get(key) == ap.get(key):
            score += 1

    relative_before = bp.get("sat:relative_orbit")
    relative_after = ap.get("sat:relative_orbit")
    if relative_before is not None and relative_before == relative_after:
        score += 2

    gap_hours = abs((_item_datetime(after) - _item_datetime(before)).total_seconds()) / 3600
    return score, -gap_hours


def select_before_after(
    features: list[dict[str, Any]], event_time: str
) -> dict[str, Any]:
    """Choose a compatible pre-event/post-event Sentinel-1 pair."""

    if not features:
        raise ValueError("No Sentinel-1 acquisitions were returned for the requested window")

    event_dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
    if event_dt.tzinfo is None:
        event_dt = event_dt.replace(tzinfo=timezone.utc)
    event_dt = event_dt.astimezone(timezone.utc)

    dated = [(item, _item_datetime(item)) for item in features]
    before = [pair for pair in dated if pair[1] < event_dt]
    after = [pair for pair in dated if pair[1] >= event_dt]

    if not before or not after:
        raise ValueError(
            "Catalog results must contain at least one acquisition before and after the event time"
        )

    candidates: list[tuple[tuple[int, float], dict[str, Any], datetime, dict[str, Any], datetime]] = []
    for before_item, before_dt in before:
        for after_item, after_dt in after:
            candidates.append(
                (
                    _pair_compatibility_score(before_item, after_item),
                    before_item,
                    before_dt,
                    after_item,
                    after_dt,
                )
            )

    _, before_item, before_dt, after_item, after_dt = max(
        candidates, key=lambda row: row[0]
    )

    return {
        "before": {
            "id": before_item.get("id"),
            "datetime": before_dt.isoformat(),
            "item": before_item,
        },
        "after": {
            "id": after_item.get("id"),
            "datetime": after_dt.isoformat(),
            "item": after_item,
        },
        "gap_hours": round((after_dt - before_dt).total_seconds() / 3600, 2),
        "compatibility": {
            "polarization": _property(before_item, "s1:polarization"),
            "instrument_mode": _property(before_item, "sar:instrument_mode"),
            "orbit_state": _property(before_item, "sat:orbit_state"),
            "relative_orbit": _property(before_item, "sat:relative_orbit"),
        },
    }


def _scene_window(acquisition_time: str, minutes: int = 5) -> tuple[str, str]:
    dt = datetime.fromisoformat(acquisition_time.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return (
        (dt - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        (dt + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
    )


def build_process_request(
    bbox: list[float],
    start: str,
    end: str,
    width: int = 512,
    height: int = 512,
) -> dict[str, Any]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain [west, south, east, north]")
    if width < 32 or height < 32 or width > 2048 or height > 2048:
        raise ValueError("width and height must be between 32 and 2048")

    interval = utc_interval(start, end).split("/")
    return {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/EPSG/0/4326"
                },
            },
            "data": [
                {
                    "type": COLLECTION,
                    "dataFilter": {
                        "timeRange": {"from": interval[0], "to": interval[1]},
                        "acquisitionMode": "IW",\n                        "polarization": "DV",
                    },
                    "processing": {
                        "orthorectify": "true",
                        "backCoeff": "GAMMA0_TERRAIN",
                    },
                }
            ],
        },
        "output": {
            "width": width,
            "height": height,
            "responses": [
                {"identifier": "default", "format": {"type": "image/tiff"}}
            ],
        },
        "evalscript": """//VERSION=3
function setup() {
  return {
    input: ["VV", "VH", "dataMask"],
    output: { id: "default", bands: 3, sampleType: SampleType.FLOAT32 }
  }
}
function evaluatePixel(samples) {
  return [samples.VV, samples.VH, samples.dataMask]
}
""",
    }


def process_sentinel1(
    bbox: list[float],
    start: str,
    end: str,
    width: int = 512,
    height: int = 512,
) -> bytes:
    request = build_process_request(bbox, start, end, width, height)
    response = httpx.post(
        PROCESS_URL,
        json=request,
        headers={
            "Authorization": f"Bearer {_access_token()}",
            "Accept": "image/tiff",
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.content


def process_scene(
    bbox: list[float],
    acquisition_time: str,
    width: int = 512,
    height: int = 512,
) -> bytes:
    """Process one selected acquisition using a narrow time window."""

    start, end = _scene_window(acquisition_time)
    return process_sentinel1(bbox, start, end, width, height)
