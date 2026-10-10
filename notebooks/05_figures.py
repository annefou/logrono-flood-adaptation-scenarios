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
# labelled directly, because aqua is below 3:1 contrast on white.

# %%
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
for ax, risk in zip(axes, ["PFRMA", "PFRWB"]):
    d = base[base["risk"] == risk]
    for climate, colour in CLIMATE_COLOUR.items():
        c = d[d["climate"] == climate].sort_values("rp")
        ax.plot(c["rp"], c["residents_at_risk"] / 1000, color=colour, lw=2, marker="o", ms=5,
                markeredgecolor="white", markeredgewidth=1.5)
        ax.annotate(CLIMATE_LABEL[climate], (c["rp"].iloc[-1], c["residents_at_risk"].iloc[-1] / 1000),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=TEXT)
    ax.set_xscale("log")
    ax.set_xticks([2, 5, 10, 25, 50, 100, 200], labels=["2", "5", "10", "25", "50", "100", "200"])
    ax.set_xlim(1.7, 900)
    ax.set_xlabel("Return period of the design storm (years)", color=MUTED, fontsize=9)
    ax.set_title(RISK_LABEL[risk], loc="left", fontsize=11, color=TEXT)
    style_axis(ax)
axes[0].set_ylabel("Residents in buildings at risk (thousands)", color=MUTED, fontsize=9)
fig.suptitle("Logroño: residents in buildings at risk by design storm and rainfall climate",
             x=0.01, ha="left", fontsize=12.5, color=TEXT)
fig.tight_layout()
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
axes[1].legend(loc="lower right", fontsize=8.5, frameon=False)
fig.suptitle("100-year storm: residents in buildings at risk by land cover and rainfall climate",
             x=0.01, ha="left", fontsize=12.5, color=TEXT)
fig.tight_layout()
fig.savefig(FIGURES / "land_cover_rp100.png", dpi=DPI, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## How much heavier is the rainfall? Three sources
#
# Relative change of short-duration rainfall extremes by return period: REACHOUT's scaling
# of its 15-minute design storms (from EURO-CORDEX, 2041–2070 vs 1976–2005), the Climate DT
# projection (IFS-NEMO, SSP3-7.0, 2030–2049 vs 1990–2009, La Rioja; 1-hour and 3-hour
# accumulations, 90 % intervals from resampled years), and the Climate DT storylines
# (+2 °C against the present, 2017–2024, five members; 1 hour).

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
ax.set_xticks([2, 5, 10, 20, 25, 50, 100, 200], labels=["2", "5", "10", "20", "25", "50", "100", "200"])
ax.set_xlim(1.7, 1200)
ax.set_xlabel("Return period (years)", color=MUTED, fontsize=9)
ax.set_ylabel("Change in rainfall extreme (%)", color=MUTED, fontsize=9)
ax.set_title("Change in short-duration rainfall extremes: REACHOUT's scaling and the Climate DT",
             loc="left", fontsize=12, color=TEXT)
style_axis(ax)
fig.tight_layout()
fig.savefig(FIGURES / "rainfall_change.png", dpi=DPI, bbox_inches="tight")
plt.show()
