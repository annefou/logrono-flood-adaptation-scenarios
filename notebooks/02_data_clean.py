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
# # 02 — Flood scenarios: inventory and flood extents
#
# REACHOUT's archive holds 12 scenarios — four land covers × three rainfall climates —
# each for seven return periods (15-minute design storms, SaferRAIN). This notebook
#
# 1. records what the archive contains, the rainfall each map was run with (from the
#    metadata embedded in every GeoTIFF) and its defects;
# 2. checks that the two raster grids in the archive line up cell for cell;
# 3. polygonises the flood extents (depth ≥ 30, 40, … 100 cm) of every scenario and
#    return period with the replication's rule, so every scenario is compared on the
#    same ground with the same method.
#
# | Land cover | REACHOUT's description (Zenodo 10.5281/zenodo.14035876) |
# |---|---|
# | `Baseline` | current green cover |
# | `NBSplanned` | baseline + additional 4 bioswales/ponds (= 29,850 m3) and a green corridor (5.3 km x 5 m) in the southern part of the city |
# | `NBSplanned_plus` | NBS planned scenarios + additional small ponds/rain gardens (depth 0.5 m, 13,500 m3) |
# | `Allgreen` | baseline + all open spaces converted to green |
#
# Climates: present (observed station rainfall, SOS-Logroño 1999–2022), `CC_Q50` and
# `CC_Q90` (observations scaled by the median and 90th-percentile EURO-CORDEX change,
# 2041–2070 vs 1976–2005; checked in `04_climate`).

# %%
import base64
import json
import re
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.features
import rasterio.windows
from pyproj import Transformer
from shapely.geometry import shape

# %%
RAW = Path("../data/raw")
REPLICATION = Path(json.loads((RAW / "sources.json").read_text())["replication"]["path"])
CITY = REPLICATION / "data/interim/logrono.gpkg"
ARCHIVE = REPLICATION / "data/raw/PluvialFloodMap_Logrono.zip"
REACHOUT_MD5 = "324f1558766b10b613815b9e15d37a58"
INTERIM = Path("../data/interim")
FLOODS = INTERIM / "floods"
FLOODS.mkdir(parents=True, exist_ok=True)
RESULTS = Path("../results")
RESULTS.mkdir(parents=True, exist_ok=True)

CRS = "EPSG:25830"
LAND_COVERS = ["Baseline", "NBSplanned", "NBSplanned_plus", "Allgreen"]
CLIMATES = ["present", "CC_Q50", "CC_Q90"]
RETURN_PERIODS = {2: "A", 5: "B", 10: "C", 25: "D", 50: "E", 100: "F", 200: "G"}
DEPTHS_CM = list(range(30, 101, 10))
HAZARD_MARGIN_M = 100.0         # as the replication: flood polygons up to 100 m beyond the urban area

# Rainfall per return period as published in REACHOUT's Zenodo description (mm in 15 min).
PUBLISHED_MM = {
    "present": [9.79, 13.51, 16.27, 20.15, 23.33, 26.77, 30.50],
    "CC_Q50": [10.49, 14.91, 18.32, 23.18, 26.61, 31.25, 35.40],
    "CC_Q90": [11.83, 16.76, 20.96, 26.87, 32.27, 38.99, 46.65],
}


def scenario(land_cover: str, climate: str) -> str:
    return land_cover if climate == "present" else f"{land_cover}_{climate}"


def member(land_cover: str, climate: str, rp: int) -> str:
    suffix = "" if climate == "present" else "_" + climate.split("_")[1]
    return f"Logrono/{scenario(land_cover, climate)}/{RETURN_PERIODS[rp]}_RP{rp}{suffix}.tif"


# %% [markdown]
# ## 1. What the archive contains
#
# One row per land cover × climate × return period: whether the GeoTIFF exists and is
# readable, its grid, its NoData value, and the rainfall and infiltration layer decoded
# from its embedded description.

# %%
def read_metadata(path: str) -> dict:
    with rasterio.open(f"/vsizip/{ARCHIVE}/{path}") as r:
        text = base64.b64decode(r.tags()["description"]).decode()
        return {"rows": r.height, "cols": r.width, "nodata": r.nodata,
                "x0": r.transform.c, "y0": r.transform.f, "res": r.res[0],
                "rain_mm": float(re.search(r"rain of ([\d.]+)mm", text).group(1)),
                "duration_h": float(re.search(r"duration ([\d.]+)h", text).group(1)),
                "infiltration_layer": re.search(r"infiltration layer: (\S+)", text).group(1)
                .removeprefix("./").removesuffix(".shp"),
                "type": r.tags()["type"], "unit": r.tags()["um"]}


with zipfile.ZipFile(ARCHIVE) as z:
    sizes = {i.filename: i.file_size for i in z.infolist()}

rows = []
for lc in LAND_COVERS:
    for cl in CLIMATES:
        for i, rp in enumerate(RETURN_PERIODS):
            path = member(lc, cl, rp)
            row = {"land_cover": lc, "climate": cl, "rp": rp, "published_mm": PUBLISHED_MM[cl][i]}
            if path not in sizes:
                row["status"] = "missing"
            elif sizes[path] == 0:
                row["status"] = "empty file"
            else:
                row |= {"status": "ok", **read_metadata(path)}
            rows.append(row)
inventory = pd.DataFrame(rows)
inventory["rain_matches_published"] = np.isclose(inventory["rain_mm"], inventory["published_mm"])
inventory.to_csv(RESULTS / "reachout_inventory.csv", index=False)

print(inventory.pivot_table(index=["land_cover", "climate"], columns="rp", values="rain_mm",
                            aggfunc="first", sort=False).to_string())
problems = inventory[(inventory["status"] != "ok") | ~inventory["rain_matches_published"]]
print("\nNot usable as published:")
print(problems[["land_cover", "climate", "rp", "status", "rain_mm", "published_mm"]].to_string(index=False))

# %%
ok = inventory[inventory["status"] == "ok"]
assert (ok["duration_h"] == 0.25).all() and (ok["type"] == "waterdepth").all() and (ok["unit"] == "m").all()
print(ok.groupby(["land_cover", "climate"], sort=False)["infiltration_layer"].unique().to_string())
print(ok.groupby(["land_cover", "climate"], sort=False)["nodata"].unique().to_string())

# %% [markdown]
# ## 2. Grids
#
# The archive has two grids: Baseline and Allgreen at present climate (8230 × 9604
# cells), all other maps on a smaller one (5696 × 8002). Both are labelled EPSG:32632
# (UTM zone 32, see the replication's `02_data_clean` §4). They line up if the smaller
# grid's origin is a whole number of cells from the larger one's and the cell sizes agree.
# The study extent (the replication's: urban area + 130 m, as a box) must lie inside the
# smaller grid, so that every scenario covers the same ground.

# %%
grids = ok.groupby(["rows", "cols"]).agg(x0=("x0", "first"), y0=("y0", "first"),
                                         res_min=("res", "min"), res_max=("res", "max"),
                                         maps=("rp", "size")).reset_index()
print(grids.to_string(index=False))
big, small = grids.sort_values("rows", ascending=False).iloc[0], grids.sort_values("rows").iloc[0]
offset = ((small["x0"] - big["x0"]) / big["res_min"], (big["y0"] - small["y0"]) / big["res_min"])
print(f"small grid origin = big grid origin + {offset[0]:.4f} cols, {offset[1]:.4f} rows")
assert all(abs(o - round(o)) < 1e-3 for o in offset)
assert grids["res_max"].max() - grids["res_min"].min() < 1e-9

urban = gpd.read_file(CITY, layer="urban_area")
extent = urban.buffer(HAZARD_MARGIN_M + 30).envelope.iloc[0]
to_utm32 = Transformer.from_crs(CRS, "EPSG:32632", always_xy=True)
ex = to_utm32.transform_bounds(*extent.bounds)
small_bounds = (small["x0"], small["y0"] - small["rows"] * small["res_min"],
                small["x0"] + small["cols"] * small["res_min"], small["y0"])
assert ex[0] > small_bounds[0] and ex[1] > small_bounds[1] and ex[2] < small_bounds[2] and ex[3] < small_bounds[3]
print("study extent lies inside the smaller grid: all scenarios cover it")

# %% [markdown]
# ## 3. Modelled domain
#
# Two kinds of empty cell occur, and they mean different things:
#
# - **NaN** — modelled, no water (every map uses it for dry ground);
# - **NoData** (−9999 or −999999) — **not modelled**. Only the maps on the smaller grid have
#   it: those runs covered a smaller domain than the present-climate Baseline and Allgreen.
#
# Read as dry, NoData would turn every cell outside a run's domain into an "improvement".
# The comparison domain is therefore the cells modelled in **every** map; outside it no map
# is used, including the present-climate Baseline. Written as a polygon (EPSG:25830) for 03,
# which excludes buildings whose hazard rings leave it.

# %%
water = gpd.read_file(CITY, layer="water").geometry.union_all()


def read_depth(path: str) -> tuple[np.ndarray, np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
    """Depth over the study extent (NaN = dry -> 0) and the mask of modelled cells (not NoData)."""
    with rasterio.open(f"/vsizip/{ARCHIVE}/{path}") as src:
        window = rasterio.windows.from_bounds(*ex, transform=src.transform).round_offsets().round_lengths()
        raw = src.read(1, window=window)
        modelled = raw != src.nodata
        depth = np.where(modelled, np.nan_to_num(raw, nan=0.0), 0.0)
        return depth, modelled, src.window_transform(window), src.crs


domain_mask, domain_rows = None, []
for m in ok.itertuples():
    _, modelled, tf, src_crs = read_depth(member(m.land_cover, m.climate, m.rp))
    domain_rows.append({"land_cover": m.land_cover, "climate": m.climate, "rp": m.rp,
                        "modelled_km2": modelled.sum() * small["res_min"] ** 2 / 1e6})
    domain_mask = modelled if domain_mask is None else domain_mask & modelled
domain_rows = pd.DataFrame(domain_rows)
print(domain_rows.groupby(["land_cover", "climate"], sort=False)["modelled_km2"].agg(["min", "max"]).round(2).to_string())

geoms = [shape(g) for g, _ in rasterio.features.shapes(domain_mask.astype("uint8"), mask=domain_mask, transform=tf)]
domain = gpd.GeoSeries(geoms, crs=src_crs).to_crs(CRS).union_all()
gpd.GeoDataFrame(geometry=[domain], crs=CRS).to_file(INTERIM / "domain.gpkg", layer="domain", driver="GPKG")
print(f"common modelled domain: {domain_mask.sum() * small['res_min'] ** 2 / 1e6:.2f} km² of the "
      f"{domain_mask.size * small['res_min'] ** 2 / 1e6:.2f} km² study extent")

# %% [markdown]
# ## 4. Flood extents
#
# The replication's rule, otherwise unchanged: depths are **not resampled**; each threshold
# is polygonised on the native 2 m grid, inside the common domain, the polygons are
# transformed to EPSG:25830, and water bodies (Urban Atlas class 50000) are removed — the
# rain-on-grid model also fills the Ebro's bed.
#
# One GeoPackage per scenario, one layer per return period and threshold
# (`rp100_30` … `rp100_100`). Alongside, the depth rasters are compared cell by cell with
# the present-climate Baseline of the same return period, inside the domain (§5).

# %%
def polygons(depth: np.ndarray, transform, src_crs) -> dict[int, gpd.GeoSeries]:
    out = {}
    for d in DEPTHS_CM:
        wet = (depth >= d / 100).astype("uint8")
        geoms = [shape(g) for g, _ in rasterio.features.shapes(wet, mask=wet == 1, transform=transform)]
        g = gpd.GeoSeries(geoms, crs=src_crs).to_crs(CRS).difference(water).explode(index_parts=False)
        out[d] = g[~g.is_empty]
    return out


# %% [markdown]
# ## 5. Cell-by-cell change against the present-climate Baseline
#
# On the native grid, inside the common domain, water bodies included (this describes the
# maps themselves): cells whose depth changes by more than 1 cm, cells at ≥ 30 cm, and the
# change in stored water volume (m³; each cell is 2 m × 2 m in UTM 32 units).

# %%
CELL_M2 = small["res_min"] ** 2
stats, done = [], 0
for rp in RETURN_PERIODS:
    ref, _, ref_tf, _ = read_depth(member("Baseline", "present", rp))
    ref = np.where(domain_mask, ref, 0.0)
    for lc in LAND_COVERS:
        for cl in CLIMATES:
            if inventory.query("land_cover == @lc and climate == @cl and rp == @rp")["status"].iloc[0] != "ok":
                continue
            depth, _, tf, src_crs = read_depth(member(lc, cl, rp))
            assert depth.shape == ref.shape and tf.almost_equals(ref_tf)
            depth = np.where(domain_mask, depth, 0.0)
            diff = depth - ref
            stats.append({"land_cover": lc, "climate": cl, "rp": rp,
                          "cells_ge30": int((depth >= 0.3).sum()),
                          "cells_ge30_baseline": int((ref >= 0.3).sum()),
                          "cells_shallower": int((diff < -0.01).sum()),
                          "cells_deeper": int((diff > 0.01).sum()),
                          "volume_m3": float(depth.sum() * CELL_M2),
                          "volume_change_m3": float(diff.sum() * CELL_M2)})
            gpkg = FLOODS / f"{scenario(lc, cl)}.gpkg"
            for d, g in polygons(depth, tf, src_crs).items():
                gpd.GeoDataFrame(geometry=g.values, crs=CRS).to_file(gpkg, layer=f"rp{rp}_{d}", driver="GPKG")
            done += 1
    print(f"RP{rp}: {done} maps polygonised so far")

stats = pd.DataFrame(stats)
stats.to_csv(RESULTS / "hazard_cell_changes.csv", index=False)
print(stats[stats["rp"] == 100].to_string(index=False))
