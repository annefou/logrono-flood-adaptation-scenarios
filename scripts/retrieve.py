"""Retrieve the Climate DT precipitation this study uses, one month per file.

    pixi run python scripts/retrieve.py                 # projections + storylines
    pixi run python scripts/retrieve.py --only storyline --workers 4

Adapted from annefou/extreme-precipitation-climatedt-replication `scripts/retrieve.py`
(v0.1.0, commit 5a28ff7, MIT): one NetCDF per month, existing files skipped (restartable),
a partial file renamed only when complete, every month checked for its full count of
hourly fields (the silent one-hour-per-day under-fetch), retries with back-off, at most
4 concurrent downloads (Polytope's quota is 5), and the download cache swept as it goes.

Files: data/climate/raw/proj_<model>_<window>_<yyyymm>.nc and
       data/climate/raw/story_<climate>_m<member>_<yyyymm>.nc
"""

from __future__ import annotations

import argparse
import calendar
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import climatedt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "climate" / "raw"
CACHE = ROOT / "data" / ".earthkit-cache"
MAX_ATTEMPTS, BACKOFF_SECONDS, CACHE_KEEP_SECONDS = 4, 20, 900
STORYLINE_YEARS = (2017, 2024)


def tasks(only: str | None = None) -> list[tuple]:
    out = []
    if only in (None, "projection"):
        for model in climatedt.MODELS:
            for window, spec in climatedt.WINDOWS.items():
                for year in range(spec["years"][0], spec["years"][1] + 1):
                    out += [("projection", model, window, year, m) for m in range(1, 13)]
    if only in (None, "storyline"):
        # One month of 2 m temperature per climate: tells which experiment is which.
        out += [("check-t2m", climate, "1", 2018, 7) for climate in climatedt.STORYLINE_CLIMATES]
        for climate in climatedt.STORYLINE_CLIMATES:
            for member in climatedt.STORYLINE_MEMBERS:
                for year in range(STORYLINE_YEARS[0], STORYLINE_YEARS[1] + 1):
                    out += [("storyline", climate, member, year, m) for m in range(1, 13)]
    return out


def path_of(task: tuple) -> Path:
    kind, a, b, year, month = task
    prefix = {"projection": f"proj_{a}_{b}", "storyline": f"story_{a}_m{b}", "check-t2m": f"story2t_{a}_m{b}"}[kind]
    return RAW / f"{prefix}_{year}{month:02d}.nc"


def request_of(task: tuple) -> dict:
    kind, a, b, year, month = task
    if kind == "projection":
        return climatedt.projection_request(a, b, year, month)
    last = calendar.monthrange(year, month)[1]
    param = "167" if kind == "check-t2m" else climatedt.PARAM_PRECIP
    return climatedt.storyline_request(a, f"{year}{month:02d}01", f"{year}{month:02d}{last:02d}", member=b, param=param)


def fetch(task: tuple) -> Path:
    out = path_of(task)
    if out.exists():
        return out
    request = request_of(task)
    raw = climatedt.retrieve(request).to_xarray()
    ds = climatedt.to_study_schema(raw, param="2t" if task[0] == "check-t2m" else climatedt.PARAM_PRECIP)
    year, month = task[3], task[4]
    expected = calendar.monthrange(year, month)[1] * 24
    if ds.sizes.get("time", 0) != expected:
        raise RuntimeError(f"{out.name}: expected {expected} hourly fields, got {ds.sizes.get('time', 0)}")
    ds.attrs.update(provenance=climatedt.REAL_PROVENANCE, polytope_address=climatedt.POLYTOPE_ADDRESS,
                    request=json.dumps({k: v for k, v in request.items() if k != "feature"}),
                    polygon=json.dumps(climatedt.polygon_provenance()), **climatedt.attribution_attrs())
    partial = out.with_suffix(".nc.partial")
    ds.to_netcdf(partial)
    partial.rename(out)
    return out


def fetch_with_retries(task: tuple) -> Path:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fetch(task)
        except Exception as exc:  # noqa: BLE001 - retried, then re-raised
            if attempt == MAX_ATTEMPTS:
                raise
            print(f"  ! {path_of(task).name} attempt {attempt}: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
            time.sleep(BACKOFF_SECONDS * attempt)


def sweep_cache() -> None:
    cutoff = time.time() - CACHE_KEEP_SECONDS
    for entry in CACHE.glob("polytope-*.cache"):
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            continue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["projection", "storyline"])
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    climatedt.configure_cache(CACHE)
    todo = [t for t in tasks(args.only) if not path_of(t).exists()]
    print(f"credential {climatedt.credential_source()}; {len(todo)} month(s) to fetch", flush=True)
    failed, started = [], time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_with_retries, t): t for t in todo}
        for i, f in enumerate(as_completed(futures), start=1):
            try:
                f.result()
            except Exception as exc:  # noqa: BLE001 - recorded, run continues
                failed.append((path_of(futures[f]).name, str(exc)[:200]))
            sweep_cache()
            if i % 20 == 0 or i == len(todo):
                eta = (time.time() - started) / i * (len(todo) - i) / 60
                print(f"[{i}/{len(todo)}] {len(failed)} failed, eta {eta:.0f} min", flush=True)
    for name, msg in failed:
        print(f"FAILED {name}: {msg}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
