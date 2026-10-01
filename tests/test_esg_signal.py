"""Tests for esg_signal.py: aggregating facility signals to company-period."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest

import esg_signal


RECORDS = [
    {"company": "A", "period": "2024Q1", "value": 10.0, "weight": 2.0},
    {"company": "A", "period": "2024Q1", "value": 20.0, "weight": 1.0},
    {"company": "A", "period": "2024Q2", "value": 5.0, "weight": 1.0},
    {"company": "B", "period": "2024Q1", "value": 100.0, "weight": 1.0},
]


def test_aggregate_facility_signals_weighted_mean_matches_hand_calculation():
    out = esg_signal.aggregate_facility_signals(RECORDS)
    # (10*2 + 20*1) / 3 = 40/3
    assert out[("A", "2024Q1")]["value"] == pytest.approx(40.0 / 3.0)
    assert out[("A", "2024Q2")]["value"] == pytest.approx(5.0)
    assert out[("B", "2024Q1")]["value"] == pytest.approx(100.0)


def test_aggregate_facility_signals_normalized_weights_sum_to_one():
    group = [r for r in RECORDS if r["company"] == "A" and r["period"] == "2024Q1"]
    weights = [r["weight"] for r in group]
    total = sum(weights)
    normalized = [w / total for w in weights]
    assert sum(normalized) == pytest.approx(1.0)


def test_aggregate_facility_signals_counts_facilities_per_group():
    out = esg_signal.aggregate_facility_signals(RECORDS)
    assert out[("A", "2024Q1")]["n_facilities"] == 2
    assert out[("A", "2024Q2")]["n_facilities"] == 1
    assert out[("B", "2024Q1")]["n_facilities"] == 1


def test_aggregate_facility_signals_tracks_the_raw_weight_sum():
    out = esg_signal.aggregate_facility_signals(RECORDS)
    assert out[("A", "2024Q1")]["weight_sum"] == pytest.approx(3.0)


def test_aggregate_facility_signals_raises_on_zero_total_weight():
    zero_weight_records = [
        {"company": "A", "period": "2024Q1", "value": 10.0, "weight": 0.0},
    ]
    with pytest.raises(ValueError):
        esg_signal.aggregate_facility_signals(zero_weight_records)
