from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="FloodLens AI API", version="0.1.0")

class AnalyzeRequest(BaseModel):
    event_id: str = "demo-01"
    before: str | None = None
    after: str | None = None
    bbox: list[float] | None = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "floodlens-api"}

@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    return {
        "event_id": request.event_id,
        "status": "scaffold",
        "message": "Analysis pipeline is not wired yet.",
        "flood_area_km2": None,
        "affected_roads": [],
        "affected_bridges": [],
        "isolated_communities": [],
    }
