"""Company x year panels for evaluate.py from facility-level series (pure)."""

import numpy as np

from esg_signal import aggregate_facility_signals


def company_matrix(facility_company: dict[str, str], facility_year_value: dict[tuple[str, int], float],
                   years: range) -> tuple[list[str], np.ndarray]:
    """(companies sorted, matrix [company, year]): equal-weight mean over the company's
    facilities, with a missing facility-year counted as 0 (a real zero for both ha lost
    and enforcement events)."""
    recs = [{"company": c, "period": y, "value": facility_year_value.get((f, y), 0.0)}
            for f, c in facility_company.items() for y in years]
    agg = aggregate_facility_signals(recs, weight_key=None)
    companies = sorted(set(facility_company.values()))
    return companies, np.array([[agg[(c, y)]["value"] for y in years] for c in companies])
