"""Sentinel-2 L2A scene search via the Microsoft Planetary Computer STAC API.

Planetary Computer search and anonymous signed reads need no account (rate
limited), so this is the keyless route; Copernicus Data Space is the alternative
that needs a login. `search_params` is pure; `find_scenes` is the only network call.
"""

import geo

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
COLLECTION = "sentinel-2-l2a"


def search_params(lat: float, lon: float, radius_km: float, start: str, end: str,
                  max_cloud: float = 30.0) -> dict:
    m_lat, m_lon = geo.meters_per_degree(lat)
    dlat, dlon = radius_km * 1000.0 / m_lat, radius_km * 1000.0 / m_lon
    return {
        "collections": [COLLECTION],
        "bbox": [lon - dlon, lat - dlat, lon + dlon, lat + dlat],
        "datetime": "%s/%s" % (start, end),
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
    }


def find_scenes(params: dict) -> list:
    """Signed STAC items (B04, B08, SCL assets). Needs requirements-geo.txt and network."""
    import planetary_computer
    import pystac_client

    client = pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    return list(client.search(**params).items())
