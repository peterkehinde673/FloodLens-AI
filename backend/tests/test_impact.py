import geopandas as gpd
from shapely.geometry import LineString, Polygon

from geospatial.impact import affected_roads

def test_affected_roads_marks_flooded_segment():
    roads = gpd.GeoDataFrame(
        [{"id": "R1", "geometry": LineString([(0, 0), (2, 0)])}],
        crs="EPSG:4326",
    )
    flood = gpd.GeoDataFrame(
        [{"geometry": Polygon([(0.75, -1), (1.25, -1), (1.25, 1), (0.75, 1)])}],
        crs="EPSG:4326",
    )
    result = affected_roads(roads, flood, threshold=0.25)
    assert result.loc[0, "status"] == "potentially_affected"
    assert result.loc[0, "impact_ratio"] >= 0.25
