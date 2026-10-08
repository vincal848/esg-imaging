"""Simulated power of evaluate.confirmatory_test's lag-1 test at a given panel size.

Standardised effect: y[t] = rho * x[t-1] + e with x, e unit-variance within company
(plus company and period effects). rho is therefore the within correlation, in y-SD
per x-SD. Usage: python power_h2b.py G [periods=14] [alpha=0.025] [sims=300]
"""

import sys

import numpy as np

import evaluate


def power(g: int, t: int, rho: float, alpha: float, sims: int, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(sims):
        x = rng.standard_normal((g, t + 1)) + rng.standard_normal((g, 1))
        y = rng.standard_normal((g, t + 1)) + rng.standard_normal((g, 1)) + rng.standard_normal((1, t + 1))
        y[:, 1:] += rho * x[:, :-1]
        hits += evaluate.panel_test(x[:, 1:], y[:, 1:], lag=1).p < alpha
    return hits / sims


if __name__ == "__main__":
    g = int(sys.argv[1])
    t = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    a = float(sys.argv[3]) if len(sys.argv) > 3 else 0.025
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 300
    print("G=%d T=%d alpha=%g" % (g, t, a))
    for rho in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.15):
        print("  rho %.2f  power %.2f" % (rho, power(g, t, rho, a, n)))
