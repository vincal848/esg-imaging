"""VIIRS Nightfire flare detections: parsing, buffer sums, company intensity.

Source: NOAA/EOG VIIRS Nightfire (account-gated, see README "Data you need to
obtain"). The nightly CSVs list one row per detected hot source; `RH` is the
radiant heat in MW, the usual proxy for flared volume.

The CSV column names below follow EOG's Nightfire v3 CSV as documented; they
have NOT been checked against a real download yet, so `parse_nightfire_csv`
takes a `columns` override for the first real file.
"""

import csv
import io
from dataclasses import dataclass

import numpy as np

import geo
from loaders import MissingCredentials, require_env  # noqa: F401 (re-export)

DEFAULT_COLUMNS = {
    "date": "Date_Mscan",
    "lat": "Lat_GMTCO",
    "lon": "Lon_GMTCO",
    "rh": "RH",
}


@dataclass
class Detections:
    lat: np.ndarray
    lon: np.ndarray
    rh: np.ndarray  # radiant heat, MW
    period: np.ndarray  # 'YYYYQn' strings


def quarter_of(iso_date: str) -> str:
    year, month = int(iso_date[0:4]), int(iso_date[5:7])
    return "%dQ%d" % (year, (month - 1) // 3 + 1)


def parse_nightfire_csv(text: str, columns: dict[str, str] | None = None) -> Detections:
    cols = {**DEFAULT_COLUMNS, **(columns or {})}
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in cols.values() if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError("nightfire csv is missing columns: %s" % missing)
    lat, lon, rh, period = [], [], [], []
    for row in reader:
        lat.append(float(row[cols["lat"]]))
        lon.append(float(row[cols["lon"]]))
        rh.append(float(row[cols["rh"]]))
        period.append(quarter_of(row[cols["date"]]))
    return Detections(np.array(lat), np.array(lon), np.array(rh), np.array(period))


def flare_in_buffer(det: Detections, facility_lat: float, facility_lon: float,
                    radius_km: float) -> dict[str, float]:
    """Sum of radiant heat per quarter for detections within `radius_km`."""
    inside = geo.haversine_km(det.lat, det.lon, facility_lat, facility_lon) <= radius_km
    out = {}
    for p, v in zip(det.period[inside], det.rh[inside]):
        out[str(p)] = out.get(str(p), 0.0) + float(v)
    return out


def flaring_intensity(flare: dict[tuple[str, str], float],
                      production: dict[tuple[str, str], float]) -> dict[tuple[str, str], float]:
    """Flare / production per (company, period). Zero or missing production is
    skipped: intensity there is undefined, not zero."""
    return {k: v / production[k] for k, v in flare.items()
            if production.get(k, 0) > 0}


def eog_credentials() -> tuple[str, ...]:
    """(username, password) for the EOG Nightfire download, from env."""
    return require_env("EOG_USERNAME", "EOG_PASSWORD")
