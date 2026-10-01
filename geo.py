"""Plain-numpy geodesy: distances and facility buffers on a lat/lon grid.

No projection library, no shapefiles. The buffers this project needs are small
circles (a few hundred meters to a few km) around point facilities, and at that
scale a spherical-earth haversine distance is accurate to well under a pixel --
the Sentinel-2 10 m grid is the limiting factor, not the earth model. If a later
milestone needs real polygons or UTM projections, that is `requirements-geo.txt`
(rasterio/pyproj) territory, not this module.
"""

import numpy as np

EARTH_RADIUS_KM = 6371.0088  # IUGG mean radius


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two (arrays of) lat/lon points.

    Degrees in, km out. Broadcasts the way numpy arithmetic does, so one point
    against a whole grid of points works without a loop.
    """
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lon1 = np.radians(np.asarray(lon1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lon2 = np.radians(np.asarray(lon2, dtype=float))

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    # Clip before sqrt/asin: floating-point round-off can push `a` a hair above
    # 1 for antipodal-ish inputs, which would otherwise make arcsin return nan.
    c = 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))
    return EARTH_RADIUS_KM * c


def meters_per_degree(lat):
    """Local (meters-per-degree-latitude, meters-per-degree-longitude) at `lat`.

    Meters per degree of latitude is nearly constant on a sphere; meters per
    degree of longitude shrinks by cos(lat) as the lines of longitude converge
    toward the poles. Both are needed to turn a radius in km into a pixel count
    on a lat/lon grid, since a "square" buffer in degrees is not square in
    meters away from the equator.
    """
    lat_rad = np.radians(np.asarray(lat, dtype=float))
    meters_per_deg_lat = (np.pi / 180.0) * EARTH_RADIUS_KM * 1000.0
    meters_per_deg_lon = meters_per_deg_lat * np.cos(lat_rad)
    return meters_per_deg_lat, meters_per_deg_lon


def facility_buffer_mask(lat_grid, lon_grid, facility_lat, facility_lon, radius_km):
    """Boolean mask over a lat/lon grid: True within `radius_km` of a facility.

    `lat_grid`/`lon_grid` are same-shaped arrays of pixel-center coordinates
    (e.g. from `np.meshgrid`). This is the pure-numpy stand-in for "buffer a
    point and rasterize it" -- no geometry library, just a distance threshold
    evaluated at every pixel center.
    """
    lat_grid = np.asarray(lat_grid, dtype=float)
    lon_grid = np.asarray(lon_grid, dtype=float)
    if lat_grid.shape != lon_grid.shape:
        raise ValueError(
            "lat_grid and lon_grid must have the same shape, got %r and %r"
            % (lat_grid.shape, lon_grid.shape))

    distance_km = haversine_km(lat_grid, lon_grid, facility_lat, facility_lon)
    return distance_km <= radius_km
