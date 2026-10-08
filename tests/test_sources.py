"""Tests for returns.py, ratings.py and sentinel.py (fixture text, no network)."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pytest

import ratings
import returns
import sentinel

FRENCH = """ Average Value Weighted Returns -- Daily
 
,Agric,Oil
19260701,  1.00, -99.99
19260702, -2.00,  0.50
 
 Average Equal Weighted Returns -- Daily
,Agric,Oil
19260701,  9.00,  9.00
"""


def test_parse_french_daily_scales_percent_marks_missing_and_stops_at_table_end():
    out = returns.parse_french_daily(FRENCH)
    dates, agric = out["Agric"]
    assert list(dates) == ["1926-07-01", "1926-07-02"]
    assert agric == pytest.approx([0.01, -0.02])
    assert np.isnan(out["Oil"][1][0]) and out["Oil"][1][1] == pytest.approx(0.005)


def test_parse_french_daily_needs_a_header():
    with pytest.raises(ValueError):
        returns.parse_french_daily("nothing here")


def test_rating_actions_are_changes_within_a_provider():
    text = ("company,provider,date,rating\n"
            "A,P1,2024-01-01,5\nA,P2,2024-01-01,3\nA,P1,2024-06-01,3\nA,P2,2024-07-01,4\n")
    acts = ratings.parse_ratings_csv(text)
    assert [(a.provider, a.change) for a in acts] == [("P1", -2.0), ("P2", 1.0)]
    with pytest.raises(ValueError):
        ratings.parse_ratings_csv("company,date\n")


def test_ratings_path_requires_env(monkeypatch):
    monkeypatch.delenv("ESG_RATINGS_CSV", raising=False)
    with pytest.raises(RuntimeError, match="ESG_RATINGS_CSV"):
        ratings.ratings_path()


def test_sentinel_search_params_bbox_is_centered_with_the_right_width():
    p = sentinel.search_params(45.0, -73.0, 1.0, "2024-01-01", "2024-12-31")
    w, s, e, n = p["bbox"]
    assert (w + e) / 2 == pytest.approx(-73.0) and (s + n) / 2 == pytest.approx(45.0)
    assert (n - s) * 111.195 == pytest.approx(2.0, rel=0.01)
    assert p["datetime"] == "2024-01-01/2024-12-31"
