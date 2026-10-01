# FloodLens AI architecture

## Decision flow
1. Sentinel-1 before/after imagery
2. Flood segmentation model
3. Raster-to-vector flood extent
4. OSM infrastructure intersection
5. Road graph construction
6. Remove affected edges and test community reachability
7. Gemini multimodal explanation using measured evidence

## Evidence rule
Never present structural failure, exact casualty numbers, or false model confidence when the evidence does not support it. Use language such as **potentially affected** and **potentially isolated** where the underlying evidence is inferential.

## Core API
- POST /api/analyze
- GET /api/flood-mask/{event_id}
- GET /api/roads/{event_id}
- GET /api/communities/{event_id}
- GET /api/report/{event_id}
