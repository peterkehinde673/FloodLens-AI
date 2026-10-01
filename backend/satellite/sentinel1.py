"""Sentinel-1 acquisition helpers for FloodLens.

Live credentials are intentionally not required by the MVP. The first implementation
supports catalog-query construction so the UI/backend can later request a tightly
bounded before/after pair from Copernicus Data Space.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"
COLLECTION = "sentinel-1-grd"


def utc_interval(start: str, end: str) -> str:
    """Return an RFC3339 UTC interval for Catalog API queries."""
    def normalize(value: str) -> str:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return f"{normalize(start)}/{normalize(end)}"


def build_catalog_query(bbox: list[float], start: str, end: str, limit: int = 10) -> dict[str, Any]:
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
