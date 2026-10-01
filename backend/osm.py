"""OpenStreetMap/Overpass ingestion for FloodLens AOIs."""
from __future__ import annotations
from typing import Any
import geopandas as gpd
import httpx
from shapely.geometry import LineString, Point
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def _validate_bbox(bbox: list[float]):
    if len(bbox) != 4: raise ValueError("bbox must contain [west, south, east, north]")
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90): raise ValueError("invalid bbox")
    return west, south, east, north

def build_overpass_query(bbox: list[float]) -> str:
    west, south, east, north = _validate_bbox(bbox)
    box = f"({south},{west},{north},{east})"
    return f"""[out:json][timeout:60];
(
  way["highway"]{box};
  node["place"]{box};
  way["man_made"="bridge"]{box};
  way["building"="bridge"]{box};
);
out body geom;"""

def fetch_osm_aoi(bbox: list[float], *, timeout: float = 90):
    query = build_overpass_query(bbox)
    response = httpx.post(OVERPASS_URL, data={'data': query}, headers={'User-Agent': 'FloodLens-AI/0.1'}, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    roads, bridges, communities = [], [], []
    for element in payload.get('elements', []):
        tags = element.get('tags', {})
        eid = f"{element.get('type','osm')}/{element.get('id')}"
        geometry = element.get('geometry', [])
        if element.get('type') == 'way' and 'highway' in tags and len(geometry) >= 2:
            coords = [(p['lon'], p['lat']) for p in geometry]
            roads.append({'id': eid, 'osm_id': element.get('id'), 'name': tags.get('name'), 'highway': tags.get('highway'), 'bridge': tags.get('bridge'), 'u': element.get('nodes',[None])[0], 'v': element.get('nodes',[None])[-1], 'geometry': LineString(coords)})
            if tags.get('bridge') not in (None, 'no'):
                bridges.append({'id': eid, 'osm_id': element.get('id'), 'name': tags.get('name'), 'road_id': eid, 'bridge': tags.get('bridge'), 'geometry': LineString(coords)})
        elif element.get('type') == 'way' and (tags.get('man_made') == 'bridge' or tags.get('building') == 'bridge') and len(geometry) >= 2:
            bridges.append({'id': eid, 'osm_id': element.get('id'), 'name': tags.get('name'), 'road_id': None, 'bridge': tags.get('man_made') or tags.get('building'), 'geometry': LineString([(p['lon'], p['lat']) for p in geometry])})
        elif element.get('type') == 'node' and tags.get('place') and tags.get('name'):
            communities.append({'id': eid, 'osm_id': element.get('id'), 'name': tags['name'], 'place': tags['place'], 'geometry': Point(element['lon'], element['lat'])})
    def frame(rows): return gpd.GeoDataFrame(rows, geometry='geometry', crs='EPSG:4326')
    return frame(roads), frame(bridges), frame(communities)