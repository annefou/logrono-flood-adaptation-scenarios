"""Destination Earth Climate DT requests for La Rioja: projections and storylines.

Adapted from `scripts/climatedt.py` of annefou/extreme-precipitation-climatedt-replication
(v0.1.0, commit 5a28ff7, MIT), where every key was checked against the official
examples and against live responses. Kept from there, unchanged:

  * generation "2" (1990-2049, ~5 km, hourly, HEALPix); historical =
    `baseline`/`hist`, scenario = `projections`/`SSP3-7.0`; endpoint on MareNostrum5;
  * precipitation in the hourly `clte` stream is `avg_tprate` (an hourly-mean rate,
    kg m-2 s-1), not `tp` (refused with HTTP 400);
  * `time` must list every hour: with a `/to/../by/..` range, feature extraction
    returns the first hour only, without an error;
  * MARS cannot crop HEALPix with a lat/lon box, so the domain is a server-side
    `polygon` feature.

New here, from destination-earth-digital-twins/polytope-examples (commit 3a13f05,
2026-10-07; `climate-dt/feature-extraction/climate-dt-earthkit-fe-story-nudging.ipynb`
and `climate-dt/explorer/destine_portfolio.py`):

  * storylines: `activity: story-nudging`, model `ifs-fesom` only, experiments
    `hist`, `cont`, `Tplus2.0K`, each 2017-01-01 to 2024-12-31, hourly `clte`
    surface fields, `resolution: high` = HEALPix nside 512;
  * three models for the projections: IFS-NEMO, IFS-FESOM, ICON.

Nothing here touches the network unless `retrieve()` is called.
"""

from __future__ import annotations

import calendar
import json
import os
from pathlib import Path
from typing import Any

POLYTOPE_COLLECTION = "destination-earth"
POLYTOPE_ADDRESS = "polytope.mn5.apps.dte.destination-earth.eu"
GENERATION = "2"
EXPVER = "0001"
REALIZATION = "1"
RESOLUTION = "high"
PARAM_PRECIP = "avg_tprate"
RATE_TO_MM_PER_HOUR = 3600.0
ALL_HOURS = "/".join(f"{hour:02d}00" for hour in range(24))

# Generation 2 has three models, but on 2026-10-10 only IFS-NEMO's hourly precipitation
# was on the FDB behind Polytope: IFS-FESOM and ICON answered "No data ... is available
# on the FDB" (HTTP 400) for every date tried in both windows, at `high` and `standard`
# resolution (scripts/check_destine.py; e.g. request IDs 01f3z8k983aqyp40089c6v6btg,
# 01f3z8k983aqyp8008a1btemc7). The projections are therefore single-model.
MODELS = ("IFS-NEMO",)
UNAVAILABLE_MODELS = ("IFS-FESOM", "ICON")
STORYLINE_MEMBERS = ("1", "2", "3", "4", "5")
# Two 20-year windows, as in the Germany study: the last 20 years of the
# simulation against 1990-2009, the earliest 20 the archive holds.
WINDOWS: dict[str, dict[str, Any]] = {
    "hist": {"activity": "baseline", "experiment": "hist", "years": (1990, 2009),
             "label": "historical 1990-2009"},
    "ssp370": {"activity": "projections", "experiment": "SSP3-7.0", "years": (2030, 2049),
               "label": "SSP3-7.0 2030-2049"},
}
DURATIONS_H = (1, 2, 3, 6)
RETURN_PERIODS_Y = (2.0, 5.0, 10.0, 20.0)

STORYLINE_MODEL = "ifs-fesom"
STORYLINE_CLIMATES = ("hist", "cont", "Tplus2.0K")
# The storms that flooded Logroño (replication's data/impacts/logrono_events.csv).
STORMS = ("2018-09-17", "2021-09-01", "2023-06-21", "2024-10-16")

POLYGON_PATH = Path(__file__).resolve().parents[1] / "data" / "climate" / "la_rioja_polygon.json"


def region_polygon() -> list[list[float]]:
    """Closed [latitude, longitude] ring of La Rioja, from the committed file."""
    return json.loads(POLYGON_PATH.read_text())["ring"]


def polygon_provenance() -> dict:
    return {k: v for k, v in json.loads(POLYGON_PATH.read_text()).items() if k != "ring"}


def _base(param: str) -> dict:
    return {"class": "d1", "dataset": "climate-dt", "generation": GENERATION, "expver": EXPVER,
            "realization": REALIZATION, "resolution": RESOLUTION, "stream": "clte", "type": "fc",
            "levtype": "sfc", "param": param, "time": ALL_HOURS,
            "feature": {"type": "polygon", "shape": region_polygon()}}


def projection_request(model: str, window: str, year: int, month: int, param: str = PARAM_PRECIP) -> dict:
    """Every hour of one calendar month over La Rioja, one model."""
    if model not in MODELS:
        raise KeyError(f"unknown model {model!r}; expected one of {MODELS}")
    spec = WINDOWS[window]
    first, last = spec["years"]
    if not first <= year <= last:
        raise ValueError(f"{year} is outside window {window} ({first}-{last})")
    last_day = calendar.monthrange(year, month)[1]
    return {**_base(param), "activity": spec["activity"], "experiment": spec["experiment"],
            "model": model, "date": f"{year}{month:02d}01/to/{year}{month:02d}{last_day:02d}"}


def storyline_request(climate: str, first_day: str, last_day: str, member: str = "1",
                      param: str = PARAM_PRECIP) -> dict:
    """Every hour from ``first_day`` to ``last_day`` (YYYYMMDD) over La Rioja, one storyline climate."""
    if climate not in STORYLINE_CLIMATES:
        raise KeyError(f"unknown storyline climate {climate!r}; expected one of {STORYLINE_CLIMATES}")
    return {**_base(param), "activity": "story-nudging", "experiment": climate,
            "model": STORYLINE_MODEL, "realization": member, "date": f"{first_day}/to/{last_day}"}


REAL_PROVENANCE = "destine-climate-dt"
# DestinE Terms and Conditions v2.0, Art. 3.4: attribution in this wording, co-located
# with the data; derived data must be identified as changed.
DESTINE_ATTRIBUTION = ("This data is created based on data of the European Union, using the "
                       "Destination Earth Platform, but has been modified by Anne Fouilloux.")
DESTINE_LICENCE_NOTE = ("Derived product. Aggregation and transformation of Destination Earth "
                        "Climate DT output (regional subset, hourly accumulation, maxima, "
                        "extreme-value fitting). NOT original DestinE Data. DestinE Terms and "
                        "Conditions v2.0, Art. 2.3 / 3.3 / 3.4.")


def attribution_attrs() -> dict:
    return {"attribution": DESTINE_ATTRIBUTION, "licence_note": DESTINE_LICENCE_NOTE,
            "source_terms": "https://platform.destine.eu/terms-and-conditions/"}


def credential_source() -> str | None:
    """Where polytope-client will find a credential (its own order of precedence)."""
    if os.environ.get("POLYTOPE_USER_KEY"):
        return "env:POLYTOPE_USER_KEY"
    key_path = Path(os.environ.get("POLYTOPE_KEY_PATH") or Path.home() / ".polytopeapirc")
    if key_path.exists():
        return f"file:{key_path}"
    ecmwf = Path.home() / ".ecmwfapirc"
    return f"file:{ecmwf}" if ecmwf.exists() else None


def to_study_schema(ds, param: str = PARAM_PRECIP):
    """CoverageJSON-derived dataset -> (time, cell) with lat/lon per cell.

    Polytope returns `datetimes` x `number` x `steps` x `points`, datetimes as strings.
    `number` and `steps` must be length 1 (one realization, one surface field): checked,
    so a multi-member response fails loudly instead of being collapsed.
    """
    import numpy as np
    import pandas as pd

    for name in ("number", "steps"):
        if ds.sizes.get(name, 1) != 1:
            raise ValueError(f"expected {name} of length 1, got {ds.sizes[name]}")
    out = ds[[param]]
    for name in ("number", "steps"):
        if name in out.dims:
            out = out.isel({name: 0}, drop=True)
    for name in ("levelist", "number", "steps"):
        if name in out.coords:
            out = out.drop_vars(name)
    times = pd.to_datetime([str(t) for t in np.ravel(ds["datetimes"].values)], utc=True)
    out = out.rename({"datetimes": "time", "points": "cell"})
    out = out.assign_coords(time=times.tz_localize(None), cell=np.arange(out.sizes["cell"], dtype="int32"))
    return out.transpose("time", "cell")


def configure_cache(cache_dir: Path, max_size: str = "4G") -> None:
    """Bound earthkit's download cache: its default policy never evicts during a run."""
    from earthkit.data import config

    cache_dir.mkdir(parents=True, exist_ok=True)
    config.set({"cache-policy": "user", "user-cache-directory": str(cache_dir),
                "maximum-cache-size": max_size})


def retrieve(request: dict):
    """Run one Polytope request; returns the earthkit source (call `.to_xarray()`)."""
    import earthkit.data

    return earthkit.data.from_source("polytope", POLYTOPE_COLLECTION, request,
                                     address=POLYTOPE_ADDRESS, stream=False)
