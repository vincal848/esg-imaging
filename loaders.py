"""Typed interfaces for every external data source, plus the credential check.

Each source is a `Protocol`. Tests use the synthetic implementations in
`synth.py`; real implementations live next to the code that parses them
(`flaring.py`, `forest.py`, `matching.py`, `returns.py`, `ratings.py`).
Sources that need an account read credentials from environment variables
(a local, gitignored `.env`) and raise `MissingCredentials` naming them.
"""

import os
from typing import Protocol, Sequence


class MissingCredentials(RuntimeError):
    """An account-gated source was used without its credentials set."""


def require_env(*names):
    """Values of the named env vars, or MissingCredentials listing the unset ones."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise MissingCredentials(
            "set %s (see 'Data you need to obtain' in README.md)"
            % ", ".join(missing))
    return tuple(os.environ[n] for n in names)


class FlareSource(Protocol):
    def detections(self, start: str, end: str):
        """`flaring.Detections` for ISO dates start..end."""


class ForestLossSource(Protocol):
    def loss_year_window(self, lat: float, lon: float, radius_km: float):
        """`forest.LossWindow` (lossyear grid + its lat/lon grids) around a point."""


class ReturnsSource(Protocol):
    def daily_returns(self, series: str) -> "dict[str, float]":
        """Map ISO date -> simple daily return for a named series."""


class RatingsSource(Protocol):
    def actions(self) -> "Sequence[ratings.RatingAction]":  # noqa: F821
        """Rating changes, one per (company, provider, date)."""
