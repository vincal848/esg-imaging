# Protocol H2b: power follow-up to H2-keyless (trial 2)

Written 2026-10-08 before any H2b signal or outcome was computed. Before this was
written I looked only at owner names and facility/tile counts (no forest loss, no
enforcement-vs-signal relationship). Everything below is fixed; the sample size and
power are appended in a later commit, still before the test is run.

## Why, and the multiple-testing count

H2-keyless (docs/PROTOCOL-H2-keyless.md, p = 0.365, 39 companies) was null and
underpowered. H2b is one pre-registered attempt to add power with the same
hypothesis. It is **trial 2** of this repo. Bonferroni over the 2 trials: the
decision threshold is **alpha = 0.025** (two-sided), for the primary test only.
Tests actually computed in H2b: 2 (the primary, and the trial-1 outcome on the new
sample as a secondary, which is descriptive and cannot support a claim). Running
total of tests in the repo after H2b: 3. No other signal, lag, radius or outcome
will be run.

## What changes from trial 1

(a) **Owner -> ticker matching** (names only, never tuned on outcomes):
   1. Nasdaq Trader listings (non-ETF, non-test) with unit/share-class wording cut
      (`matching.CUT_V2`).
   2. An owner matches a listed issuer if, ignoring spaces and the words
      the/companies/cos and the usual corporate suffixes, the names are equal, or the
      owner's name starts with a listed name of two or more words (a subsidiary such
      as "Duke Energy Carolinas"). One-word prefixes are refused.
   3. `owner_aliases.csv` (committed with this protocol) is consulted first. Inclusion
      rule: the owner name denotes the listed issuer itself, a former/successor name
      of it, or a US subsidiary named for it. Each row records its public basis.
      Excluded by rule: subsidiaries of foreign parents under a different name
      (BASF, Saint-Gobain, Holcim), private firms, governments, cooperatives, and
      issuers delisted by 2026-10 (US Steel). The table was written from the list of
      unmatched owners ranked by facility count, with names only in view.
   4. Matching is by ticker: owners with the same ticker form one company.

(b) **Scope**: all GHGRP "Direct Point Emitters" with coordinates, FRS id and a
   matched owner, any NAICS. Kept only if forest is plausibly within 10 km, defined as
   at least one Hansen `lossyear` pixel (any year 2001-2024) in the 10 km window;
   Hansen loss exists only where tree cover existed in 2000. Tile budget: at most 40
   tiles (22 are needed; checked in advance). Tile-edge facilities (within 10 km of a
   tile border) are excluded and counted, not mosaicked, since mosaicking needs extra
   tiles for few facilities. The forest filter uses the signal file only, never the
   outcome.

(c) **Outcomes**, fixed now:
   - **Primary: D** = per facility-year, the number of distinct EPA enforcement
     events: federal civil settlements (as in trial 1) plus EPA informal enforcement
     actions (ECHO `EPA_INFORMAL_ENFORCEMENT_ACTIONS`: notices of violation and
     noncompliance, by `ACHIEVED_DATE`). Inspections are not counted: the extract has
     no violation flag, and an inspection alone is not an adverse event.
   - **Secondary (descriptive)**: settlements only (the trial-1 outcome).

(d) **Unchanged**: signal (2 km buffer minus 2-10 km ring excess loss, ha), company
   value = equal-weight mean over facilities (missing facility-years are 0), panel
   2001-2024, split year 2011 (periods 2011-2024), lag 1,
   `evaluate.confirmatory_test` with seed 0 and the shuffled-across-companies placebo.
   Decision rule: claim "signal leads enforcement" only if beta > 0, p < 0.025 and
   placebo p > 0.05. Otherwise no edge.

## Known limits, stated now

Facilities that are landfills, power plants and similar are mostly not near forest,
so the forest filter removes many; owners and coordinates are 2023 vintage; D is
count data with many zeros, which the normal approximation handles imperfectly;
informal actions reflect inspection effort (a facility-level confound that fixed
effects only partly absorb); forest loss includes fire and logging.

## If this is null

The honest end state is "no detectable lead of Hansen forest loss over EPA
enforcement with the keyless data available". More power needs data the repo cannot
get without an account or licence: EOG VIIRS Nightfire flaring (H1), a licensed
ESG ratings export, and a firm-level returns source.

## Pre-run sample and power (appended before the test was run; no outcome read)

`python run_h2b.py sample` (reads only GHGRP, owner names, Hansen tiles):

| | n |
|---|---|
| in-scope located GHGRP point emitters, any NAICS | 6,176 |
| owner matched to a ticker (44.1%) | 2,723 |
| tiles needed (budget 40) | 22 (631 MB + 221 MB; 7 added to `fetch_data.py`) |
| excluded: within 10 km of a tile edge | 141 |
| excluded: no Hansen loss pixel in 10 km | 25 |
| **facilities used** | **2,557** |
| **companies (tickers)** | **242** (trial 1: 39) |

The forest filter removed only 25 facilities: almost every 10 km window contains some
loss pixel, so the sample is effectively "all matched US point emitters" and includes
many non-forest facilities (landfills, power plants), which dilutes any real effect.

Power (`python power_h2b.py G`, 300 simulations per cell, 14 periods, lag 1,
alpha 0.025, normal approximation as in evaluate.py; rho = within correlation of
y[t] with x[t-1], in SD units, with company and period effects):

| rho | 0.02 | 0.04 | 0.06 | 0.08 | 0.10 | 0.15 |
|---|---|---|---|---|---|---|
| power, G = 39 (trial 1) | 0.03 | 0.09 | 0.18 | 0.32 | 0.50 | 0.84 |
| power, G = 242 (H2b) | 0.10 | 0.45 | 0.81 | 0.97 | 1.00 | 1.00 |

Size at rho = 0 (varies by seed): about 0.02-0.04 for G = 242 and 0.00-0.08 for
G = 39, against a nominal 0.025. Minimum detectable effect at 80% power: rho of about
0.06 for H2b, about 0.12 for trial 1. These are upper bounds on real power: D is a
zero-inflated count and the simulation uses Gaussian noise.
