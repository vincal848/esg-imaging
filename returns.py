"""Free return proxies: Ken French's daily industry portfolios and factors.

Source: Kenneth French Data Library (Dartmouth), no account. Industry-level, not
stock-level: the file `49_Industry_Portfolios_daily_CSV.zip` has Oil, Mines, Agric,
etc., and `F-F_Research_Data_Factors_daily_CSV.zip` has Mkt-RF and RF. Both share
this layout: preamble, a header row starting with a comma, then YYYYMMDD rows in
percent (-99.99 / -999 = missing), ended by a blank line. Unzipping is the caller's job.
"""

import re

import numpy as np

_MISSING = (-99.99, -999.0)


def parse_french_daily(text: str) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """{series name: (dates as 'YYYY-MM-DD' strings, simple returns)}; first table only."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(",")), None)
    if start is None:
        raise ValueError("no header row found")
    names = [n.strip() for n in lines[start].split(",")[1:]]
    dates: list[str] = []
    rows: list[list[float]] = []
    for ln in lines[start + 1:]:
        parts = [p.strip() for p in ln.split(",")]
        if not re.fullmatch(r"\d{8}", parts[0]):
            break
        dates.append("%s-%s-%s" % (parts[0][:4], parts[0][4:6], parts[0][6:]))
        rows.append([float(v) for v in parts[1:]])
    arr = np.array(rows)
    arr[np.isin(arr, _MISSING)] = np.nan
    arr /= 100.0
    d = np.array(dates)
    return {n: (d, arr[:, j]) for j, n in enumerate(names)}
