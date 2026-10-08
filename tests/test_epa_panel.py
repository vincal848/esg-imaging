"""Tests for epa.py, panel.py and matching.parse_nasdaq_symbols."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pytest

import epa
import matching
import panel

NASDAQ = ("Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
          "AAA|Acme Oil Corporation - Common Stock|G|N|N|100|N|N\n"
          "ETFX|Acme Oil Bull 2X ETF|G|N|N|100|Y|N\n"
          "File Creation Time: 1008202601:01||||||")
OTHER = ("ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
         "BBB|Beta Paper Inc. Common Stock|N|BBB|N|100|N|BBB\n"
         "TST|Test Corp Common Stock|N|TST|N|100|Y|TST")


def test_nasdaq_symbols_skip_etfs_tests_and_share_class_text():
    assert matching.parse_nasdaq_symbols(NASDAQ, OTHER) == {"acme oil": "AAA", "beta paper": "BBB"}


def _coord(fid, frs="1", lat=10.0):
    return {"Facility Id": fid, "FRS Id": frs, "Facility Name": "n", "Latitude": lat, "Longitude": 5.0}


def _parent(fid, name, pct, naics="211120"):
    return {"GHGRP FACILITY ID": fid, "PARENT COMPANY NAME": name,
            "PARENT CO. PERCENT OWNERSHIP": pct, "FACILITY NAICS CODE": naics}


def test_facilities_use_largest_owner_and_drop_out_of_scope_or_unlocated():
    coords = [_coord(1.0), _coord(2.0), _coord(3.0), _coord(4.0, lat=None), _coord(5.0, frs=None)]
    parents = [_parent(1.0, "SMALL CO", 20), _parent(1.0, "BIG CO", 80),
              _parent(2.0, "UTILITY", 100, naics="221112"), _parent(3.0, "PAPER INC", 100, "322121"),
              _parent(4.0, "X", 100), _parent(5.0, "Y", 100)]
    facs, frs = epa.facilities_with_owners(coords, parents)
    assert [(f.facility, f.company) for f in facs] == [("1", "BIG CO"), ("3", "PAPER INC")]
    assert frs == {"1": "1", "3": "1"}


def test_enforcement_counts_distinct_conclusions_per_registry_year():
    conc = [{"ENF_CONCLUSION_ID": "a", "SETTLEMENT_ENTERED_DATE": "03/24/2015"},
            {"ENF_CONCLUSION_ID": "b", "SETTLEMENT_ENTERED_DATE": "01/02/2015"},
            {"ENF_CONCLUSION_ID": "c", "SETTLEMENT_ENTERED_DATE": ""}]
    fac = [{"ENF_CONCLUSION_ID": "a", "FACILITY_UIN": "9"}, {"ENF_CONCLUSION_ID": "a", "FACILITY_UIN": "9"},
           {"ENF_CONCLUSION_ID": "b", "FACILITY_UIN": "9"}, {"ENF_CONCLUSION_ID": "c", "FACILITY_UIN": "9"}]
    counts, dropped = epa.enforcement_counts(conc, fac)
    assert counts == {("9", 2015): 2} and dropped == 1


def test_company_matrix_is_a_per_facility_mean_with_missing_as_zero():
    comps, m = panel.company_matrix({"f1": "A", "f2": "A", "f3": "B"},
                                    {("f1", 2002): 4.0, ("f3", 2001): 1.0}, range(2001, 2003))
    assert comps == ["A", "B"]
    assert np.allclose(m, [[0.0, 2.0], [1.0, 0.0]])


def test_pipeline_finds_a_planted_lead_and_nothing_in_noise():
    # facility-level planted effect, through panel.company_matrix and evaluate
    import evaluate

    rng = np.random.default_rng(0)
    g, t = 60, 14
    x = rng.standard_normal((g, t)) + rng.standard_normal((g, 1))
    for beta, expect_hit in ((0.5, True), (0.0, False)):
        y = rng.standard_normal((g, t))
        y[:, 1:] += beta * x[:, :-1]
        fc = {"f%d" % i: "c%03d" % i for i in range(g)}
        xv = {("f%d" % i, 2001 + s): x[i, s] for i in range(g) for s in range(t)}
        yv = {("f%d" % i, 2001 + s): y[i, s] for i in range(g) for s in range(t)}
        _, xm = panel.company_matrix(fc, xv, range(2001, 2001 + t))
        _, ym = panel.company_matrix(fc, yv, range(2001, 2001 + t))
        test, placebo = evaluate.confirmatory_test(xm, ym, split=2)
        assert (test.p < 0.01) == expect_hit
        assert placebo.p > 0.01
