"""power_h2b.power: near the nominal rate with no effect, near 1 with a big one."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import power_h2b


def test_power_simulation_has_null_and_signal_ends():
    assert power_h2b.power(80, 14, 0.0, 0.05, 150) < 0.15
    assert power_h2b.power(80, 14, 0.3, 0.05, 50) > 0.95
