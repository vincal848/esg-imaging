# Satellite-Imagery ESG Signal

[![tests](https://github.com/vincal848/esg-imaging/actions/workflows/tests.yml/badge.svg)](https://github.com/vincal848/esg-imaging/actions/workflows/tests.yml)

This project asks whether you can measure what a company is actually doing at
its physical facilities from free satellite data, and whether that measurement
leads the ESG ratings and controversies that are supposed to be tracking it.
ESG ratings are slow, mostly self-reported, and the big providers disagree
with each other more than you'd want from something investors treat as a
number. A gas flare or a cleared forest patch, on the other hand, is a
physical fact that a satellite recorded on a specific date, independent of
what the company chose to disclose.

I don't know yet whether this works. The two signals below are specific
enough to fail cleanly, which is the point -- a vague "satellites + ESG" idea
can't be wrong, and I'd rather find out early that flaring intensity has no
relationship to downgrades than build five milestones on top of a hunch.

## Hypotheses

**H1 -- flaring intensity predicts rating downgrades.** Among oil & gas
producers, flaring volume per unit of production (not raw flaring volume,
which just tracks company size) measured from VIIRS Nightfire detections
should lead negative ESG rating actions and environmental controversy flags,
because flaring is a routine-maintenance-vs-waste choice regulators and raters
care about and that companies have weak incentive to self-report promptly.

**H2 -- abnormal forest loss near facilities predicts controversies or
returns.** Among agriculture, mining and paper companies with facilities
located using public trackers, forest loss near a facility in excess of the
regional baseline rate should lead both controversy flags and (more
speculatively) negative abnormal returns around disclosure.

**Likely confounders, honestly.** Facility location data is noisy and dated;
a buffer around a reported point can miss the actual operational footprint or
include unrelated land use. Forest loss has obvious non-corporate causes
(wildfire, smallholder clearing, regional deforestation trends) that a single
company's buffer can't separate from company-caused loss without a lot more
care than this scaffold has. Flaring also has legitimate safety reasons
(pressure relief) that look identical in the data to routine waste flaring.
And ESG ratings from different providers disagree enough with each other that
"predicts a downgrade" has to be evaluated against each provider separately,
not against some notional consensus rating. Given all that, a null result --
no useful lead/lag relationship -- is a live possibility and would still be
worth reporting, since "raters already price this in, or it doesn't matter to
them" is itself informative.

## Data

- **VIIRS Nightfire** (NOAA/EOG) -- nightly sub-pixel thermal detections,
  including flare radiant heat and estimated flared gas volume. Free, daily,
  global. Access: NOAA/EOG's VIIRS Nightfire distribution site.
- **Sentinel-2 L2A** -- 10 m surface reflectance, via the Microsoft Planetary
  Computer STAC API (`pystac-client` + `planetary-computer`, free, no
  authentication for search) or the Copernicus Data Space Ecosystem directly.
  Used for NDVI and NDVI change.
- **Hansen Global Forest Change** -- pre-computed annual forest loss at 30 m,
  from Hansen et al. (2013), hosted by the University of Maryland / Google
  Earth Engine. Coarser and slower-updating than a Sentinel-2 change detector,
  but free, pre-validated, and a much cheaper first pass before building a
  custom NDVI-change pipeline.
- **Facility locations** -- Global Energy Monitor's oil & gas and mining
  trackers (free, CSV, company-attributed) for H1/H2's international
  facilities; EPA FLIGHT (Facility Level Information on GreenHouse gases Tool)
  for US-only cross-checks. Both need a company-name matching step, which is
  its own source of error -- ticker/facility mapping is not solved here.
- **Ratings and returns** -- noted but not sourced yet. ESG ratings
  (MSCI/Sustainalytics-style) are generally paywalled; a real version of this
  project either needs institutional access or a public proxy like
  controversy counts from news. Returns are the easy part (any price vendor);
  getting the *rating* side without paying for it is the actual data risk in
  this project, more so than the imagery.

## Method

1. **Facility buffers.** For each facility (lat/lon + type), rasterize a
   circular buffer onto a regular lat/lon grid (`geo.facility_buffer_mask`).
2. **NDVI.** `NDVI = (NIR - Red) / (NIR + Red)` from Sentinel-2 bands B08/B04,
   masked to clear land/water pixels using the SCL band
   (`imagery.cloud_mask_from_scl`).
3. **Seasonal baseline.** Vegetation NDVI has a strong seasonal cycle, so a
   single before/after comparison would confuse "it's winter" with "it was
   cleared." The baseline for a target date is the median NDVI over past
   images within a day-of-year window (`imagery.seasonal_baseline`), and
   change is measured baseline-vs-current, not date-vs-date.
4. **Change detection.** A pixel is flagged as cleared if NDVI drops by more
   than a threshold between baseline and current (`imagery.ndvi_change`),
   converted to hectares using the pixel's ground sample distance. For
   flaring, VIIRS Nightfire detections falling inside a facility's buffer are
   summed instead of thresholded, since they're already discrete
   detections rather than a continuous field.
5. **Aggregation.** Per-facility signals are combined to a company-period
   observation with a weighted mean (`esg_esg_signal.aggregate_facility_signals`),
   weighted by something that approximates facility importance (production
   capacity or acreage, once that data is attached -- equal weights for now).
6. **Event study / panel regression.** Not built yet (M5). The plan is a
   standard event-study around rating-action dates, and a panel regression of
   rating changes or abnormal returns on lagged facility signals with
   company and time fixed effects.

## Milestones

- [x] **M1 -- imagery primitives on arrays.** NDVI, cloud masking, seasonal
      baselines, change detection, buffer-level loss (`imagery.buffer_loss_ha`),
      flare sums in a buffer, equal-weight aggregation; tested on synthetic
      rasters. No downloads.
- [~] **M2 -- facility table for one sector.** Code done: tracker column
      mapping (`assets.load_facilities(columns=...)`), SEC ticker matching and
      coverage (`matching.py`). Not done: the real facility file has not been
      downloaded or matched.
- [~] **M3 -- flaring signal for ~50 oil & gas firms.** Code done:
      Nightfire CSV parsing, buffer sums, intensity (`flaring.py`). Blocked on
      an EOG account and on a production denominator (open question).
- [~] **M4 -- deforestation signal.** Code done: Hansen tile naming/URLs,
      windowed read, excess loss vs a surrounding ring (`forest.py`), Sentinel-2
      search parameters (`sentinel.py`). Not run on real tiles yet.
- [~] **M5 -- event study.** Code done and validated on synthetic data:
      two-way fixed-effects lead/lag test with company-clustered errors,
      shuffled placebo, market-model CAR (`evaluate.py`). No real result exists;
      needs ratings (`ratings.py`) and the signals above.

## Success metrics

- M1: every function in `imagery.py`/`geo.py` has a test against a known
  value or a synthetic case with a hand-computable answer (not just "doesn't
  crash").
- M3/M4: a facility coverage rate (fraction of a sector's production or
  acreage represented by located facilities) reported alongside the signal,
  since a flaring intensity built from 10% facility coverage isn't comparable
  across companies.
- M5: an honest lead/lag result, reported even if it's null, with the
  confounders above addressed well enough that a null result means "no
  relationship found" rather than "buried in noise."

## Status

M1 complete. M2-M5 have tested code but no real data has been downloaded, so
**there is no empirical result yet** -- not even a null.

What runs today (`pytest tests -q`, all on synthetic or fixture data):

- Imagery, buffer and aggregation primitives (M1).
- Parsers for the real file formats: Nightfire CSV, Hansen GeoTIFF tiles,
  SEC ticker JSON, Ken French return files, ratings CSV. The Nightfire column
  names and tracker column maps are from documentation and unverified against
  a real file.
- The evaluation (`evaluate.py`) is checked both ways: on signal-free panels
  it rejects at about the nominal 5% rate (300 simulated panels), and with a
  planted effect it finds it (and recovers its size). Its placebo, which
  shuffles signals across companies, stays null when a real effect is planted.
- Returns are only available as industry portfolios (Ken French), not
  per-stock, so the return side of H2 is industry-level until a stock price
  source is chosen.

Research protocol for M5: fix the train/holdout split before looking, explore
only before it, run `evaluate.confirmatory_test` once on the holdout, and
count every signal/lag tried (correct for that count; the code does not).

## Data you need to obtain

Accounts are never created by this repo. Put credentials in a local `.env`
(gitignored); the code reads them from environment variables.

| Source | Needed for | What to do | Env vars |
|---|---|---|---|
| EOG VIIRS Nightfire | H1 flaring (M3) | Register a free account at https://eogdata.mines.edu/ , accept the terms, download the Nightfire CSV products (global nightly or monthly) | `EOG_USERNAME`, `EOG_PASSWORD` |
| ESG ratings | M5 | Obtain a licensed export (MSCI/Sustainalytics/etc. via a university terminal or library) as CSV with columns `company,provider,date,rating`; no free equivalent is wired up | `ESG_RATINGS_CSV` (path to the file) |
| Copernicus Data Space (optional) | Sentinel-2 | Not required: `sentinel.py` uses the keyless Planetary Computer. Only register at https://dataspace.copernicus.eu/ if you want that route instead | none read yet |
| Global Energy Monitor trackers | M2 facilities | Free, but the download form asks for name and email; save the CSV locally | none |

Keyless sources (no account): Hansen GFC tiles, SEC ticker file, EPA GHGRP
spreadsheets, Ken French returns, Planetary Computer Sentinel-2. URLs and
sizes are in the hand-off notes, not downloaded yet.

## Repository guide

| Path | Contents |
|---|---|
| `imagery.py` | NDVI, cloud masking, change detection, seasonal baseline -- all on plain numpy arrays |
| `geo.py` | Haversine distance, meters-per-degree, facility buffer masks |
| `assets.py` | `Facility` schema and CSV loader with validation |
| `esg_signal.py` | Weighted aggregation of facility signals to company-period |
| `flaring.py`, `forest.py`, `sentinel.py` | Nightfire, Hansen and Sentinel-2 signals (M3/M4) |
| `matching.py`, `returns.py`, `ratings.py` | Ticker matching, free returns, ratings parsing |
| `evaluate.py`, `synth.py` | M5 test and the synthetic panels that validate it |
| `loaders.py` | `MissingCredentials` and the env-var check |
| `tests/` | Synthetic-data tests for all of the above |
| `tests/fixtures/facilities.csv` | Three fictional example facilities |
| `docs/DESIGN.md` | Pipeline diagram, Sentinel-2 band table, SCL class table |
| `requirements-geo.txt` | Optional geo deps (rasterio, pystac-client, planetary-computer), not needed for M1 |

## Quick start

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

## Notes

- The only network call is `sentinel.find_scenes`; everything else takes text
  or a local path. Geo libraries are imported lazily inside functions.
- The buffer/distance math in `geo.py` uses a spherical-earth haversine
  distance rather than a real projection. That's fine at the scale of a
  facility buffer (sub-10km) relative to Sentinel-2's 10m pixels, and would
  need revisiting for anything landscape-scale.
- `tests/fixtures/facilities.csv` is entirely made up -- company names,
  coordinates and all -- and labeled as such in the file. Nothing in this
  repo currently touches a real company's data.
