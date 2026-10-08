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


_CUT = r" - | Common Stock| Ordinary Shares| Class [A-Z]| Depositary"
# H2b: also cut unit/share-class wording ("Energy Transfer LP Common Units").
CUT_V2 = _CUT + r"| Common Units?| Common Shares| Units?| Subordinate Voting| Limited Partner| L\.P\."


def parse_nasdaq_symbols(*texts: str, cut: str = _CUT) -> dict[str, str]:
    """{normalised company name: ticker} from Nasdaq Trader's `nasdaqlisted.txt` and
    `otherlisted.txt` (pipe-delimited, no account). ETFs and test issues are skipped;
    share-class text after the company name is cut. Keyless stand-in for the SEC file."""
    out: dict[str, str] = {}
    for text in texts:
        rows = [ln.split("|") for ln in text.splitlines()]
        head = rows[0]
        sym = head.index("Symbol") if "Symbol" in head else head.index("ACT Symbol")
        etf, test = head.index("ETF"), head.index("Test Issue")
        for r in rows[1:]:
            if len(r) < len(head) or r[etf] == "Y" or r[test] == "Y":
                continue  # also drops the trailing "File Creation Time" line
            name = re.split(cut, r[1])[0]
            out.setdefault(normalize(name), r[sym])
    return out


def match_tickers(facilities: list[Facility], index: dict[str, str]) -> dict[str, str | None]:
    """{company: ticker or None} for every distinct company in `facilities`."""
    return {f.company: index.get(normalize(f.company)) for f in facilities}


def coverage(facilities: list[Facility], matches: dict[str, str | None]) -> float:
    """Fraction of facilities whose company matched a ticker."""
    if not facilities:
        raise ValueError("no facilities")
    return sum(matches[f.company] is not None for f in facilities) / len(facilities)


_DROP = {"the", "companies", "cos"}


def _tokens(name: str) -> list[str]:
    return [t for t in normalize(name).split() if t not in _DROP]


def parse_nasdaq_tokens(index: dict[str, str]) -> dict[str, tuple[str, int]]:
    """{space-free key: (ticker, token count)} from a `parse_nasdaq_symbols` index."""
    out: dict[str, tuple[str, int]] = {}
    for name, ticker in index.items():
        t = _tokens(name)
        if t:
            out.setdefault("".join(t), (ticker, len(t)))
    return out


def match_owner(name: str, keys: dict[str, tuple[str, int]]) -> str | None:
    """Ticker for an owner name: equal to a listed name ignoring spaces and 'the/companies',
    or starting with a listed name of >= 2 words (a subsidiary like 'Duke Energy Carolinas').
    Longest listed name wins. Rule fixed in docs/PROTOCOL-H2b.md."""
    t = _tokens(name)
    for k in range(len(t), 0, -1):
        hit = keys.get("".join(t[:k]))
        if hit and (k == len(t) or hit[1] >= 2):
            return hit[0]
    return None
