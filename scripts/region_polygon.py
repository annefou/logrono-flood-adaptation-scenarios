"""Write data/climate/la_rioja_polygon.json: the Climate DT retrieval domain.

La Rioja (NUTS 2021 level 2, ES23) from Eurostat GISCO, 1:1 million, as a closed
ring of [latitude, longitude] pairs — the vertex order Polytope's
`feature: {type: polygon}` expects. Run once; the output is committed so the
domain cannot drift with the upstream dataset.

    pixi run python scripts/region_polygon.py
"""

import datetime
import json
from pathlib import Path

import requests
import shapely
from shapely.geometry import shape

URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326_LEVL_2.geojson"
NUTS_ID = "ES23"
EPSILON_DEG = 0.005
OUT = Path(__file__).resolve().parents[1] / "data" / "climate" / "la_rioja_polygon.json"


def main() -> None:
    features = requests.get(URL, timeout=300).json()["features"]
    feature = next(f for f in features if f["properties"]["NUTS_ID"] == NUTS_ID)
    geom = shape(feature["geometry"])
    parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    main_part = max(parts, key=lambda p: p.area)
    ring = shapely.simplify(main_part, EPSILON_DEG).exterior
    coords = [[round(lat, 4), round(lon, 4)] for lon, lat in ring.coords]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    lats, lons = [c[0] for c in coords], [c[1] for c in coords]
    doc = {
        "name": "La Rioja, Spain",
        "description": "Closed boundary ring of La Rioja (NUTS-2 ES23) as [latitude, longitude] "
                       "pairs, in the vertex order Polytope's feature: {type: polygon} expects.",
        "source": {"dataset": "Eurostat GISCO NUTS 2021, level 2, 1:1 million, EPSG:4326",
                   "url": URL, "feature": f"NUTS_ID = {NUTS_ID}",
                   "accessed_on": datetime.date.today().isoformat(),
                   "licence": "Eurostat NUTS — free reuse with attribution "
                              "(© EuroGeographics for the administrative boundaries)"},
        "processing": f"Largest polygon ({len(parts)} part(s)); Douglas-Peucker simplification with "
                      f"epsilon = {EPSILON_DEG} degrees -> {len(coords)} vertices; longitude/latitude "
                      "swapped to latitude/longitude; ring closed.",
        "area_km2_approx": round(main_part.area * 111.2 * 111.2 * 0.743, 0),
        "bbox_lat_lon": [min(lats), min(lons), max(lats), max(lons)],
        "n_vertices": len(coords),
        "ring": coords,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1))
    print(f"wrote {OUT}: {len(coords)} vertices, bbox {doc['bbox_lat_lon']}")


if __name__ == "__main__":
    main()
