from satellite.sentinel1 import build_catalog_query, utc_interval

def test_utc_interval_normalizes_dates():
    assert utc_interval("2026-10-01", "2026-10-02") == "2026-10-01T00:00:00Z/2026-10-02T00:00:00Z"

def test_build_catalog_query():
    query = build_catalog_query(
        [-1.0, 6.0, -0.9, 6.1],
        "2026-10-01",
        "2026-10-02",
        limit=10,
    )
    assert query["collections"] == ["sentinel-1-grd"]
    assert query["bbox"] == [-1.0, 6.0, -0.9, 6.1]
    assert query["limit"] == 10
