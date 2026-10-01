import numpy as np
import pytest

from vision.baseline import flood_change_mask

def test_flood_change_mask_flags_backscatter_drop():
    before = np.array([[-10.0, -10.0]])
    after = np.array([[-14.0, -11.0]])
    result = flood_change_mask(before, after, threshold_db=-3.0)
    assert result.tolist() == [[True, False]]

def test_flood_change_mask_requires_matching_shapes():
    with pytest.raises(ValueError):
        flood_change_mask(np.zeros((2, 2)), np.zeros((2, 3)))
