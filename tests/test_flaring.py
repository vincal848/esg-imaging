"""Tests for flaring.py: VIIRS Nightfire detections inside facility buffers."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pytest

import flaring

CSV = (
    "Date_Mscan,Lat_GMTCO,Lon_GMTCO,RH\n"
    "2024-01-15 01:00:00,29.75,-95.37,10.0\n"   # at the facility
    "2024-02-10 01:00:00,29.76,-95.37,5.0\n"    # ~1.1 km north
    "2024-05-10 01:00:00,29.75,-95.37,7.0\n"    # Q2
    "2024-01-20 01:00:00,40.00,-100.0,99.0\n"   # far away
)


def test_parse_nightfire_csv_reads_columns_and_quarters():
    det = flaring.parse_nightfire_csv(CSV)
    assert len(det.lat) == 4
    assert list(det.period) == ["2024Q1", "2024Q1", "2024Q2", "2024Q1"]
    assert det.rh[0] == pytest.approx(10.0)


def test_parse_nightfire_csv_raises_on_missing_column():
    with pytest.raises(ValueError):
        flaring.parse_nightfire_csv("Date_Mscan,Lat_GMTCO\n2024-01-01,1.0\n")


def test_flare_in_buffer_sums_only_detections_inside_the_radius():
    det = flaring.parse_nightfire_csv(CSV)
    out = flaring.flare_in_buffer(det, 29.75, -95.37, radius_km=2.0)
    assert out["2024Q1"] == pytest.approx(15.0)
    assert out["2024Q2"] == pytest.approx(7.0)
    tight = flaring.flare_in_buffer(det, 29.75, -95.37, radius_km=0.5)
    assert tight["2024Q1"] == pytest.approx(10.0)


def test_flare_in_buffer_is_empty_when_nothing_is_detected():
    det = flaring.parse_nightfire_csv(CSV)
    assert flaring.flare_in_buffer(det, 0.0, 0.0, radius_km=5.0) == {}


def test_flaring_intensity_divides_by_production_and_skips_zero_production():
    flare = {("A", "2024Q1"): 30.0, ("B", "2024Q1"): 5.0}
    prod = {("A", "2024Q1"): 10.0, ("B", "2024Q1"): 0.0}
    out = flaring.flaring_intensity(flare, prod)
    assert out == {("A", "2024Q1"): pytest.approx(3.0)}


def test_eog_credentials_are_required_and_named(monkeypatch):
    monkeypatch.delenv("EOG_USERNAME", raising=False)
    monkeypatch.delenv("EOG_PASSWORD", raising=False)
    with pytest.raises(flaring.MissingCredentials, match="EOG_USERNAME"):
        flaring.eog_credentials()
    monkeypatch.setenv("EOG_USERNAME", "u")
    monkeypatch.setenv("EOG_PASSWORD", "p")
    assert flaring.eog_credentials() == ("u", "p")
