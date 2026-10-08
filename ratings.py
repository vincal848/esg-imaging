"""ESG rating actions from a licensed vendor export (account-gated, see README).

Expected CSV columns: company, provider, date (YYYY-MM-DD), rating (numeric,
higher = better). A rating action is the change vs the same provider's previous
rating for that company; providers are never pooled (they disagree).
Path comes from env `ESG_RATINGS_CSV`.
"""

import csv
import io
from dataclasses import dataclass

from loaders import require_env


@dataclass(frozen=True)
class RatingAction:
    company: str
    provider: str
    date: str
    change: float


def parse_ratings_csv(text: str) -> list[RatingAction]:
    reader = csv.DictReader(io.StringIO(text))
    need = {"company", "provider", "date", "rating"}
    if not need <= set(reader.fieldnames or []):
        raise ValueError("ratings csv needs columns %s" % sorted(need))
    rows = sorted(reader, key=lambda r: r["date"])
    last: dict[tuple[str, str], float] = {}
    out = []
    for r in rows:
        key, rating = (r["company"], r["provider"]), float(r["rating"])
        if key in last:
            out.append(RatingAction(r["company"], r["provider"], r["date"], rating - last[key]))
        last[key] = rating
    return out


def ratings_path() -> str:
    return require_env("ESG_RATINGS_CSV")[0]
