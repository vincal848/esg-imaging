"""NDVI, cloud masking and change detection on plain numpy arrays.

This module works on arrays the caller already has in memory -- it does not read
rasters, fetch tiles, or know about coordinate reference systems. That split is
deliberate: the primitives here are the part that is easy to get wrong silently
(a flipped band order, an off-by-one threshold, 0/0 producing inf instead of nan)
and the part that is cheap to test with synthetic data. Pulling real Sentinel-2
or VIIRS Nightfire scenes is `requirements-geo.txt` territory and belongs in a
later milestone (see README.md).

Conventions:
  nir, red    reflectance in [0, 1] as floats, or raw digital numbers (uint16)
              paired with `scale`/`offset` to convert them
  scl         the Sentinel-2 L2A Scene Classification Layer, integer codes
              0-11 (see docs/DESIGN.md for the full table)
  pixel_size_m  the ground size of one pixel, in meters, along one side

References: ESA Sentinel-2 L2A Algorithm Theoretical Basis Document (SCL
definition); Hansen et al. 2013 (Science) for the forest-loss-as-threshold-on-
NDVI-drop idea, which Hansen Global Forest Change implements at a coarser
resolution than we do here.
"""

import numpy as np

# Scene Classification Layer codes worth keeping for a vegetation/water
# NDVI signal: 4 = vegetation, 5 = not-vegetated (bare soil), 6 = water.
# Everything else is cloud, cloud shadow, snow or no-data -- see docs/DESIGN.md.
DEFAULT_SCL_KEEP = (4, 5, 6)


def ndvi(nir, red, scale=None, offset=0.0):
    """Normalized Difference Vegetation Index: (NIR - Red) / (NIR + Red).

    If `scale` is given, `nir` and `red` are treated as raw digital numbers
    (e.g. the uint16 reflectance values Sentinel-2 L2A ships, DN/10000) and
    converted to reflectance via `value * scale + offset` before the ratio.

    A pixel where NIR + Red == 0 returns nan, not inf and not a silent zero.
    0/0 is not a real "no vegetation" reading -- it means both bands read zero,
    which for reflectance data means missing or saturated data, not a
    measurement. Letting that propagate as inf would make a single bad pixel
    poison a `nanmean` into +-inf instead of just being excluded.
    """
    nir = np.asarray(nir, dtype=float)
    red = np.asarray(red, dtype=float)
    if scale is not None:
        nir = nir * scale + offset
        red = red * scale + offset

    denom = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(denom == 0, np.nan, (nir - red) / denom)
    return out


def cloud_mask_from_scl(scl, keep=DEFAULT_SCL_KEEP):
    """Boolean mask, True where the SCL class is one of `keep`.

    This is intentionally a whitelist rather than a blacklist of cloud codes --
    new sensors have added SCL-like classes before (e.g. thin cirrus), and a
    whitelist fails safe by excluding anything unrecognized rather than letting
    it through.
    """
    scl = np.asarray(scl)
    return np.isin(scl, keep)


def masked_mean(values, mask):
    """Mean of `values` where `mask` is True, ignoring any nan left in.

    Returns nan (not an error) if nothing survives the combined mask -- an
    all-cloud scene over a facility buffer is a real outcome that callers need
    to be able to detect and skip, not a crash.
    """
    values = np.asarray(values, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    keep = mask & ~np.isnan(values)
    if not np.any(keep):
        return float("nan")
    return float(np.mean(values[keep]))


def ndvi_change(before, after, threshold, pixel_size_m):
    """Flag pixels where NDVI dropped by at least `threshold`, and their area.

    Returns `(loss_mask, area_ha)`. `loss_mask` is a boolean array the same
    shape as the inputs; `area_ha` is the flagged pixel count converted to
    hectares using `pixel_size_m` as the (square) ground sample distance.

    A drop rather than an absolute post-clearing NDVI is used because a
    facility surrounded by bare soil or sparse scrub never had a high NDVI to
    begin with -- the signal is the change, not the level.
    """
    before = np.asarray(before, dtype=float)
    after = np.asarray(after, dtype=float)
    if before.shape != after.shape:
        raise ValueError(
            "before and after must have the same shape, got %r and %r"
            % (before.shape, after.shape))

    drop = before - after
    # nan in either image means no comparison is possible there, not a loss.
    loss_mask = np.where(np.isnan(drop), False, drop >= threshold)

    pixel_area_ha = (float(pixel_size_m) ** 2) / 10000.0
    area_ha = float(np.sum(loss_mask)) * pixel_area_ha
    return loss_mask, area_ha


def seasonal_baseline(stack, doy, target_doy, window=15):
    """Median of the images in `stack` whose day-of-year is within `window`
    days of `target_doy`, wrapping around the new year.

    `stack` is `(T, H, W)`; `doy` is length-`T` day-of-year values (1-365ish).
    A plain calendar-date comparison would treat Dec 20 and Jan 5 as 350 days
    apart instead of 16, which would silently drop half of a facility's winter
    baseline every year -- the circular distance below is the fix.

    Raises ValueError if no image falls inside the window, rather than
    returning an all-nan raster that looks like a valid (if unlucky) baseline.
    """
    stack = np.asarray(stack, dtype=float)
    doy = np.asarray(doy, dtype=float)
    if stack.shape[0] != doy.shape[0]:
        raise ValueError(
            "stack and doy must have the same length along axis 0, got %d and %d"
            % (stack.shape[0], doy.shape[0]))

    raw_delta = np.abs(doy - float(target_doy))
    circular_delta = np.minimum(raw_delta, 365.0 - raw_delta)
    selected = circular_delta <= window
    if not np.any(selected):
        raise ValueError(
            "no images within %g days of day-of-year %g" % (window, target_doy))

    return np.nanmedian(stack[selected], axis=0)


def buffer_loss_ha(ndvi_stack, doy, current, target_doy, buffer_mask,
                   threshold, pixel_size_m, window=15):
    """Hectares of NDVI loss inside a facility buffer on date `current`.

    Composes the primitives above: the baseline is the seasonal median of every
    image in `ndvi_stack` (T, H, W) *except* index `current`, compared against
    `ndvi_stack[current]` with `ndvi_change`, then restricted to `buffer_mask`.
    Cloud-masked pixels must already be nan in the stack, so they are never
    counted as loss.
    """
    ndvi_stack = np.asarray(ndvi_stack, dtype=float)
    others = np.arange(ndvi_stack.shape[0]) != current
    baseline = seasonal_baseline(ndvi_stack[others], np.asarray(doy)[others],
                                 target_doy, window)
    loss_mask, _ = ndvi_change(baseline, ndvi_stack[current], threshold,
                               pixel_size_m)
    n_pixels = int(np.sum(loss_mask & np.asarray(buffer_mask, dtype=bool)))
    return n_pixels * (float(pixel_size_m) ** 2) / 10000.0
