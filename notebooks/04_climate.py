# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 04 — How much heavier does rainfall get? Three sources
#
# REACHOUT's future flood maps scale observed 15-minute design storms by changes from
# EURO-CORDEX. This notebook checks those changes and adds two independent views from the
# Destination Earth Climate DT:
#
# 1. **EURO-CORDEX** (the source of REACHOUT's `CC_Q50` / `CC_Q90`): can the published
#    factors be reproduced from REACHOUT's own IDF file (Zenodo 10.5281/zenodo.14035736)?
# 2. **Climate DT generation-2 projections** (IFS-NEMO, SSP3-7.0, HEALPix level 10): change
#    of 1–6 h return levels over La Rioja, 2030–2049 against 1990–2009.
# 3. **Climate DT storylines** (IFS-FESOM nudged to ERA5 above the boundary layer, 2017–2024,
#    five members, three climates): how much heavier the heaviest hours are at +2 °C, for
#    the whole period and for the four storms that flooded Logroño.
#
# The data are retrieved by `scripts/retrieve.py` (hours of requests; credentials needed,
# see `scripts/climatedt.py`). This notebook reads the monthly files and only measures.
#
# **Durations.** REACHOUT's storms last 15 minutes; EURO-CORDEX's shortest duration is 3 h
# and the Climate DT's 1 h. Only relative changes are compared, never absolute amounts, and
# applying a change from longer durations to 15 minutes is an assumption, stated, not tested.

# %%
import calendar
import hashlib
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

sys.path.insert(0, str(Path("../scripts").resolve()))
import climatedt  # noqa: E402
import extremes  # noqa: E402

RAW = Path("../data/raw")
RAW.mkdir(parents=True, exist_ok=True)
CLIMATE = Path("../data/climate/raw")
# The monthly Climate DT files need DestinE credentials (scripts/retrieve.py). Without them
# (e.g. in CI), sections 2-3 show the committed results instead of recomputing them.
HAVE_CLIMATEDT = CLIMATE.exists() and any(CLIMATE.glob("proj_*.nc"))
COMMITTED_NOTE = ("Climate DT data not available on this machine (no DestinE credentials): showing the "
                  "committed results in results/, computed by this notebook where the data were retrieved.")
RESULTS = Path("../results")
RNG_SEED, N_BOOT = 20261010, 1000
RPS = np.array([2.0, 5.0, 10.0, 20.0])
REACHOUT_RPS = [2, 5, 10, 25, 50, 100, 200]
inventory = pd.read_csv(RESULTS / "reachout_inventory.csv")
published = inventory.drop_duplicates(["climate", "rp"]).pivot(index="rp", columns="climate", values="published_mm")
reachout_factor = pd.DataFrame({"CC_Q50": published["CC_Q50"] / published["present"],
                                "CC_Q90": published["CC_Q90"] / published["present"]})
print(reachout_factor.round(3).T.to_string())

# %% [markdown]
# ## 1. EURO-CORDEX behind REACHOUT's climate scenarios
#
# REACHOUT: "Observations are then scaled according to the changes simulated between future
# and historical scenarios, using the median and 90th percentile values estimated from the
# EURO-CORDEX ensemble." The IDF file gives GEV return levels per simulation for 3, 6, 12 and
# 24 h, 1976–2005 and 2041–2070, RCP 2.6 / 4.5 / 8.5. Neither the scenario nor the duration
# behind the published factors is stated, so every combination is tried: ratio future /
# historical per simulation, then the median and 90th percentile across simulations.

# %%
# Zenodo files are immutable: the MD5 below is the one Zenodo publishes for this file, so a
# local copy that matches it is the same file and need not be fetched again.
IDF = {"record": "14035736", "file": "IDF_Logrono.zip", "md5": "3f7b59afdbe00cb71e76234dffaaa014"}
HEADERS = {"User-Agent": "logrono-flood-adaptation-scenarios (+https://github.com/annefou/logrono-flood-adaptation-scenarios)"}


def get(url: str, attempts: int = 6) -> requests.Response:
    """GET with retries and growing back-off: Zenodo throttles and answers 504 / empty bodies."""
    for i in range(attempts):
        try:
            r = requests.get(url, timeout=300, headers=HEADERS)
            r.raise_for_status()
            if not r.content:
                raise ValueError("empty response")
            return r
        except (requests.RequestException, ValueError) as e:
            if i == attempts - 1:
                raise
            print(f"retry {i + 1} after: {str(e)[:120]}")
            time.sleep(30 * (i + 1))


idf_path = RAW / IDF["file"]
if idf_path.exists() and hashlib.md5(idf_path.read_bytes()).hexdigest() == IDF["md5"]:
    blob = idf_path.read_bytes()
else:
    blob = get(f"https://zenodo.org/records/{IDF['record']}/files/{IDF['file']}?download=1").content
    assert hashlib.md5(blob).hexdigest() == IDF["md5"], "IDF file does not match Zenodo's MD5"
    idf_path.write_bytes(blob)
entry = {"checksum": f"md5:{IDF['md5']}"}

ratios, skipped = [], []
with zipfile.ZipFile(io.BytesIO(blob)) as z:
    for name in z.namelist():
        text = z.read(name).decode()
        cols = text.splitlines()[0].split(",")[1:]  # raw header: pandas would rename duplicates silently
        if len(set(cols)) != len(cols) or not any(c.endswith(" hist") for c in cols):
            skipped.append({"file": name, "header": cols})
            continue
        table = pd.read_csv(io.StringIO(text), index_col=0)
        for col in cols:
            duration, scenario = col.split()
            if scenario == "hist":
                continue
            for rp_label, value in table[col].items():
                ratios.append({"simulation": name, "scenario": scenario, "duration": duration,
                               "rp": int(rp_label.split("-")[0]), "ratio": value / table.loc[rp_label, f"{duration} hist"]})
ratios = pd.DataFrame(ratios)
print(f"{ratios['simulation'].nunique()} simulation files used; {len(skipped)} skipped (malformed header):")
for s in skipped:
    print("  ", s["file"], s["header"][:6], "...")

pooled = ratios.assign(scenario="all")
cordex = (pd.concat([ratios, pooled]).groupby(["scenario", "duration", "rp"])["ratio"]
          .agg(n="size", Q50="median", Q90=lambda s: s.quantile(0.9)).reset_index())
cordex.to_csv(RESULTS / "cordex_factors.csv", index=False)

common = [rp for rp in REACHOUT_RPS if rp in set(cordex["rp"])]
match = []
for (sc, du), g in cordex.groupby(["scenario", "duration"]):
    g = g.set_index("rp").loc[common]
    err50 = (g["Q50"] - reachout_factor.loc[common, "CC_Q50"]).abs()
    err90 = (g["Q90"] - reachout_factor.loc[common, "CC_Q90"]).abs()
    match.append({"scenario": sc, "duration": du, "n_simulations": int(g["n"].iloc[0]),
                  "max_abs_error_Q50": err50.max(), "max_abs_error_Q90": err90.max(),
                  "max_abs_error": max(err50.max(), err90.max())})
match = pd.DataFrame(match).sort_values("max_abs_error")
match.to_csv(RESULTS / "cordex_match.csv", index=False)
print(match.head(6).round(3).to_string(index=False))

# %% [markdown]
# ## HEALPix cells on the sphere and on WGS84
#
# The Climate DT's HEALPix grid is defined on a sphere, and Polytope's polygon feature
# keeps the cells whose spherical centre lies inside La Rioja. On the WGS84 ellipsoid
# (authalic latitude, healpix-geo) the same cell index lies up to 0.128° (~14 km) further
# north, so border cells can be inside on one convention and outside on the other. All
# cells around the region are listed with healpix-geo (NESTED), at the projections' level
# 10 and the storylines' level 9; the sphere set must equal the delivered cells. The
# changes in §2–3 are then also computed over the cells inside on **both** conventions —
# reported, not used to replace the delivered domain. Cells inside only on WGS84 were not
# retrieved.

# %%
import healpix_domain as hd  # noqa: E402

MEMBERSHIP = {depth: hd.membership(climatedt.region_polygon(), depth) for depth in (10, 9)}
member_rows = []
for depth, m in MEMBERSHIP.items():
    member_rows.append({"healpix_level": depth, "inside_sphere": int(m["in_sphere"].sum()),
                        "inside_both": int((m["in_sphere"] & m["in_wgs84"]).sum()),
                        "leaving_on_wgs84": int((m["in_sphere"] & ~m["in_wgs84"]).sum()),
                        "entering_on_wgs84": int((~m["in_sphere"] & m["in_wgs84"]).sum()),
                        "max_latitude_shift_deg": float((m["lat_wgs84"] - m["lat_sphere"]).abs().max())})
membership_summary = pd.DataFrame(member_rows)
membership_summary.to_csv(RESULTS / "healpix_membership.csv", index=False)
print(membership_summary.round(3).to_string(index=False))


def inside_both(lat: np.ndarray, lon: np.ndarray, depth: int) -> np.ndarray:
    """For delivered cells (spherical centres): inside La Rioja on both conventions."""
    m = MEMBERSHIP[depth].set_index("cell_id")
    ids = hd.match_delivered(m, lat, hd.wrap(lon), depth)
    assert set(ids) == set(m.index[m["in_sphere"]]), "delivered cells differ from the sphere membership"
    return (m.loc[ids, "in_sphere"] & m.loc[ids, "in_wgs84"]).to_numpy()


def wgs84_centres(lat: np.ndarray, lon: np.ndarray, depth: int) -> tuple[np.ndarray, np.ndarray]:
    m = MEMBERSHIP[depth].set_index("cell_id")
    ids = hd.match_delivered(m, lat, hd.wrap(lon), depth)
    return m.loc[ids, "lat_wgs84"].to_numpy(), m.loc[ids, "lon_wgs84"].to_numpy()


# %% [markdown]
# ## 2. Climate DT projections: 1–6 h return levels over La Rioja
#
# Hourly precipitation (`avg_tprate` × 3600 = mm per hour) on HEALPix level 10, clipped
# server-side to La Rioja. Annual maxima of 1, 2, 3 and 6 h accumulations per cell and
# year; one GEV growth curve per window by regional index-flood pooling (L-moments; the
# vendored `extremes` module of the Germany study); return level = growth × index flood.
# Change = return level 2030–2049 / 1990–2009 − 1, as the median over cells, for the region
# and for the cells within 25 km of Logroño. Uncertainty: 1,000 resamples of the years
# (both windows, all cells together — neighbouring cells share their storms).

# %%
LOGRONO = (42.465, -2.445)


def monthly_files(pattern: str, years: range) -> dict[int, list[Path]]:
    out = {}
    for y in years:
        files = [CLIMATE / pattern.format(ym=f"{y}{m:02d}") for m in range(1, 13)]
        missing = [f.name for f in files if not f.exists()]
        assert not missing, f"missing months: {missing[:3]} — run scripts/retrieve.py"
        out[y] = files
    return out


def annual_maxima(by_year: dict[int, list[Path]]) -> tuple[np.ndarray, dict[int, np.ndarray], xr.Dataset]:
    def chunks():
        for y, files in by_year.items():
            ds = xr.open_mfdataset(files, combine="nested", concat_dim="time")
            yield y, ds[climatedt.PARAM_PRECIP].values * climatedt.RATE_TO_MM_PER_HOUR
    first = xr.open_dataset(next(iter(by_year.values()))[0])
    years, am = extremes.annual_maxima_multi(chunks(), climatedt.DURATIONS_H)
    return years, am, first


def distance_km(lat: np.ndarray, lon: np.ndarray, point: tuple[float, float]) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    pa, po = np.radians(point[0]), np.radians(point[1])
    return 6371.0 * np.arccos(np.clip(np.sin(la) * np.sin(pa) + np.cos(la) * np.cos(pa) * np.cos(lo - po), -1, 1))


def change(am_hist: np.ndarray, am_fut: np.ndarray, cells: np.ndarray) -> np.ndarray:
    """Median over cells of the return-level ratio future / historical, per return period."""
    rl_h = extremes.regional_return_levels(am_hist[:, cells], RPS)
    rl_f = extremes.regional_return_levels(am_fut[:, cells], RPS)
    return np.nanmedian(rl_f / rl_h, axis=1) - 1


def change_with_ci(am_hist: np.ndarray, am_fut: np.ndarray, cells: np.ndarray) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    best = change(am_hist, am_fut, cells)
    boot = np.array([change(am_hist[rng.integers(0, len(am_hist), len(am_hist))],
                            am_fut[rng.integers(0, len(am_fut), len(am_fut))], cells) for _ in range(N_BOOT)])
    return pd.DataFrame({"rp": RPS, "change": best, "ci_lo": np.nanpercentile(boot, 5, axis=0),
                         "ci_hi": np.nanpercentile(boot, 95, axis=0)})


if HAVE_CLIMATEDT:
    rows = []
    for model in climatedt.MODELS:
        am = {}
        for window, spec in climatedt.WINDOWS.items():
            y0, y1 = spec["years"]
            _, am[window], sample = annual_maxima(monthly_files(f"proj_{model}_{window}_{{ym}}.nc", range(y0, y1 + 1)))
        lat, lon = sample["latitude"].values, hd.wrap(sample["longitude"].values)
        lat_e, lon_e = wgs84_centres(lat, lon, 10)
        domains = {"La Rioja": np.ones(lat.size, bool),
                   "La Rioja, inside on sphere and WGS84": inside_both(lat, lon, 10),
                   "within 25 km of Logroño": distance_km(lat, lon, LOGRONO) <= 25,
                   "within 25 km of Logroño (WGS84 centres)": distance_km(lat_e, lon_e, LOGRONO) <= 25}
        for dname, cells in domains.items():
            for d in climatedt.DURATIONS_H:
                rows.append(change_with_ci(am["hist"][d], am["ssp370"][d], cells).assign(
                    model=model, domain=dname, n_cells=int(cells.sum()), duration_h=d))
    projection = pd.concat(rows, ignore_index=True)
    projection.to_csv(RESULTS / "climatedt_projection_change.csv", index=False)
    print(projection.pivot_table(index=["domain", "duration_h"], columns="rp", values="change").round(3).to_string())
else:
    projection = pd.read_csv(RESULTS / "climatedt_projection_change.csv")
    print(COMMITTED_NOTE)
    print(projection.pivot_table(index=["domain", "duration_h"], columns="rp", values="change").round(3).to_string())

# %% [markdown]
# ## 3. Storylines: the same weather in three climates
#
# The storylines nudge the large-scale circulation to ERA5 above the boundary layer, so
# each experiment sees the weather that happened, 2017–2024, in a different climate. Which
# experiment is which is checked here, not taken from the names: the mean 2 m temperature
# over La Rioja in July 2018 (member 1).

# %%
if HAVE_CLIMATEDT:
    JULY_2018_T2M_C = {c: float(xr.open_dataset(CLIMATE / f"story2t_{c}_m1_201807.nc")["2t"].mean()) - 273.15
                       for c in climatedt.STORYLINE_CLIMATES}
    (RESULTS / "storyline_t2m_check.json").write_text(json.dumps(JULY_2018_T2M_C, indent=1))
else:
    JULY_2018_T2M_C = json.loads((RESULTS / "storyline_t2m_check.json").read_text())
    print(COMMITTED_NOTE)
print({c: round(t, 2) for c, t in JULY_2018_T2M_C.items()})
order = sorted(JULY_2018_T2M_C, key=JULY_2018_T2M_C.get)
assert order == ["cont", "hist", "Tplus2.0K"]
CLIMATE_NAME = {"cont": "1950s-like", "hist": "present", "Tplus2.0K": "+2 °C"}
print("coolest → warmest:", [f"{c} ({CLIMATE_NAME[c]})" for c in order])

# %% [markdown]
# **Heaviest hours, 2017–2024.** Annual maxima per cell, climate and member (8 years × 5
# members = 40 per cell), pooled as in §2; change of the RP2–RP10 return levels against the
# present (`hist`). Resampling: member-years.

# %%
if HAVE_CLIMATEDT:
    STORY_YEARS = range(2017, 2025)
    story_am = {}
    for climate in climatedt.STORYLINE_CLIMATES:
        per_member = []
        for member in climatedt.STORYLINE_MEMBERS:
            _, am, sample = annual_maxima(monthly_files(f"story_{climate}_m{member}_{{ym}}.nc", STORY_YEARS))
            per_member.append(am)
        story_am[climate] = {d: np.concatenate([m[d] for m in per_member]) for d in climatedt.DURATIONS_H}
    story_domains = {"La Rioja": np.ones(sample.sizes["cell"], bool),
                     "La Rioja, inside on sphere and WGS84": inside_both(sample["latitude"].values,
                                                                       sample["longitude"].values, 9)}
    story_rows = []
    for dname, cells in story_domains.items():
        for climate in ("cont", "Tplus2.0K"):
            for d in climatedt.DURATIONS_H:
                story_rows.append(change_with_ci(story_am["hist"][d], story_am[climate][d], cells).assign(
                    climate=climate, against="hist", duration_h=d, domain=dname, n_cells=int(cells.sum())))
    storyline_change = pd.concat(story_rows, ignore_index=True)
    storyline_change["rp"] = storyline_change["rp"].astype(float)
    storyline_change = storyline_change[storyline_change["rp"] <= 10]
    storyline_change.to_csv(RESULTS / "storyline_change.csv", index=False)
    print(storyline_change.pivot_table(index=["domain", "climate", "duration_h"], columns="rp", values="change").round(3).to_string())
else:
    storyline_change = pd.read_csv(RESULTS / "storyline_change.csv")
    print(COMMITTED_NOTE)
    print(storyline_change.pivot_table(index=["domain", "climate", "duration_h"], columns="rp", values="change").round(3).to_string())

# %% [markdown]
# **The four storms.** For each storm, the regional maximum (over La Rioja's cells) of the
# 1, 2, 3 and 6 h accumulations from the day before to the day after, per climate and
# member; the ratio to the present (`hist`) of the same member, so that the same weather is
# compared. How unusual the storm is in the present storyline: the rank of its regional
# 1-hour maximum among all days of 2017–2024 (member by member).

# %%
if HAVE_CLIMATEDT:
    def hourly_region(climate: str, member: str, first: pd.Timestamp, last: pd.Timestamp) -> xr.DataArray:
        months = pd.period_range(first, last, freq="M")
        files = [CLIMATE / f"story_{climate}_m{member}_{p.year}{p.month:02d}.nc" for p in months]
        ds = xr.open_mfdataset(files, combine="nested", concat_dim="time")
        return ds[climatedt.PARAM_PRECIP].sel(time=slice(first, last)) * climatedt.RATE_TO_MM_PER_HOUR


    storm_rows = []
    for storm in climatedt.STORMS:
        day = pd.Timestamp(storm)
        for climate in climatedt.STORYLINE_CLIMATES:
            for member in climatedt.STORYLINE_MEMBERS:
                pr = hourly_region(climate, member, day - pd.Timedelta("2D"), day + pd.Timedelta("1D 23h")).values
                for d in climatedt.DURATIONS_H:
                    acc = extremes.rolling_sum(pr, d)[24:]          # windows ending on or after the day before
                    storm_rows.append({"storm": storm, "climate": climate, "member": member, "duration_h": d,
                                       "regional_max_mm": float(np.nanmax(acc))})
    storms = pd.DataFrame(storm_rows)
    present = storms[storms["climate"] == "hist"].set_index(["storm", "member", "duration_h"])["regional_max_mm"]
    storms["ratio_to_present"] = storms["regional_max_mm"] / storms.set_index(["storm", "member", "duration_h"]).index.map(present)


    DAILY_MAX = {m: hourly_region("hist", m, pd.Timestamp("2017-01-01"), pd.Timestamp("2024-12-31 23:00"))
                 .max("cell").resample(time="1D").max().to_series() for m in climatedt.STORYLINE_MEMBERS}


    def storm_rank(storm: str, member: str) -> float:
        daily_max = DAILY_MAX[member]
        window = daily_max[pd.Timestamp(storm) - pd.Timedelta("1D"): pd.Timestamp(storm) + pd.Timedelta("1D")].max()
        return float((daily_max < window).mean())


    ranks = pd.DataFrame([{"storm": s, "member": m, "percentile_of_day_in_present": storm_rank(s, m)}
                          for s in climatedt.STORMS for m in climatedt.STORYLINE_MEMBERS])
    storms.to_csv(RESULTS / "storyline_storms.csv", index=False)
    ranks.to_csv(RESULTS / "storyline_storm_ranks.csv", index=False)
    print(storms.groupby(["storm", "climate", "duration_h"])["ratio_to_present"].median().unstack("climate").round(3).to_string())
    print(ranks.groupby("storm")["percentile_of_day_in_present"].describe()[["min", "50%", "max"]].round(3).to_string())
else:
    storms = pd.read_csv(RESULTS / "storyline_storms.csv")
    ranks = pd.read_csv(RESULTS / "storyline_storm_ranks.csv")
    print(COMMITTED_NOTE)
    print(storms.groupby(["storm", "climate", "duration_h"])["ratio_to_present"].median().unstack("climate").round(3).to_string())
    print(ranks.groupby("storm")["percentile_of_day_in_present"].describe()[["min", "50%", "max"]].round(3).to_string())

# %% [markdown]
# ## Attribution
#
# Sections 2–3: derived from Destination Earth Climate DT data. This data is created based
# on data of the European Union, using the Destination Earth Platform, but has been modified
# by Anne Fouilloux (DestinE Terms and Conditions v2.0, Art. 3.4). The hourly DestinE data
# are not redistributed.

# %%
(RESULTS / "climate_provenance.json").write_text(json.dumps({
    "cordex": {"record": IDF["record"], "md5": entry["checksum"], "skipped_files": skipped},
    "climatedt": {"endpoint": climatedt.POLYTOPE_ADDRESS, "models": climatedt.MODELS,
                  "unavailable_models": climatedt.UNAVAILABLE_MODELS, "windows": climatedt.WINDOWS,
                  "storyline_members": climatedt.STORYLINE_MEMBERS, "durations_h": climatedt.DURATIONS_H,
                  "polygon": climatedt.polygon_provenance(), **climatedt.attribution_attrs()},
    "bootstrap": {"n": N_BOOT, "seed": RNG_SEED, "resampled": "years (projections), member-years (storylines)"},
}, indent=2, default=str))
