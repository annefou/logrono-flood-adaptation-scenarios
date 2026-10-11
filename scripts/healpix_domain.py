"""Which HEALPix cells belong to the study region, on the sphere and on the WGS84 ellipsoid.

The Climate DT's HEALPix grid is defined on a sphere, and Polytope's polygon feature
selects cells whose (spherical) centre falls inside the polygon. Placed on the WGS84
ellipsoid (authalic latitude, as healpix-geo does), the same cell index sits up to
0.128° further from the equator, so cells near the border can be inside on one
convention and outside on the other. DOMAIN.md: measure it and report it, don't
silently correct it.

All cell ids are NESTED.
"""

from __future__ import annotations

import healpix_geo
import numpy as np
import pandas as pd
from shapely import contains_xy
from shapely.geometry import Polygon


def wrap(lon: np.ndarray) -> np.ndarray:
    lon = np.asarray(lon, float)
    return np.where(lon > 180, lon - 360, lon)


def region(ring_lat_lon: list[list[float]]) -> Polygon:
    return Polygon([(lon, lat) for lat, lon in ring_lat_lon])


def membership(ring_lat_lon: list[list[float]], depth: int, margin_deg: float = 0.5) -> pd.DataFrame:
    """Every cell around the region: centre on the sphere and on WGS84, and inside flags."""
    poly = region(ring_lat_lon)
    lon0, lat0, lon1, lat1 = poly.bounds
    ids, _, _ = healpix_geo.nested.box_coverage(
        ((lon0 + lon1) / 2, (lat0 + lat1) / 2), (lon1 - lon0 + 2 * margin_deg, lat1 - lat0 + 2 * margin_deg),
        0.0, depth, ellipsoid="sphere")
    ids = np.unique(ids)
    lon_s, lat_s = healpix_geo.nested.healpix_to_lonlat(ids, depth, ellipsoid="sphere")
    lon_e, lat_e = healpix_geo.nested.healpix_to_lonlat(ids, depth, ellipsoid="WGS84")
    lon_s, lon_e = wrap(lon_s), wrap(lon_e)  # healpix-geo returns longitudes in [0, 360)
    out = pd.DataFrame({"cell_id": ids, "lon_sphere": lon_s, "lat_sphere": lat_s,
                        "lon_wgs84": lon_e, "lat_wgs84": lat_e})
    out["in_sphere"] = contains_xy(poly, out["lon_sphere"], out["lat_sphere"])
    out["in_wgs84"] = contains_xy(poly, out["lon_wgs84"], out["lat_wgs84"])
    return out[out["in_sphere"] | out["in_wgs84"]].reset_index(drop=True)


def match_delivered(cells: pd.DataFrame, lat: np.ndarray, lon: np.ndarray, depth: int) -> np.ndarray:
    """NESTED ids of delivered cells, from the spherical centres Polytope returns."""
    return np.asarray(healpix_geo.nested.lonlat_to_healpix(np.asarray(lon, float), np.asarray(lat, float),
                                                          depth, ellipsoid="sphere"))
