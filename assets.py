"""Facility table: the one piece of ground-truth this project needs that is not
satellite data. `load_facilities` reads a CSV of facility name, operating
company, sector, coordinates and type, and validates it before anything
downstream trusts a lat/lon.

Real facility locations come from public trackers (Global Energy Monitor's
oil/gas and mining trackers, EPA FLIGHT for US greenhouse-gas reporters) -- see
README.md for sourcing notes and caveats. `tests/fixtures/facilities.csv`
holds three made-up rows, clearly labeled fictional, so the tests never depend
on a real company's data or on network access.
"""

import csv
from dataclasses import dataclass

REQUIRED_COLUMNS = ("facility", "company", "sector", "lat", "lon", "facility_type")


@dataclass
class Facility:
    """One physical site. `facility_type` is e.g. 'oil_gas', 'mine', 'farm',
    'paper_mill' -- it is what decides which signal (flaring vs. forest loss)
    applies to this row, so it is required, not a free-text note."""

    facility: str
    company: str
    sector: str
    lat: float
    lon: float
    facility_type: str
    source: str = ""
    notes: str = ""


def load_facilities(csv_path):
    """Read and validate a facility CSV, returning a list of `Facility`.

    Raises ValueError if the header is missing a required column, or if any
    row's lat/lon is not numeric or is out of the physically possible range.
    Failing loudly here is the point: a bad coordinate that silently makes it
    into a buffer mask produces a signal for the wrong patch of ground, and
    nothing downstream would notice.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("facilities csv %r has no header row" % (csv_path,))

        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                "facilities csv %r is missing required columns: %s"
                % (csv_path, missing))

        facilities = []
        for i, row in enumerate(reader):
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
            except (TypeError, ValueError):
                raise ValueError(
                    "row %d: lat/lon must be numeric, got lat=%r lon=%r"
                    % (i, row.get("lat"), row.get("lon")))

            if not (-90.0 <= lat <= 90.0):
                raise ValueError("row %d: lat %r out of range [-90, 90]" % (i, lat))
            if not (-180.0 <= lon <= 180.0):
                raise ValueError("row %d: lon %r out of range [-180, 180]" % (i, lon))

            facilities.append(Facility(
                facility=row["facility"],
                company=row["company"],
                sector=row["sector"],
                lat=lat,
                lon=lon,
                facility_type=row["facility_type"],
                source=row.get("source") or "",
                notes=row.get("notes") or "",
            ))
        return facilities
