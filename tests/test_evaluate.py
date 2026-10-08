"""evaluate.py must find nothing in signal-free data and find a planted effect."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pytest

import evaluate
import synth


def test_null_panels_reject_at_about_the_nominal_rate():
    rejections = [
        evaluate.panel_test(*synth.make_panel(80, 20, 0.0, seed), lag=1).p < 0.05
        for seed in range(300)
    ]
    rate = np.mean(rejections)
    assert 0.01 <= rate <= 0.10  # nominal 5%; a broken test is far outside


def test_planted_effect_is_found_with_the_right_size():
    res = evaluate.panel_test(*synth.make_panel(80, 20, 0.15, seed=1), lag=1)
    assert res.p < 0.001
    assert res.beta == pytest.approx(0.15, abs=0.04)


def test_planted_effect_is_found_in_most_seeds():
    hits = [evaluate.panel_test(*synth.make_panel(80, 20, 0.1, s), lag=1).p < 0.05
            for s in range(100)]
    assert np.mean(hits) > 0.9


def test_shuffled_placebo_stays_null_when_the_effect_is_real():
    test, placebo = evaluate.confirmatory_test(
        *synth.make_panel(150, 30, 0.15, seed=2), split=10)
    assert test.p < 0.001
    assert placebo.p > 0.01


def test_fixed_effects_remove_a_pure_company_level_confound():
    # x and y share a company effect and nothing else: must not look significant.
    rng = np.random.default_rng(0)
    c = rng.standard_normal((100, 1)) * 5
    x = c + rng.standard_normal((100, 20)) * 0.1
    y = c + rng.standard_normal((100, 20))
    assert evaluate.panel_test(x, y, lag=1).p > 0.01


def test_panel_test_rejects_bad_input():
    x = np.ones((10, 5))
    with pytest.raises(ValueError):
        evaluate.panel_test(x, x, lag=1)  # no variation
    with pytest.raises(ValueError):
        evaluate.panel_test(x, np.ones((10, 4)), lag=1)
    x[0, 0] = np.nan
    with pytest.raises(ValueError):
        evaluate.panel_test(x, x, lag=1)


def test_car_is_zero_without_an_event_and_finds_a_planted_jump():
    rng = np.random.default_rng(3)
    mkt = rng.standard_normal(300) * 0.01
    stock = 0.0002 + 1.2 * mkt + rng.standard_normal(300) * 0.002
    assert abs(evaluate.market_model_car(stock, mkt, event=200)) < 0.01
    stock[200] -= 0.05
    assert evaluate.market_model_car(stock, mkt, event=200) < -0.04
    with pytest.raises(ValueError):
        evaluate.market_model_car(stock, mkt, event=10)
