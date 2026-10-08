"""Run the H2-keyless confirmatory test once (docs/PROTOCOL-H2-keyless.md).

Needs data/raw from `python fetch_data.py` and requirements-geo.txt. Writes
data/h2_result.json and prints the result table. Do not edit parameters after
seeing a result: they are the protocol's.
"""

import csv
import io
import json
import os
import zipfile

import openpyxl
from pyxlsb import open_workbook

import epa
import evaluate
import forest
import matching
import panel

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")
YEARS = range(2001, 2025)
SPLIT_YEAR = 2011
BUFFER_KM, RING_KM = 2.0, 10.0


def _sheet_rows(rows, header_at):
    it = iter(rows)
    for _ in range(header_at):
        next(it)
    head = list(next(it))
    return [dict(zip(head, r)) for r in it]


def read_inputs():
    with zipfile.ZipFile(os.path.join(RAW, "ghgrp.zip")) as z, z.open("ghgp_data_by_year_2023.xlsx") as f:
        ws = openpyxl.load_workbook(io.BytesIO(f.read()), read_only=True)["Direct Point Emitters"]
        coords = _sheet_rows(ws.iter_rows(values_only=True), 3)
    with open_workbook(os.path.join(RAW, "parent.xlsb")) as wb, wb.get_sheet("2023") as sh:
        parents = _sheet_rows(([c.v for c in r] for r in sh.rows()), 0)
    text = lambda n: open(os.path.join(RAW, n), encoding="latin1").read()
    index = matching.parse_nasdaq_symbols(text("nasdaqlisted.txt"), text("otherlisted.txt"))
    with zipfile.ZipFile(os.path.join(RAW, "case.zip")) as z:
        def table(name):
            return list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding="latin1")))
        counts, no_date = epa.enforcement_counts(table("CASE_ENFORCEMENT_CONCLUSIONS.csv"),
                                                 table("CASE_ENFORCEMENT_CONCLUSION_FACILITIES.csv"))
    return coords, parents, index, counts, no_date


def main() -> dict:
    coords, parents, index, counts, no_date = read_inputs()
    facs, frs = epa.facilities_with_owners(coords, parents)
    tickers = matching.match_tickers(facs, index)
    matched = [f for f in facs if tickers[f.company]]
    kept = [f for f in matched if not forest.near_tile_edge(f.lat, f.lon, RING_KM)]
    cov = {"in_scope_located_facilities": len(facs), "matched_to_ticker": len(matched),
           "ticker_coverage": round(matching.coverage(facs, tickers), 3),
           "edge_excluded": len(matched) - len(kept), "facilities_used": len(kept)}

    loss, enf, company = {}, {}, {}
    for f in kept:
        tile = os.path.join(RAW, "hansen", "Hansen_GFC-2024-v1.12_lossyear_%s.tif" % forest.tile_id(f.lat, f.lon))
        win = forest.read_loss_window(tile, f.lat, f.lon, RING_KM)
        for y, ha in forest.excess_loss_by_year(win, f.lat, f.lon, BUFFER_KM, RING_KM).items():
            loss[(f.facility, y)] = ha
        for y in YEARS:
            enf[(f.facility, y)] = float(counts.get((frs[f.facility], y), 0))
        company[f.facility] = tickers[f.company]
    names, x = panel.company_matrix(company, loss, YEARS)
    _, y = panel.company_matrix(company, enf, YEARS)

    split = YEARS.index(SPLIT_YEAR)
    test, placebo = evaluate.confirmatory_test(x, y, split, lag=1, seed=0)
    cov.update(companies=len(names), enforcement_without_date=no_date,
               facility_years_with_enforcement=sum(v > 0 for v in enf.values()),
               facility_years_with_nonzero_signal=len(loss))
    out = {"coverage": cov, "test": test.__dict__, "placebo": placebo.__dict__}
    with open(os.path.join(RAW, "..", "h2_result.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


if __name__ == "__main__":
    r = main()
    print(json.dumps(r["coverage"], indent=1))
    print("%-8s %9s %9s %7s %7s %6s" % ("", "beta", "se", "t", "p", "n_obs"))
    for k in ("test", "placebo"):
        v = r[k]
        print("%-8s %9.4g %9.4g %7.2f %7.3f %6d" % (k, v["beta"], v["se"], v["t"], v["p"], v["n_obs"]))
