"""Probe Climate DT access with one day per data stream this study uses.

    pixi run python scripts/check_destine.py

For each projection model (one day of the historical window) and each storyline
climate (the first storm's day), requests 24 hourly fields over La Rioja and reports
the number of hours, cells and the precipitation maximum — or the error. Proves the
credential, the entitlement and the request keys before a long retrieval starts.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import climatedt  # noqa: E402


def probe(label: str, request: dict) -> None:
    t0 = time.time()
    try:
        ds = climatedt.to_study_schema(climatedt.retrieve(request).to_xarray())
        mm = float(ds[climatedt.PARAM_PRECIP].max()) * climatedt.RATE_TO_MM_PER_HOUR
        print(f"OK    {label:32s} {ds.sizes['time']:3d} h x {ds.sizes['cell']:4d} cells, "
              f"max {mm:5.1f} mm/h  ({time.time() - t0:.0f} s)", flush=True)
    except Exception as exc:  # noqa: BLE001 - report every stream, then decide
        print(f"FAIL  {label:32s} {type(exc).__name__}: {str(exc)[:300]}", flush=True)


def main() -> None:
    print(f"credential: {climatedt.credential_source()}; endpoint {climatedt.POLYTOPE_ADDRESS}")
    climatedt.configure_cache(Path("data/.earthkit-cache"))
    for model in climatedt.MODELS:
        r = climatedt.projection_request(model, "hist", 1990, 1)
        probe(f"projection {model} hist", {**r, "date": "19900101/to/19900101"})
        r = climatedt.projection_request(model, "ssp370", 2049, 12)
        probe(f"projection {model} ssp370", {**r, "date": "20491231/to/20491231"})
    day = climatedt.STORMS[0].replace("-", "")
    for climate in climatedt.STORYLINE_CLIMATES:
        probe(f"storyline {climate}", climatedt.storyline_request(climate, day, day))


if __name__ == "__main__":
    main()
