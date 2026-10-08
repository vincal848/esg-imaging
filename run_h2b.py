"""H2b (docs/PROTOCOL-H2b.md). Two phases:

  python run_h2b.py sample   build the sample and its forest-loss signal, print sizes
  python run_h2b.py test     run the pre-registered test once on that sample

`sample` never reads enforcement data. Needs data/raw from fetch_data.py.
"""

import csv
import json
import os
import sys

import epa
import evaluate
import forest
import matching
import panel
import run_h2 as base

CACHE = os.path.join(base.RAW, "..", "h2b_sample.json")
ALIASES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "owner_aliases.csv")


def owner_ticker(keys: dict, aliases: dict[str, str]):
    return lambda name: aliases.get(matching.normalize(name)) or matching.match_owner(name, keys)


def sample() -> dict:
    coords, parents = base.read_ghgrp()
    epa.SCOPE_PREFIXES = ("",)  # H2b: any NAICS
    facs, frs = epa.facilities_with_owners(coords, parents)
    keys = matching.parse_nasdaq_tokens(base.read_nasdaq(cut=matching.CUT_V2))
    with open(ALIASES, newline="") as f:
        aliases = {matching.normalize(r["owner"]): r["ticker"] for r in csv.DictReader(f)}
    tick = owner_ticker(keys, aliases)
    matched = [f for f in facs if tick(f.company)]
    inner = [f for f in matched if not forest.near_tile_edge(f.lat, f.lon, base.RING_KM)]
    loss, company, no_forest = {}, {}, 0
    for f in inner:
        tile = os.path.join(base.RAW, "hansen", "Hansen_GFC-2024-v1.12_lossyear_%s.tif" % forest.tile_id(f.lat, f.lon))
        win = forest.read_loss_window(tile, f.lat, f.lon, base.RING_KM)
        if not (win.lossyear > 0).any():
            no_forest += 1
            continue
        for y, ha in forest.excess_loss_by_year(win, f.lat, f.lon, base.BUFFER_KM, base.RING_KM).items():
            loss["%s|%d" % (f.facility, y)] = ha
        company[f.facility] = tick(f.company)
    out = {"in_scope_located_facilities": len(facs), "matched_to_ticker": len(matched),
           "ticker_coverage": round(len(matched) / len(facs), 3),
           "tiles": len({forest.tile_id(f.lat, f.lon) for f in matched}),
           "edge_excluded": len(matched) - len(inner), "no_forest_in_10km": no_forest,
           "facilities_used": len(company), "companies": len(set(company.values())),
           "company": company, "frs": {k: frs[k] for k in company}, "loss": loss}
    with open(CACHE, "w") as f:
        json.dump(out, f)
    return out


def test() -> dict:
    s = json.load(open(CACHE))
    company, frs = s["company"], s["frs"]
    loss = {(k.split("|")[0], int(k.split("|")[1])): v for k, v in s["loss"].items()}
    settle, _ = epa.enforcement_counts(*base.read_echo("CASE_ENFORCEMENT_CONCLUSIONS.csv",
                                                       "CASE_ENFORCEMENT_CONCLUSION_FACILITIES.csv"))
    informal = epa.informal_counts(base.read_echo("EPA_INFORMAL_ENFORCEMENT_ACTIONS.csv")[0])
    split = base.YEARS.index(base.SPLIT_YEAR)
    _, x = panel.company_matrix(company, loss, base.YEARS)
    res = {}
    for name, counters in (("primary_D", (settle, informal)), ("secondary_settlements", (settle,))):
        y_fy = {(f, y): float(sum(c.get((frs[f], y), 0) for c in counters)) for f in company for y in base.YEARS}
        _, y = panel.company_matrix(company, y_fy, base.YEARS)
        t, p = evaluate.confirmatory_test(x, y, split, lag=1, seed=0)
        res[name] = {"test": t.__dict__, "placebo": p.__dict__,
                     "facility_years_with_event": sum(v > 0 for v in y_fy.values())}
    with open(os.path.join(base.RAW, "..", "h2b_result.json"), "w") as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == "__main__":
    if sys.argv[1:] == ["sample"]:
        r = sample()
        print(json.dumps({k: v for k, v in r.items() if k not in ("company", "frs", "loss")}, indent=1))
    elif sys.argv[1:] == ["test"]:
        for k, v in test().items():
            print(k, "facility-years with event:", v["facility_years_with_event"])
            for w in ("test", "placebo"):
                m = v[w]
                print("  %-8s beta %.4g se %.4g t %.2f p %.4f n %d" % (w, m["beta"], m["se"], m["t"], m["p"], m["n_obs"]))
    else:
        raise SystemExit(__doc__)
