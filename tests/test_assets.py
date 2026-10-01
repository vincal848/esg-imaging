"""Tests for assets.py: Facility schema loading and validation."""

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

import assets

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "facilities.csv")


def test_load_facilities_reads_the_fixture_rows():
    facilities = assets.load_facilities(FIXTURE)
    assert len(facilities) == 3
    assert all(isinstance(f, assets.Facility) for f in facilities)
    assert facilities[0].company == "Fictional Oil Co"
    assert facilities[0].facility_type == "oil_gas"
    assert facilities[1].lat == pytest.approx(-23.55)


def test_load_facilities_raises_on_missing_required_column(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("facility,company,sector,lat,lon\n"
                        "Site,Co,sector,0.0,0.0\n")  # facility_type missing
    with pytest.raises(ValueError):
        assets.load_facilities(str(bad_csv))


def test_load_facilities_raises_on_out_of_range_latitude(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("facility,company,sector,lat,lon,facility_type\n"
                        "Site,Co,sector,99.0,0.0,oil_gas\n")
    with pytest.raises(ValueError):
        assets.load_facilities(str(bad_csv))


def test_load_facilities_raises_on_non_numeric_lat(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("facility,company,sector,lat,lon,facility_type\n"
                        "Site,Co,sector,not_a_number,0.0,oil_gas\n")
    with pytest.raises(ValueError):
        assets.load_facilities(str(bad_csv))
