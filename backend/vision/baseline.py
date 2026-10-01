"""Simple Sentinel-1 change-detection baseline."""
from __future__ import annotations
import numpy as np

def linear_to_db(values: np.ndarray, floor: float = 1e-8) -> np.ndarray:
    """Convert Sentinel-1 linear power to decibels."""
    return 10.0 * np.log10(np.maximum(np.asarray(values, dtype=np.float32), floor))

def flood_change_mask(before_db: np.ndarray, after_db: np.ndarray, threshold_db: float = -3.0) -> np.ndarray:
    if before_db.shape != after_db.shape:
        raise ValueError("before_db and after_db must have the same shape")
    return (after_db - before_db) < threshold_db

def flood_change_mask_linear(before_linear: np.ndarray, after_linear: np.ndarray, threshold_db: float = -3.0, valid_mask: np.ndarray | None = None) -> np.ndarray:
    mask = flood_change_mask(linear_to_db(before_linear), linear_to_db(after_linear), threshold_db)
    if valid_mask is not None:
        if valid_mask.shape != mask.shape:
            raise ValueError("valid_mask must have the same shape as the SAR arrays")
        mask &= valid_mask.astype(bool)
    return mask
