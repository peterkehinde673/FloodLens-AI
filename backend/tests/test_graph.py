import geopandas as gpd
from shapely.geometry import LineString

from network.graph import boundary_safe_nodes


def test_boundary_safe_nodes_detects_exit_endpoints():
    roads = gpd.GeoDataFrame(
        [
            {
                "id": "R1",
                "u": 1,
                "v": 2,
                "geometry": LineString([(0.0, 0.5), (1.0, 0.5)]),
            },
            {
                "id": "R2",
                "u": 3,
                "v": 4,
                "geometry": LineString([(0.5, 0.0), (0.5, 1.0)]),
            },
        ],
        crs="EPSG:4326",
    )

    safe = boundary_safe_nodes(
        roads,
        [0.0, 0.0, 1.0, 1.0],
        margin_m=2000,
    )

    assert set(safe) == {1, 2, 3, 4}
