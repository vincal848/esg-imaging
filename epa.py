"""EPA GHGRP and ECHO tables as plain dicts (M2 facilities, M5 outcome).

Pure: every function takes already-read rows (lists of dicts keyed by the file's
own headers) so tests feed fixtures; `run_h2.py` does the file reading.
Sources (public domain, no account): GHGRP data summary spreadsheets and parent
company file; ECHO case downloads. Facilities are keyed by GHGRP facility id,
enforcement by FRS registry id, which GHGRP also carries.
"""

from collections import Counter
from typing import Iterable

from assets import Facility

# NAICS prefixes in scope: agriculture/forestry, mining + oil & gas extraction, wood, paper.
SCOPE_PREFIXES = ("11", "21", "321", "322")


def in_scope(naics: str) -> bool:
    return naics.startswith(SCOPE_PREFIXES)


def facilities_with_owners(coords: Iterable[dict], parents: Iterable[dict]) -> tuple[list[Facility], dict[str, str]]:
    """In-scope facilities with coordinates, owned by their largest-share parent.

    `coords`: rows with 'Facility Id','FRS Id','Facility Name','Latitude','Longitude'
    ("Direct Point Emitters"). `parents`: rows of the parent-company sheet.
    Returns (facilities, {facility name: FRS id}); `Facility.notes` holds the GHGRP id.
    """
    best: dict[str, dict] = {}
    for r in parents:
        k = str(int(r["GHGRP FACILITY ID"]))
        if k not in best or (r["PARENT CO. PERCENT OWNERSHIP"] or 0) > (best[k]["PARENT CO. PERCENT OWNERSHIP"] or 0):
            best[k] = r
    out, frs = [], {}
    for c in coords:
        k = str(int(c["Facility Id"]))
        p = best.get(k)
        if p is None or c["Latitude"] is None or c["Longitude"] is None or not c["FRS Id"]:
            continue
        naics = str(p["FACILITY NAICS CODE"] or "")
        if not in_scope(naics):
            continue
        out.append(Facility(k, p["PARENT COMPANY NAME"], naics, float(c["Latitude"]),
                            float(c["Longitude"]), "ghgrp_point_emitter", "EPA GHGRP 2023", k))
        frs[k] = str(c["FRS Id"])
    return out, frs


def enforcement_counts(conclusions: Iterable[dict], conclusion_facilities: Iterable[dict]
                       ) -> tuple[Counter, int]:
    """(Counter {(registry id, year): distinct conclusions}, n dropped for no date).

    `conclusions`: ECHO CASE_ENFORCEMENT_CONCLUSIONS rows; `conclusion_facilities`:
    CASE_ENFORCEMENT_CONCLUSION_FACILITIES rows. Year is the settlement-entered date.
    """
    year, dropped = {}, 0
    for r in conclusions:
        d = r["SETTLEMENT_ENTERED_DATE"]  # MM/DD/YYYY
        if len(d) == 10:
            year[r["ENF_CONCLUSION_ID"]] = int(d[-4:])
        else:
            dropped += 1
    seen = {(f["ENF_CONCLUSION_ID"], f["FACILITY_UIN"]) for f in conclusion_facilities}
    counts = Counter((uin, year[cid]) for cid, uin in seen if cid in year)
    return counts, dropped


def informal_counts(rows: Iterable[dict]) -> Counter:
    """Counter {(registry id, year): distinct informal EPA enforcement actions}.

    `rows`: ECHO EPA_INFORMAL_ENFORCEMENT_ACTIONS (notices of violation/noncompliance and
    similar); year is ACHIEVED_DATE (MM/DD/YYYY); rows without a date are skipped."""
    seen = {(r["REGISTRY_ID"], r["ENF_IDENTIFIER"], r["ACHIEVED_DATE"][-4:])
            for r in rows if len(r["ACHIEVED_DATE"]) == 10}
    return Counter((reg, int(y)) for reg, _, y in seen)
