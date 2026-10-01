"""Simple, configurable Sentinel-1 change-detection baseline.

This is intentionally a baseline, not the final learned flood model. It mirrors
the core idea used in the Copernicus openEO flood example: compare pre/post SAR
backscatter and threshold a significant decrease.
"""

from __future__ import annotations

import numpy as np


def flood_change_mask(
    before_db: np.ndarray,
    after_db: np.ndarray,
    threshold_db: float = -3.0,
) -> np.ndarray:
    """Return a boolean mask where post-event backscatter drops enough to flag change.

    Both arrays must have the same shape and represent comparable backscatter
    values in dB. The threshold is configurable because an appropriate value
    depends on the event, acquisition geometry, terrain, and preprocessing.
    """
    if before_db.shape != after_db.shape:
        raise ValueError("before_db and after_db must have the same shape")
    change_db = after_db - before_db
    return change_db < threshold_db
