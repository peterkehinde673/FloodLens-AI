"""Sentinel-1 flood change detection and raster-to-vector helpers."""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np
from rasterio.features import shapes
from rasterio.io import MemoryFile
from shapely.geometry import shape


def linear_to_db(values: np.ndarray, floor: float = 1e-8) -> np.ndarray:
    """Convert Sentinel-1 linear backscatter power to decibels."""
    values = np.asarray(values, dtype=np.float32)
    return 10.0 * np.log10(np.maximum(values, floor))


def flood_change_mask(
    before_vv: np.ndarray,
    after_vv: np.ndarray,
    before_vh: np.ndarray | None = None,
    after_vh: np.ndarray | None = None,
    threshold_db: float = -3.0,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Flag pixels with a configurable post-event SAR backscatter decrease.

    VV is the primary signal. If VH is supplied, the final mask requires the
    decrease in either channel to meet the threshold. This is a transparent
    baseline and not a trained segmentation model.
    """

    if before_vv.shape != after_vv.shape:
        raise ValueError("before_vv and after_vv must have the same shape")

    vv_change = linear_to_db(after_vv) - linear_to_db(before_vv)
    mask = vv_change < threshold_db

    if before_vh is not None or after_vh is not None:
        if before_vh is None or after_vh is None:
            raise ValueError("before_vh and after_vh must be supplied together")
        if before_vh.shape != after_vh.shape or before_vh.shape != before_vv.shape:
            raise ValueError("VV and VH arrays must have the same shape")
        vh_change = linear_to_db(after_vh) - linear_to_db(before_vh)
        mask = mask | (vh_change < threshold_db)

    if valid_mask is not None:
        if valid_mask.shape != mask.shape:
            raise ValueError("valid_mask must have the same shape as the SAR arrays")
        mask &= valid_mask.astype(bool)

    return mask


def tiff_bands(content: bytes) -> tuple[np.ndarray, Any]:
    """Read the VV/VH/dataMask TIFF returned by the Process API."""
    with MemoryFile(content) as memfile:
        with memfile.open() as dataset:
            if dataset.count < 3:
                raise ValueError("Expected a 3-band TIFF containing VV, VH and dataMask")
            arrays = dataset.read([1, 2, 3])
            profile = dataset.profile.copy()
            transform = dataset.transform
            crs = dataset.crs
    metadata = {"profile": profile, "transform": transform, "crs": crs}
    return arrays, metadata


def mask_to_geojson(
    mask: np.ndarray,
    transform: Any,
    crs: Any,
    min_pixels: int = 4,
) -> gpd.GeoDataFrame:
    """Convert connected raster mask regions to flood polygons."""

    if mask.dtype != bool:
        mask = mask.astype(bool)

    records = []
    for geometry, value in shapes(mask.astype(np.uint8), mask=mask, transform=transform):
        if value != 1:
            continue
        geom = shape(geometry)
        if geom.area >= min_pixels:
            records.append({"geometry": geom, "class": "flood_water"})

    if not records:
        return gpd.GeoDataFrame(
            {"class": [], "geometry": []},
            geometry="geometry",
            crs=crs,
        )

    return gpd.GeoDataFrame(records, geometry="geometry", crs=crs)
