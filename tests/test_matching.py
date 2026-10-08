"""Tests for matching.py and assets column mapping."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

import assets
import matching

SEC = ('{"0":{"cik_str":34088,"ticker":"XOM","title":"EXXON MOBIL CORP"},'
       '"1":{"cik_str":93410,"ticker":"CVX","title":"Chevron Corp"}}')


def _fac(company):
    return assets.Facility("f", company, "s", 0.0, 0.0, "oil_gas")


def test_normalize_drops_suffixes_and_punctuation():
    assert matching.normalize("Exxon Mobil Corporation") == "exxon mobil"
    assert matching.normalize("AT&T Inc.") == "at and t"


def test_match_and_coverage_report_the_gap():
    index = matching.parse_sec_tickers(SEC)
    facs = [_fac("Exxon Mobil Corporation"), _fac("Exxon Mobil Corporation"),
            _fac("Chevron Corporation"), _fac("Fictional Oil Co")]
    m = matching.match_tickers(facs, index)
    assert m == {"Exxon Mobil Corporation": "XOM", "Chevron Corporation": "CVX",
                 "Fictional Oil Co": None}
    assert matching.coverage(facs, m) == pytest.approx(0.75)


def test_coverage_of_nothing_is_an_error():
    with pytest.raises(ValueError):
        matching.coverage([], {})


def test_load_facilities_with_a_tracker_column_mapping(tmp_path):
    p = tmp_path / "gem.csv"
    p.write_text("Name,Parent,Fuel,Latitude,Longitude,Type\n"
                 "Field,Acme Oil,oil,10.5,20.5,oil_gas\n")
    cols = {"facility": "Name", "company": "Parent", "sector": "Fuel",
            "lat": "Latitude", "lon": "Longitude", "facility_type": "Type"}
    (f,) = assets.load_facilities(str(p), columns=cols)
    assert (f.company, f.lat, f.lon) == ("Acme Oil", 10.5, 20.5)
    with pytest.raises(ValueError):
        assets.load_facilities(str(p))  # unmapped headers are rejected
