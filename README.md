# FloodLens AI

Satellite-powered flood damage and accessibility intelligence.

> AI connects satellite evidence to human impact.

## Track B
FloodLens is being built for the Multimodal AI Hackathon 2026 Track B: **Mapping Flood Damage from Space**.

Core pipeline:

Satellite imagery → flood detection → infrastructure impact → road network → potential isolation → evidence-backed explanation.

## Architecture
- **Frontend:** Next.js App Router + TypeScript + Tailwind
- **Map:** MapLibre-ready dashboard
- **Backend:** FastAPI/Python service
- **Geospatial:** GeoPandas, Shapely, Rasterio, NetworkX
- **AI:** Gemini for multimodal reasoning/explanation, not as the primary flood segmentation model
- **Satellite:** Sentinel-1 SAR via Copernicus Data Space/Sentinel Hub
- **Infrastructure:** OpenStreetMap

## MVP principle
The demo must work from a deterministic preprocessed event dataset. Live satellite retrieval is an enhancement, not a dependency for the core demo.

## Status
Day 1 — foundation scaffold.
