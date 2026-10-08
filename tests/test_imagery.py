"""Tests for imagery.py: NDVI, cloud masking, change detection, baselines."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pytest

import imagery


def test_ndvi_of_healthy_vegetation_reflectance_is_about_0_8():
    nir = np.array([0.45])
    red = np.array([0.05])
    assert imagery.ndvi(nir, red)[0] == pytest.approx(0.8)


def test_ndvi_of_water_reflectance_is_negative():
    nir = np.array([0.01])
    red = np.array([0.02])
    assert imagery.ndvi(nir, red)[0] < 0.0


def test_ndvi_of_bare_soil_is_between_0_1_and_0_2():
    nir = np.array([0.20])
    red = np.array([0.15])
    value = imagery.ndvi(nir, red)[0]
    assert 0.1 < value < 0.2


def test_ndvi_handles_uint16_scaled_reflectance():
    nir_dn = np.array([4500], dtype=np.uint16)
    red_dn = np.array([500], dtype=np.uint16)
    value = imagery.ndvi(nir_dn, red_dn, scale=1.0 / 10000.0)[0]
    assert value == pytest.approx(0.8)


def test_ndvi_of_a_zero_sum_pixel_is_nan_not_inf_or_error():
    nir = np.array([0.0, 0.3])
    red = np.array([0.0, 0.1])
    out = imagery.ndvi(nir, red)
    assert np.isnan(out[0])
    assert np.isfinite(out[1])


def test_cloud_mask_keeps_only_allowed_scl_classes():
    scl = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    mask = imagery.cloud_mask_from_scl(scl, keep=(4, 5, 6))
    expected = np.isin(scl, (4, 5, 6))
    assert np.array_equal(mask, expected)
    assert mask.sum() == 3


def test_masked_mean_ignores_masked_and_nan_pixels():
    values = np.array([1.0, np.nan, 3.0, 100.0])
    mask = np.array([True, True, True, False])
    # Only index 0 and 2 survive: masked-in and not nan.
    assert imagery.masked_mean(values, mask) == pytest.approx(2.0)


def test_masked_mean_is_nan_when_nothing_survives_the_mask():
    values = np.array([1.0, 2.0])
    mask = np.array([False, False])
    assert np.isnan(imagery.masked_mean(values, mask))


def test_a_synthetic_clearing_is_detected_with_the_exact_area():
    before = np.full((20, 20), 0.8)
    after = np.full((20, 20), 0.8)
    after[5:15, 5:15] = 0.2  # a 10x10 cleared square

    loss_mask, area_ha = imagery.ndvi_change(before, after, threshold=0.3,
                                              pixel_size_m=10.0)

    expected_mask = np.zeros((20, 20), dtype=bool)
    expected_mask[5:15, 5:15] = True
    assert np.array_equal(loss_mask, expected_mask)

    # 100 pixels at 10m x 10m = 100 x 100 m^2 = 10,000 m^2 = 1.0 ha.
    assert area_ha == pytest.approx(1.0)


def test_noise_below_the_threshold_is_not_flagged():
    before = np.full((10, 10), 0.6)
    after = before - 0.05  # well under a 0.3 drop threshold

    loss_mask, area_ha = imagery.ndvi_change(before, after, threshold=0.3,
                                              pixel_size_m=10.0)

    assert not loss_mask.any()
    assert area_ha == pytest.approx(0.0)


def test_ndvi_change_raises_on_mismatched_shapes():
    before = np.zeros((5, 5))
    after = np.zeros((4, 4))
    with pytest.raises(ValueError):
        imagery.ndvi_change(before, after, threshold=0.3, pixel_size_m=10.0)


def test_seasonal_baseline_is_the_median_of_images_within_the_window():
    stack = np.array([
        np.full((2, 2), 1.0),
        np.full((2, 2), 2.0),
        np.full((2, 2), 3.0),
        np.full((2, 2), 100.0),  # far from the target doy, must be excluded
    ])
    doy = np.array([10, 15, 20, 200])

    baseline = imagery.seasonal_baseline(stack, doy, target_doy=15, window=10)
    # Images at doy 10, 15, 20 are within 10 days of 15; median of 1, 2, 3 is 2.
    assert np.all(baseline == 2.0)


def test_seasonal_baseline_wraps_around_the_year_boundary():
    stack = np.array([
        np.full((2, 2), 1.0),   # doy 360
        np.full((2, 2), 3.0),   # doy 5
        np.full((2, 2), 100.0),  # doy 180, far away
    ])
    doy = np.array([360, 5, 180])

    # Target doy 1 is 6 days from doy 360 (365 - 360 + 1) and 4 days from
    # doy 5 -- both within a 10-day window only if wraparound is handled.
    baseline = imagery.seasonal_baseline(stack, doy, target_doy=1, window=10)
    assert np.all(baseline == 2.0)  # median of 1.0 and 3.0


def test_seasonal_baseline_raises_when_no_images_are_in_window():
    stack = np.array([np.full((2, 2), 1.0)])
    doy = np.array([1])
    with pytest.raises(ValueError):
        imagery.seasonal_baseline(stack, doy, target_doy=180, window=5)


def test_buffer_loss_ha_counts_only_cleared_pixels_inside_the_buffer():
    # Four dates; baseline target doy 100 uses the first three (all NDVI 0.8).
    stack = np.full((4, 20, 20), 0.8)
    doy = np.array([95, 100, 105, 300])
    stack[3, 5:15, 5:15] = 0.2  # 10x10 clearing on the "current" date
    buffer_mask = np.zeros((20, 20), dtype=bool)
    buffer_mask[:, :10] = True  # buffer covers half of the clearing (50 px)

    area_ha = imagery.buffer_loss_ha(stack, doy, current=3, target_doy=100,
                                     buffer_mask=buffer_mask, threshold=0.3,
                                     pixel_size_m=10.0, window=15)
    assert area_ha == pytest.approx(0.5)


def test_buffer_loss_ha_ignores_pixels_masked_as_cloud_on_the_current_date():
    stack = np.full((2, 4, 4), 0.8)
    doy = np.array([100, 300])
    stack[1] = np.nan  # fully clouded current scene: no comparison possible
    area_ha = imagery.buffer_loss_ha(stack, doy, current=1, target_doy=100,
                                     buffer_mask=np.ones((4, 4), dtype=bool),
                                     threshold=0.3, pixel_size_m=10.0)
    assert area_ha == pytest.approx(0.0)
