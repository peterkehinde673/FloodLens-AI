"""Sentinel-1 acquisition helpers for FloodLens.

Live credentials are intentionally not required by the MVP. The first implementation
supports catalog-query construction so the UI/backend can later request a tightly
bounded before/after pair from Copernicus Data Space.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import os
import time

import httpx

CATALOG_URL = "https://sh.dataspace.copernicus.eu/catalog/v1/search"
COLLECTION = "sentinel-1-grd"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


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


def _access_token() -> str:
    now = time.time()
    cached = _token_cache.get("access_token")
    if cached and now < float(_token_cache.get("expires_at", 0)) - 60:
        return str(cached)
    client_id = os.getenv("CDSE_CLIENT_ID")
    client_secret = os.getenv("CDSE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("CDSE_CLIENT_ID and CDSE_CLIENT_SECRET are required for live Sentinel-1 search.")
    response = httpx.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
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


def search_sentinel1(bbox: list[float], start: str, end: str, limit: int = 10) -> dict[str, Any]:
    query = build_catalog_query(bbox, start, end, limit)
    response = httpx.post(
        CATALOG_URL,
        json=query,
        headers={"Authorization": f"Bearer {_access_token()}"},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()
