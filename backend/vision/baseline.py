"""Transparent Sentinel-1 VV/VH flood-change baseline."""
from __future__ import annotations

import numpy as np


def linear_to_db(values: np.ndarray, floor: float = 1e-8) -> np.ndarray:
    """Convert Sentinel-1 linear power to decibels."""
    return 10.0 * np.log10(np.maximum(np.asarray(values, dtype=np.float32), floor))


def flood_change_mask(
    before_db: np.ndarray,
    after_db: np.ndarray,
    threshold_db: float = -3.0,
) -> np.ndarray:
    """Detect a backscatter drop in a single polarization."""
    if before_db.shape != after_db.shape:
        raise ValueError("before_db and after_db must have the same shape")
    return (after_db - before_db) < threshold_db


def flood_change_mask_linear(
    before_linear: np.ndarray,
    after_linear: np.ndarray,
    threshold_db: float = -3.0,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Single-polarization baseline operating on Sentinel-1 linear power."""
    mask = flood_change_mask(
        linear_to_db(before_linear),
        linear_to_db(after_linear),
        threshold_db,
    )
    if valid_mask is not None:
        if valid_mask.shape != mask.shape:
            raise ValueError("valid_mask must have the same shape as the SAR arrays")
        mask &= valid_mask.astype(bool)
    return mask


def dual_polarization_flood_mask(
    before_vv: np.ndarray,
    after_vv: np.ndarray,
    before_vh: np.ndarray,
    after_vh: np.ndarray,
    vv_threshold_db: float = -3.0,
    vh_threshold_db: float = -2.0,
    valid_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """Combine VV and VH change evidence conservatively.

    A pixel is flagged when both VV and VH show the configured backscatter drop.
    This is a transparent baseline, not a trained flood segmentation model.
    """
    arrays = (before_vv, after_vv, before_vh, after_vh)
    if any(array.shape != before_vv.shape for array in arrays):
        raise ValueError("VV and VH arrays must have matching shapes")

    vv_drop = linear_to_db(after_vv) - linear_to_db(before_vv)
    vh_drop = linear_to_db(after_vh) - linear_to_db(before_vh)
    mask = (vv_drop < vv_threshold_db) & (vh_drop < vh_threshold_db)

    if valid_mask is not None:
        if valid_mask.shape != mask.shape:
            raise ValueError("valid_mask must have the same shape as the SAR arrays")
        mask &= valid_mask.astype(bool)

    diagnostics = {
        "vv_threshold_db": float(vv_threshold_db),
        "vh_threshold_db": float(vh_threshold_db),
        "vv_mean_change_db": float(np.nanmean(vv_drop)),
        "vh_mean_change_db": float(np.nanmean(vh_drop)),
    }
    return mask, diagnostics
