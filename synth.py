"""Synthetic panels for checking the evaluation code (test and demo use only)."""

import numpy as np


def make_panel(g: int, t: int, beta: float, seed: int, ar: float = 0.7
               ) -> tuple[np.ndarray, np.ndarray]:
    """(x, y): persistent signal x with company effects; y[:, s] = beta * x[:, s-1]
    + company effect + period effect + noise. beta = 0 is the signal-free null."""
    rng = np.random.default_rng(seed)
    x = np.zeros((g, t))
    x[:, 0] = rng.standard_normal(g)
    for s in range(1, t):
        x[:, s] = ar * x[:, s - 1] + rng.standard_normal(g)
    x += rng.standard_normal((g, 1)) * 2
    y = (rng.standard_normal((g, 1)) + rng.standard_normal((1, t))
         + rng.standard_normal((g, t)))
    y[:, 1:] += beta * x[:, :-1]
    return x, y
