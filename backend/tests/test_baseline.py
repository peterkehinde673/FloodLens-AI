import numpy as np
import pytest

from vision.baseline import (
    dual_polarization_flood_mask,
    flood_change_mask,
    flood_change_mask_linear,
    linear_to_db,
)


def test_flood_change_mask_flags_backscatter_drop():
    before = np.array([[-10.0, -10.0]])
    after = np.array([[-14.0, -11.0]])
    result = flood_change_mask(before, after, threshold_db=-3.0)
    assert result.tolist() == [[True, False]]


def test_flood_change_mask_requires_matching_shapes():
    with pytest.raises(ValueError):
        flood_change_mask(np.zeros((2, 2)), np.zeros((2, 3)))


def test_linear_to_db():
    assert np.allclose(linear_to_db(np.array([[1.0, 0.1]])), [[0.0, -10.0]], atol=1e-5)


def test_linear_flood_change_mask():
    before = np.array([[1.0, 1.0]])
    after = np.array([[0.1, 0.6]])
    result = flood_change_mask_linear(before, after, threshold_db=-3.0)
    assert result.tolist() == [[True, False]]


def test_dual_polarization_requires_both_vv_and_vh_drop():
    before_vv = np.array([[1.0, 1.0]])
    after_vv = np.array([[0.1, 0.5]])
    before_vh = np.array([[1.0, 1.0]])
    after_vh = np.array([[0.1, 0.5]])

    result, diagnostics = dual_polarization_flood_mask(
        before_vv, after_vv, before_vh, after_vh
    )

    assert result.tolist() == [[True, False]]
    assert diagnostics["vv_threshold_db"] == -3.0
    assert diagnostics["vh_threshold_db"] == -2.0


def test_dual_polarization_valid_mask():
    arrays = [
        np.ones((1, 2)),
        np.array([[0.1, 0.1]]),
        np.ones((1, 2)),
        np.array([[0.1, 0.1]]),
    ]
    result, _ = dual_polarization_flood_mask(
        *arrays,
        valid_mask=np.array([[1, 0]]),
    )
    assert result.tolist() == [[True, False]]
