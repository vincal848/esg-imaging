"""Tests for forest.py: Hansen tile naming and excess-loss-versus-ring."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pytest

import forest


def test_tile_id_uses_the_upper_left_corner():
    assert forest.tile_id(45.5, -73.57) == "50N_080W"
    assert forest.tile_id(-23.55, -46.63) == "20S_050W"
    assert forest.tile_id(29.75, -95.37) == "30N_100W"
    assert forest.tile_id(5.0, 10.0) == "10N_010E"


def test_tile_url_matches_the_published_pattern():
    assert forest.tile_url(45.5, -73.57) == (
        "https://storage.googleapis.com/earthenginepartners-hansen/"
        "GFC-2024-v1.12/Hansen_GFC-2024-v1.12_lossyear_50N_080W.tif")


def _window(inner_loss_frac, ring_loss_frac, seed=0):
    rng = np.random.default_rng(seed)
    d = np.arange(-100, 101) * 0.001
    lon_grid, lat_grid = np.meshgrid(d, d)
    dist = np.hypot(lat_grid, lon_grid) * 111.195
    loss = np.zeros(lat_grid.shape, dtype=np.uint8)
    inner = dist <= 5
    ring = (dist > 5) & (dist <= 10)
    loss[inner & (rng.random(loss.shape) < inner_loss_frac)] = 20
    loss[ring & (rng.random(loss.shape) < ring_loss_frac)] = 20
    return forest.LossWindow(loss, lat_grid, lon_grid, pixel_area_ha=1.0)


def test_excess_loss_is_near_zero_when_buffer_matches_the_ring():
    out = forest.excess_loss_by_year(_window(0.1, 0.1), 0.0, 0.0, 5, 10)
    inner_px = 7800
    assert abs(out[2020]) < 0.1 * inner_px * 0.15  # sampling noise only


def test_excess_loss_picks_up_extra_clearing_inside_the_buffer():
    out = forest.excess_loss_by_year(_window(0.4, 0.1), 0.0, 0.0, 5, 10)
    assert out[2020] > 0.25 * 7000


def test_excess_loss_needs_a_ring():
    with pytest.raises(ValueError):
        forest.excess_loss_by_year(_window(0.1, 0.1), 0.0, 0.0, 5, 5)


def test_read_loss_window_from_a_tiny_geotiff(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    path = str(tmp_path / "t.tif")
    data = np.zeros((400, 400), dtype=np.uint8)
    data[190:210, 190:210] = 5
    res = 0.00025
    with rasterio.open(path, "w", driver="GTiff", height=400, width=400, count=1,
                       dtype="uint8", crs="EPSG:4326",
                       transform=from_origin(-80.0, 50.0, res, res)) as dst:
        dst.write(data, 1)
    lat, lon = 50.0 - 200 * res, -80.0 + 200 * res
    win = forest.read_loss_window(path, lat, lon, radius_km=1.0)
    assert (win.lossyear == 5).sum() == pytest.approx(400, abs=40)
    assert win.pixel_area_ha == pytest.approx(0.0497, rel=0.01)  # 27.8 m x 17.9 m at 50N
    out = forest.excess_loss_by_year(win, lat, lon, 0.3, 0.9)
    assert out[2005] > 0
