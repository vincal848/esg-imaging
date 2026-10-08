"""Aggregate per-facility signals up to company-period observations.

A company with five oil & gas facilities does not have five ESG signals, it
has one -- some combination of what happened at each site, weighted by how
much that site matters (production capacity, acreage, historical emissions).
This module is the stub for that combination: group facility-level readings by
(company, period) and take a weighted mean. The weighting scheme itself is a
placeholder (equal weights work as a default) until M3/M4 attach something
real, like reported production or facility acreage.
"""

import numpy as np


def aggregate_facility_signals(records, group_keys=("company", "period"),
                                value_key="value", weight_key="weight"):
    """Weighted mean of a facility-level signal, grouped by `group_keys`.

    `records` is an iterable of dicts, each with the group keys, `value_key`
    and `weight_key`. Returns a dict keyed by the group-key tuple, mapping to
    `{"value": weighted mean, "weight_sum": sum of raw weights,
    "n_facilities": count of records in the group}`.

    `weight_key=None` means equal weights (every record weighs 1).

    Raises ValueError if a group's weights sum to zero or less -- a weighted
    mean is undefined there, and returning nan silently would make a company
    with no usable facility data look identical to one with a genuinely flat
    (zero) signal.
    """
    groups = {}
    for record in records:
        key = tuple(record[k] for k in group_keys)
        groups.setdefault(key, []).append(record)

    out = {}
    for key, group_records in groups.items():
        weights = np.array([1.0 if weight_key is None else r[weight_key]
                            for r in group_records], dtype=float)
        values = np.array([r[value_key] for r in group_records], dtype=float)

        weight_sum = float(np.sum(weights))
        if weight_sum <= 0:
            raise ValueError(
                "group %r has non-positive total weight (%g); cannot take a "
                "weighted mean" % (key, weight_sum))

        normalized_weights = weights / weight_sum
        out[key] = {
            "value": float(np.sum(normalized_weights * values)),
            "weight_sum": weight_sum,
            "n_facilities": len(group_records),
        }
    return out
