"""Tests for geo.py: haversine distance and facility buffer masks."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pytest

import geo


def test_haversine_of_one_degree_of_latitude_is_about_111_2_km():
    distance = geo.haversine_km(0.0, 0.0, 1.0, 0.0)
    assert distance == pytest.approx(111.2, abs=0.2)


def test_haversine_of_zero_distance_is_zero():
    assert geo.haversine_km(40.0, -73.0, 40.0, -73.0) == pytest.approx(0.0, abs=1e-9)


def test_haversine_broadcasts_a_point_against_a_grid():
    lat_grid, lon_grid = np.meshgrid(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    distances = geo.haversine_km(lat_grid, lon_grid, 0.0, 0.0)
    assert distances.shape == lat_grid.shape
    assert distances[0, 0] == pytest.approx(0.0, abs=1e-9)


def test_meters_per_degree_longitude_shrinks_toward_the_poles():
    _, lon_at_equator = geo.meters_per_degree(0.0)
    _, lon_at_60 = geo.meters_per_degree(60.0)
    # cos(60 deg) = 0.5, so a degree of longitude at 60N is about half as wide.
    assert lon_at_60 == pytest.approx(lon_at_equator * 0.5, rel=1e-3)


def test_meters_per_degree_latitude_is_about_111_km_everywhere():
    lat_at_equator, _ = geo.meters_per_degree(0.0)
    lat_at_60, _ = geo.meters_per_degree(60.0)
    assert lat_at_equator == pytest.approx(111195.0, abs=50.0)
    assert lat_at_60 == pytest.approx(lat_at_equator, abs=1.0)


def test_facility_buffer_mask_radius_is_correct_to_within_a_pixel():
    facility_lat, facility_lon = 0.0, 0.0
    pixel_deg = 0.01
    radius_km = 50.0

    lon_offsets = np.arange(-100, 101) * pixel_deg
    lon_grid = (facility_lon + lon_offsets).reshape(1, -1)
    lat_grid = np.full_like(lon_grid, facility_lat)

    mask = geo.facility_buffer_mask(lat_grid, lon_grid, facility_lat,
                                     facility_lon, radius_km)
    distances = geo.haversine_km(lat_grid, lon_grid, facility_lat, facility_lon)

    pixel_km = geo.haversine_km(0.0, 0.0, 0.0, pixel_deg)

    inside_distances = distances[mask]
    outside_distances = distances[~mask]

    assert inside_distances.max() <= radius_km
    assert outside_distances.min() > radius_km
    # The farthest "inside" pixel and the nearest "outside" pixel must each be
    # within one pixel width of the true radius -- that is the best any
    # rasterized boundary on this grid can do.
    assert (radius_km - inside_distances.max()) <= pixel_km
    assert (outside_distances.min() - radius_km) <= pixel_km


def test_facility_buffer_mask_raises_on_mismatched_grid_shapes():
    lat_grid = np.zeros((3, 3))
    lon_grid = np.zeros((2, 2))
    with pytest.raises(ValueError):
        geo.facility_buffer_mask(lat_grid, lon_grid, 0.0, 0.0, 10.0)
