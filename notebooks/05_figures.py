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
# # 05 — Figures
#
# Each figure is saved to `figures/` and displayed inline (`plt.show()` after
# `fig.savefig()`; no `matplotlib.use('Agg')`, which blocks inline display).
#
# Colours: the three climates (or rainfall sources) take the first three categorical slots
# of a palette validated for colour-vision deficiency (blue, orange, aqua); every line is
# labelled directly, because aqua is below 3:1 contrast on white. Before saving, every
# figure passes `scripts/figcheck.py`: no overlapping text, no legend over data.

# %%
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path("../scripts").resolve()))
from figcheck import assert_layout, spread_labels  # noqa: E402

RESULTS = Path("../results")
FIGURES = Path("../figures")
FIGURES.mkdir(parents=True, exist_ok=True)
plt.style.use("seaborn-v0_8-whitegrid")
DPI = 150

CLIMATE_COLOUR = {"present": "#2a78d6", "CC_Q50": "#eb6834", "CC_Q90": "#1baf7a"}
CLIMATE_LABEL = {"present": "present rainfall", "CC_Q50": "future, median (Q50)", "CC_Q90": "future, 90th pct. (Q90)"}
RISK_LABEL = {"PFRMA": "Risk to mobility and accessibility", "PFRWB": "Risk to well-being"}
LAND_LABEL = {"Baseline": "Current green cover", "NBSplanned": "Planned NBS",
              "NBSplanned_plus": "Planned NBS + ponds", "Allgreen": "All open space green"}
TEXT, MUTED = "#0b0b0b", "#52514e"

summary = pd.read_csv(RESULTS / "scenario_summary.csv")
counts = summary[summary["variant"] == "counts"]


def style_axis(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", visible=False)
    ax.tick_params(colors=MUTED, labelsize=9)


# %% [markdown]
# ## Main result: residents in buildings at risk, by return period
#
# Current green cover; every residential building inside the modelled domain. A building
# is "at risk" when its risk index is above zero (the hazard reaches it at ≥ 30 cm).

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharex=True)
base = counts[counts["land_cover"] == "Baseline"]
line_labels = {}
for ax, risk in zip(axes, ["PFRMA", "PFRWB"]):
    d = base[base["risk"] == risk]
    line_labels[ax] = []
    for climate, colour in CLIMATE_COLOUR.items():
        c = d[d["climate"] == climate].sort_values("rp")
        ax.plot(c["rp"], c["residents_at_risk"] / 1000, color=colour, lw=2, marker="o", ms=5,
                markeredgecolor="white", markeredgewidth=1.5)
        line_labels[ax].append((c["rp"].iloc[-1], c["residents_at_risk"].iloc[-1] / 1000, CLIMATE_LABEL[climate]))
    ax.set_xscale("log")
    ax.set_xticks([2, 5, 10, 25, 50, 100, 200], labels=["2", "5", "10", "25", "50", "100", "200"])
    ax.set_xlim(1.7, 3000)  # room for the direct labels
    ax.set_xlabel("Return period of the design storm (years)", color=MUTED, fontsize=9)
    ax.set_title(RISK_LABEL[risk], loc="left", fontsize=11, color=TEXT)
    style_axis(ax)
axes[0].set_ylabel("Residents in buildings at risk (thousands)", color=MUTED, fontsize=9)
fig.suptitle("Logroño: residents in buildings at risk by design storm and rainfall climate",
             x=0.01, ha="left", fontsize=12.5, color=TEXT)
fig.tight_layout()
for ax, items in line_labels.items():
    spread_labels(ax, items, fontsize=8.5, color=TEXT)
assert_layout(fig)
fig.savefig(FIGURES / "main_result.png", dpi=DPI, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## Land cover against climate, 100-year storm
#
# Residents in buildings at risk for each land cover (rows) and rainfall climate (dots).

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharey=True)
rp100 = counts[counts["rp"] == 100]
rows = list(LAND_LABEL)
for ax, risk in zip(axes, ["PFRMA", "PFRWB"]):
    d = rp100[rp100["risk"] == risk]
    for i, lc in enumerate(rows):
        vals = d[d["land_cover"] == lc].set_index("climate")["residents_at_risk"] / 1000
        ax.plot([vals.min(), vals.max()], [i, i], color="#d6d5d0", lw=2, zorder=1)
        for climate, colour in CLIMATE_COLOUR.items():
            if climate in vals:
                ax.scatter(vals[climate], i, s=60, color=colour, edgecolor="white", linewidth=1.5, zorder=2,
                           label=CLIMATE_LABEL[climate] if i == 0 else None)
    ax.set_yticks(range(len(rows)), labels=[LAND_LABEL[r] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("Residents in buildings at risk (thousands)", color=MUTED, fontsize=9)
    ax.set_title(RISK_LABEL[risk], loc="left", fontsize=11, color=TEXT)
    style_axis(ax)
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=3, fontsize=8.5, frameon=False,
           bbox_to_anchor=(0.5, 0.0))
fig.suptitle("100-year storm: residents in buildings at risk by land cover and rainfall climate",
             x=0.01, ha="left", fontsize=12.5, color=TEXT)
fig.tight_layout()
assert_layout(fig)
fig.savefig(FIGURES / "land_cover_rp100.png", dpi=DPI, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## How much heavier is the rainfall? Three sources
#
# Relative change of short-duration rainfall extremes by return period: REACHOUT's scaling
# of its 15-minute design storms (from EURO-CORDEX, 2041–2070 vs 1976–2005), the Climate DT
# projection (IFS-NEMO, SSP3-7.0, 2030–2049 vs 1990–2009, La Rioja; 1-hour and 3-hour
# accumulations, 90 % interval from resampled years shown for 1 hour), and the Climate DT
# storylines (+2 °C against the present, 2017–2024, five members; 1 hour; 90 % interval).

# %%
inventory = pd.read_csv(RESULTS / "reachout_inventory.csv").drop_duplicates(["climate", "rp"])
pub = inventory.pivot(index="rp", columns="climate", values="published_mm")
proj = pd.read_csv(RESULTS / "climatedt_projection_change.csv")
proj = proj[proj["domain"] == "La Rioja"]
story = pd.read_csv(RESULTS / "storyline_change.csv")
story = story[(story["climate"] == "Tplus2.0K") & (story["duration_h"] == 1)]

fig, ax = plt.subplots(figsize=(8.5, 4.6))
for q, ls in (("CC_Q50", "-"), ("CC_Q90", "--")):
    y = 100 * (pub[q] / pub["present"] - 1)
    ax.plot(pub.index, y, color="#2a78d6", lw=2, ls=ls)
    ax.annotate(f"REACHOUT {q[-3:]} (15 min)", (pub.index[-1], y.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=8.5, color=TEXT)
for dur, ls in ((1, "-"), (3, "--")):
    p = proj[proj["duration_h"] == dur].sort_values("rp")
    if dur == 1:  # one band per source keeps the intervals readable
        ax.fill_between(p["rp"], 100 * p["ci_lo"], 100 * p["ci_hi"], color="#eb6834", alpha=0.12, lw=0)
    ax.plot(p["rp"], 100 * p["change"], color="#eb6834", lw=2, ls=ls, marker="o", ms=5,
            markeredgecolor="white", markeredgewidth=1.5)
    ax.annotate(f"Climate DT projection ({dur} h)", (p["rp"].iloc[-1], 100 * p["change"].iloc[-1]),
                xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=TEXT)
s = story.sort_values("rp")
ax.fill_between(s["rp"], 100 * s["ci_lo"], 100 * s["ci_hi"], color="#1baf7a", alpha=0.15, lw=0)
ax.plot(s["rp"], 100 * s["change"], color="#1baf7a", lw=2, marker="o", ms=5, markeredgecolor="white",
        markeredgewidth=1.5)
ax.annotate("Climate DT storylines, +2 °C (1 h)", (s["rp"].iloc[-1], 100 * s["change"].iloc[-1]),
            xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=TEXT)
ax.axhline(0, color="#a3a29b", lw=1)
ax.set_xscale("log")
ax.set_xticks([2, 5, 10, 20, 50, 100, 200], labels=["2", "5", "10", "20", "50", "100", "200"])
ax.set_xlim(1.7, 1200)
ax.set_xlabel("Return period (years)", color=MUTED, fontsize=9)
ax.set_ylabel("Change in rainfall extreme (%)", color=MUTED, fontsize=9)
ax.set_title("Change in short-duration rainfall extremes: REACHOUT's scaling and the Climate DT",
             loc="left", fontsize=12, color=TEXT)
style_axis(ax)
fig.tight_layout()
assert_layout(fig)
fig.savefig(FIGURES / "rainfall_change.png", dpi=DPI, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## Where to look first: vulnerable residents at risk
#
# Residential buildings inside the modelled domain, 100-year storm, current green cover.
# A building is at risk when either risk index is above zero; its colour is the
# vulnerability of its residents (census-section rates, five groups of equal population,
# light = least, dark = most vulnerable). Other buildings are grey. Left: at risk with
# present rainfall. Right: newly at risk with future rainfall (Q90).
# Vulnerability was not validated against impact data, and the measures were modelled only
# as infiltration (SaferRAIN): a map of where to look, not of where to build.
#
# Basemap: Esri World Light Gray Canvas and its reference (labels) layer, fetched when the
# figure is built — context only, nothing is computed from it; the labels are drawn above
# the buildings. CARTO's tiles now require an API key and OpenStreetMap's own tile servers
# refuse automated use, so neither is used. Without network access the map is drawn
# without a basemap.

# %%
import contextily as cx  # noqa: E402
import geopandas as gpd  # noqa: E402
import xyzservices  # noqa: E402

BASE = cx.providers.Esri.WorldGrayCanvas
LABELS = xyzservices.TileProvider(
    name="Esri.WorldGrayReference", attribution=BASE.attribution, max_zoom=16,
    url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}")

GROUP_COLOUR = {1: "#86b6ef", 2: "#5598e7", 3: "#2a78d6", 4: "#1c5cab", 5: "#104281"}
GROUP_LABEL = {1: "least vulnerable fifth", 2: "2nd", 3: "3rd", 4: "4th", 5: "most vulnerable fifth"}
sources = __import__("json").loads((Path("../data/raw/sources.json")).read_text())
CITY = Path(sources["replication"]["path"]) / "data/interim/logrono.gpkg"
geom = gpd.read_file(CITY, layer="buildings")[["ID", "geometry"]]
groups = pd.read_csv(RESULTS / "vulnerability_by_building.csv")
br = pd.read_parquet(RESULTS / "building_risk.parquet",
                     filters=[("variant", "==", "rates"), ("land_cover", "==", "Baseline"), ("rp", "==", 100)])
br["at_risk"] = (br["PFRWB"] > 0) | (br["PFRMA"] > 0)
status = br.pivot_table(index="ID", columns="climate", values="at_risk", aggfunc="first")
gdf = (geom.merge(groups, on="ID").merge(status.reset_index(), on="ID")
       .merge(br[br["climate"] == "present"][["ID", "R"]], on="ID"))
panels = {"At risk with present rainfall": gdf["present"],
          "Newly at risk with future rainfall (Q90)": gdf["CC_Q90"] & ~gdf["present"]}

def add_basemap(ax) -> bool:
    """Light tiles below the data and their labels above it; False if the tiles cannot be fetched."""
    try:
        cx.add_basemap(ax, crs=geom.crs, source=BASE, attribution=False, zorder=0)
        cx.add_basemap(ax, crs=geom.crs, source=LABELS, attribution=False, zorder=10)
        return True
    except Exception as exc:  # noqa: BLE001 - context layer only, never fail the figure on it
        print(f"basemap not drawn ({type(exc).__name__}): {str(exc)[:120]}")
        return False


def scale_bar(ax, length_m: float = 1000.0) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x0 + 0.04 * (x1 - x0), y0 + 0.05 * (y1 - y0)
    ax.plot([x, x + length_m], [y, y], color=TEXT, lw=3, solid_capstyle="butt", zorder=11)
    ax.text(x + length_m / 2, y + 0.015 * (y1 - y0), f"{length_m / 1000:g} km", ha="center", va="bottom",
            fontsize=8.5, color=TEXT, zorder=11)


urban = gpd.read_file(CITY, layer="urban_area").total_bounds
fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
basemap = []
for ax, (title, mask) in zip(axes, panels.items()):
    ax.set_xlim(urban[0], urban[2])
    ax.set_ylim(urban[1], urban[3])
    geom.plot(ax=ax, color="#d6d5d0", linewidth=0, alpha=0.6)
    for g, colour in GROUP_COLOUR.items():
        sel = gdf[mask & (gdf["vulnerability_group"] == g)]
        if len(sel):  # outline in the fill colour keeps small buildings visible at city scale
            sel.plot(ax=ax, color=colour, edgecolor=colour, linewidth=1.2)
    ax.set_xlim(urban[0], urban[2])
    ax.set_ylim(urban[1], urban[3])
    basemap.append(add_basemap(ax))
    scale_bar(ax)
    ax.set_title(f"{title}\n{int(mask.sum())} buildings, {gdf.loc[mask, 'R'].sum():,.0f} residents",
                 loc="left", fontsize=11, color=TEXT)
    ax.set_axis_off()
if all(basemap):
    fig.text(0.99, 0.08, f"Basemap: {BASE.attribution}", ha="right", fontsize=7, color=MUTED)
handles = [plt.Line2D([], [], marker="s", ls="", color=c, markersize=9, label=GROUP_LABEL[g])
           for g, c in GROUP_COLOUR.items()]
fig.legend(handles=handles, loc="upper center", ncol=5, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 0.02))
fig.suptitle("Logroño (La Rioja, Spain), 100-year storm: residential buildings at risk by residents' social vulnerability",
             x=0.01, ha="left", fontsize=12.5, color=TEXT)
fig.tight_layout()
assert_layout(fig)
fig.savefig(FIGURES / "priority_map.png", dpi=DPI, bbox_inches="tight")
plt.show()
