"""M5 evaluation: two-way fixed-effects lead/lag test, plus a market-model CAR.

Pure numpy. Panels are balanced arrays of shape (companies, periods). The test
asks: does `x` (a facility signal) at t-lag explain `y` (rating change or
abnormal return) at t, after removing company and period effects, with standard
errors clustered by company? Normal approximation for p-values (needs a decent
number of companies; ponytail: switch to t/wild-bootstrap for G < 30).

To keep the result honest the confirmatory run uses `confirmatory_test`: the
split is fixed before looking, only periods after it are used, and the shuffled-signal
placebo must come back null. It is one test; if several signals or
lags are tried, the caller must count them and correct (Bonferroni at minimum).
"""

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PanelResult:
    beta: float
    se: float
    t: float
    p: float
    n_obs: int


def _demean_two_way(a: np.ndarray) -> np.ndarray:
    return a - a.mean(axis=1, keepdims=True) - a.mean(axis=0, keepdims=True) + a.mean()


def panel_test(x: np.ndarray, y: np.ndarray, lag: int) -> PanelResult:
    """Regress y[:, t] on x[:, t - lag]. lag > 0 is a lead of x over y; lag < 0
    pairs y with FUTURE x; lag = 0 is contemporaneous."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.shape != y.shape or x.ndim != 2:
        raise ValueError("x and y must be 2-D arrays of the same shape")
    if np.isnan(x).any() or np.isnan(y).any():
        raise ValueError("panel must be balanced and nan-free")
    g, t = x.shape
    if abs(lag) >= t - 1 or g < 3:
        raise ValueError("panel too small for lag %d" % lag)
    if lag >= 0:
        xs, ys = x[:, : t - lag], y[:, lag:]
    else:
        xs, ys = x[:, -lag:], y[:, : t + lag]
    xd, yd = _demean_two_way(xs), _demean_two_way(ys)
    sxx = float((xd**2).sum())
    if sxx == 0:
        raise ValueError("signal has no variation after removing fixed effects")
    beta = float((xd * yd).sum() / sxx)
    score = (xd * (yd - beta * xd)).sum(axis=1)
    se = math.sqrt(g / (g - 1) * float((score**2).sum())) / sxx
    tstat = beta / se if se > 0 else float("inf")
    p = math.erfc(abs(tstat) / math.sqrt(2))
    return PanelResult(beta, se, tstat, p, xd.size)


def confirmatory_test(x: np.ndarray, y: np.ndarray, split: int, lag: int = 1,
                      seed: int = 0) -> tuple[PanelResult, PanelResult]:
    """(test, placebo) on periods >= `split` only. The placebo re-runs the same
    test with companies' signals shuffled across companies, which destroys any
    real link but keeps the signal's persistence; it must come back null. (A lead
    of x is NOT a clean placebo: persistent signals correlate with their own future.)"""
    xs, ys = x[:, split:], y[:, split:]
    shuffled = xs[np.random.default_rng(seed).permutation(xs.shape[0])]
    return panel_test(xs, ys, lag), panel_test(shuffled, ys, lag)


def market_model_car(stock: np.ndarray, market: np.ndarray, event: int,
                     est_len: int = 120, half_window: int = 2) -> float:
    """Cumulative abnormal return over [event-half_window, event+half_window],
    with alpha/beta fitted on the `est_len` days before the window. Returns are
    simple daily returns; costs are not modelled here (event study, no trading)."""
    stock, market = np.asarray(stock, dtype=float), np.asarray(market, dtype=float)
    lo, hi = event - half_window, event + half_window + 1
    if lo - est_len < 0 or hi > len(stock):
        raise ValueError("not enough data around the event")
    ms, ss = market[lo - est_len: lo], stock[lo - est_len: lo]
    beta, alpha = np.polyfit(ms, ss, 1)
    return float((stock[lo:hi] - alpha - beta * market[lo:hi]).sum())
