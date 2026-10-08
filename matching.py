"""Company-name to ticker matching (M2) against SEC's public ticker file.

Source: https://www.sec.gov/files/company_tickers.json (no account; SEC asks for
a descriptive User-Agent header). Matching is exact on a normalised name, which
is deliberately conservative: an unmatched facility is a documented coverage gap,
a wrong match is silent contamination. Fuzzy matching is not attempted.
"""

import json
import re

from assets import Facility

_SUFFIX = re.compile(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|llc|lp|sa|nv|ag|holdings?|group)\b")


def normalize(name: str) -> str:
    name = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " and "))
    return " ".join(_SUFFIX.sub(" ", name).split())


def parse_sec_tickers(text: str) -> dict[str, str]:
    """{normalised company name: ticker}; first listed ticker wins on duplicates."""
    out: dict[str, str] = {}
    for row in json.loads(text).values():
        out.setdefault(normalize(row["title"]), row["ticker"])
    return out


def match_tickers(facilities: list[Facility], index: dict[str, str]) -> dict[str, str | None]:
    """{company: ticker or None} for every distinct company in `facilities`."""
    return {f.company: index.get(normalize(f.company)) for f in facilities}


def coverage(facilities: list[Facility], matches: dict[str, str | None]) -> float:
    """Fraction of facilities whose company matched a ticker."""
    if not facilities:
        raise ValueError("no facilities")
    return sum(matches[f.company] is not None for f in facilities) / len(facilities)
