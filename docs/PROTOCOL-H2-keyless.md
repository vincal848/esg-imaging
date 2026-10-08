# Protocol H2-keyless: excess forest loss near facilities vs later EPA enforcement

Written 2026-10-08 BEFORE any forest-loss value or enforcement-vs-signal
relationship was computed. Only facility/company counts and file layouts had been
looked at. Commit history shows the order.

## What this tests (and what it does not)

Question: does excess forest loss (Hansen GFC) near a company's US facilities
lead EPA federal civil enforcement settlements at those facilities?

This is **not** a test against ESG ratings (no licensed export is available) and
**not** a returns test (no legal keyless firm-level price source was found: Stooq
served HTML, Yahoo forbids scraping, Ken French is industry-level). It tests
"satellite signal leads a regulatory event". A null here says nothing about
ratings.

## Data (all keyless; URLs and sha256 in `fetch_data.py`)

- Facilities: EPA GHGRP 2023 data-summary spreadsheets (public domain), sheet
  "Direct Point Emitters" only, for lat/lon. The basin-level sheets (onshore
  production, gathering) report the company office address as the coordinate and
  are excluded. Parent company and ownership: EPA `ghgp_data_parent_company.xlsb`
  (2023 sheet); the parent with the largest ownership share is the owner.
- Tickers: Nasdaq Trader symbol directory (non-ETF, non-test rows), exact
  match on `matching.normalize`. (SEC's `company_tickers.json` rejects requests
  without a real contact in the User-Agent; no contact is invented.)
- Forest loss: Hansen GFC-2024-v1.12 `lossyear` tiles (CC BY 4.0), loss years
  2001-2024.
- Outcome: EPA ECHO case downloads (public domain). Join
  `CASE_ENFORCEMENT_CONCLUSION_FACILITIES.FACILITY_UIN` (FRS id) to the GHGRP
  FRS id, date from `CASE_ENFORCEMENT_CONCLUSIONS.SETTLEMENT_ENTERED_DATE`.

## Definitions (fixed)

- Scope: GHGRP facilities with primary NAICS prefix 11, 21, 321 or 322
  (agriculture/forestry, mining and oil and gas extraction, wood, paper), with
  coordinates, an FRS id, and an owner whose name matches a listed ticker.
- Signal x[c, t]: per facility, `forest.excess_loss_by_year` with buffer
  radius 2 km and ring 2-10 km (the ring stands in for the regional baseline);
  missing years in the output are 0 ha. Company value = equal-weight mean over
  the company's facilities (`esg_signal.aggregate_facility_signals`). Facilities
  within 10 km of a 10-degree tile edge are excluded and counted (no mosaicking).
- Outcome y[c, t]: per facility, the number of distinct enforcement conclusions
  with settlement-entered year t; company value = equal-weight mean over
  facilities. Conclusions without a date are dropped and counted.
- Panel: companies x years 2001-2024, balanced by construction (zeros are real
  zeros). Companies need >= 1 usable facility.
- Test: `evaluate.confirmatory_test(x, y, split, lag=1, seed=0)`, two-way fixed
  effects, company-clustered errors, normal approximation.
- Split fixed in advance: `split` = index of year 2011, so the test uses
  periods 2011-2024 (x at t-1 against y at t). 2001-2010 is burn-in and is not
  used. No parameter above is tuned on any data.
- Placebo: the shuffled-across-companies run inside `confirmatory_test`
  (seed 0). It must come back null (p > 0.05) or the result is void.

## Decision rule

One test, run once. "Signal leads enforcement" is claimed only if beta > 0,
p < 0.05, and the placebo p > 0.05. Anything else is reported as no edge. Number
of tests run: 1. The pipeline is also run once on signal-free synthetic panels
(tests) before this.

## Known limits, stated now

- Number of companies is small (about 43, a data-driven consequence of the
  exact-name ticker match); power is low, so a null is weak evidence of absence.
- Owner and coordinates are 2023 vintage applied to all years (look-ahead on
  ownership). Many oil and gas sites are not near forest; forest loss may also
  be fire or logging, not company activity.
- Enforcement counts mix statutes and are driven by agency priorities that vary
  by year; period effects absorb the common part only.
- Equal-weight mean over facilities treats a small and a large site alike.
