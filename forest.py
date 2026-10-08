"""Hansen Global Forest Change: tile naming, windowed reads, excess forest loss.

Source: Hansen et al. (2013), University of Maryland / Google, CC BY 4.0, no
account. Tiles are 10x10 degrees at ~30 m, named by their upper-left corner.
We use the `lossyear` layer only: 0 = no loss, n = loss in year 2000+n. (Hansen
loss exists only where tree cover was present in 2000, so this is forest loss.)

"Abnormal" loss is the facility buffer's loss fraction minus the loss fraction
of a surrounding ring, which stands in for the regional baseline rate.
"""

import math
from dataclasses import dataclass

import numpy as np

import geo

VERSION = "GFC-2024-v1.12"
BASE_URL = "https://storage.googleapis.com/earthenginepartners-hansen/" + VERSION


def tile_id(lat: float, lon: float) -> str:
    """Upper-left corner id of the 10-degree tile holding the point, e.g. '50N_080W'."""
    top = math.floor(lat / 10.0) * 10 + 10
    left = math.floor(lon / 10.0) * 10
    return "%02d%s_%03d%s" % (abs(top), "N" if top >= 0 else "S",
                              abs(left), "E" if left >= 0 else "W")


def near_tile_edge(lat: float, lon: float, km: float) -> bool:
    """True if the point is within `km` of its 10-degree tile's border, where a window
    of that radius would be clipped (see read_loss_window)."""
    m_lat, m_lon = geo.meters_per_degree(lat)
    d_lat = min(lat % 10.0, 10.0 - lat % 10.0) * m_lat / 1000.0
    d_lon = min(lon % 10.0, 10.0 - lon % 10.0) * m_lon / 1000.0
    return min(d_lat, d_lon) < km


def tile_url(lat: float, lon: float, layer: str = "lossyear") -> str:
    return "%s/Hansen_%s_%s_%s.tif" % (BASE_URL, VERSION, layer, tile_id(lat, lon))


@dataclass
class LossWindow:
    lossyear: np.ndarray  # (H, W) uint8
    lat_grid: np.ndarray
    lon_grid: np.ndarray
    pixel_area_ha: float


def read_loss_window(path: str, lat: float, lon: float, radius_km: float) -> LossWindow:
    """Read the lossyear pixels within `radius_km` of a point from a local tile.

    Needs rasterio (requirements-geo.txt). Windows that cross a tile edge are
    clipped to the tile -- ponytail: mosaic neighbours if facilities near edges matter.
    """
    import rasterio
    from rasterio.windows import from_bounds

    m_lat, m_lon = geo.meters_per_degree(lat)
    dlat = radius_km * 1000.0 / m_lat
    dlon = radius_km * 1000.0 / m_lon
    with rasterio.open(path) as src:
        win = from_bounds(lon - dlon, lat - dlat, lon + dlon, lat + dlat,
                          src.transform).round_offsets().round_lengths()
        data = src.read(1, window=win)
        rows, cols = np.mgrid[0:data.shape[0], 0:data.shape[1]]
        xs, ys = rasterio.transform.xy(src.window_transform(win), rows, cols)
        res_x, res_y = src.res
    lon_grid = np.array(xs).reshape(data.shape)
    lat_grid = np.array(ys).reshape(data.shape)
    area = (res_y * m_lat) * (res_x * m_lon) / 10000.0
    return LossWindow(data, lat_grid, lon_grid, area)


def excess_loss_by_year(win: LossWindow, lat: float, lon: float, radius_km: float,
                        ring_km: float) -> dict[int, float]:
    """{year: excess ha} = (buffer loss fraction - ring loss fraction) * buffer area.

    Negative values are kept: the buffer lost less than its surroundings.
    """
    dist = geo.haversine_km(win.lat_grid, win.lon_grid, lat, lon)
    inner = dist <= radius_km
    ring = (dist > radius_km) & (dist <= ring_km)
    if not inner.any() or not ring.any():
        raise ValueError("window does not cover both the buffer and its ring")
    out = {}
    for code in np.unique(win.lossyear[inner | ring]):
        if code == 0:
            continue
        hit = win.lossyear == code
        f_in = hit[inner].mean()
        f_ring = hit[ring].mean()
        out[2000 + int(code)] = float((f_in - f_ring) * inner.sum() * win.pixel_area_ha)
    return out
