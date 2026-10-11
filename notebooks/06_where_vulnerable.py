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
# # 06 — Why greening helps the most vulnerable residents least
#
# Notebook 03 found that converting all open space to green surfaces mainly takes less
# socially vulnerable residents out of pluvial flood risk. That raises a planning question:
# would placing greening near the most vulnerable residents help them? In this flood model
# the all-green scenario is already an upper bound for that, since it greens every open
# space, including all of it around their homes. This notebook asks where the residents at
# risk live and how much the all-green scenario lowers their hazard, comparing the most
# vulnerable fifth with the least vulnerable fifth.
#
# **Exploratory.** These questions were asked after seeing notebook 03's result, not
# before; the comparisons are descriptive and are counted over every map, not tested.
#
# For every map (climate × return period) and both risks, among residents at risk under
# REACHOUT's planned scenario with ponds:
#
# 1. **Room to green**: share of land within 100 m of each building in Urban Atlas 2018
#    classes that could be greened (low-density fabric, construction sites, land without
#    use, green urban areas, sports and leisure, farmland, forest and semi-natural land).
#    REACHOUT does not publish the cells its all-green scenario changes, so this is a
#    proxy for where greening can act, not REACHOUT's layer.
# 2. **Hazard**: the risk's hazard at the building (HWB for well-being, HMA for mobility),
#    which grows with the depth and extent of water around it.
# 3. **Effect of all-green**: the resident-weighted drop of that hazard from the planned
#    scenario with ponds to the all-green scenario, and the share of residents whose hazard
#    drops at all or reaches zero (out of risk).

# %%
import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path("../scripts").resolve()))
from figcheck import assert_layout  # noqa: E402

RESULTS = Path("../results")
FIGURES = Path("../figures")
CRS = "EPSG:25830"
sources = json.loads(Path("../data/raw/sources.json").read_text())
REPLICATION = Path(sources["replication"]["path"])
CITY = REPLICATION / "data/interim/logrono.gpkg"
URBAN_ATLAS = REPLICATION / "data/raw/urban_atlas_2018_logrono.geojson"

PLANNED, GREEN = "NBSplanned_plus", "Allgreen"
RISKS = {"PFRWB": "HWB", "PFRMA": "HMA"}
GREENABLE = ["11230", "11240", "13300", "13400", "14100", "14200",
             "21000", "22000", "23000", "31000", "32000", "40000"]
RADIUS = 100.0

plt.style.use("seaborn-v0_8-whitegrid")
DPI = 150
GROUP_COLOUR = {1: "#86b6ef", 5: "#104281"}
GROUP_LABEL = {1: "least vulnerable fifth", 5: "most vulnerable fifth"}
TEXT, MUTED = "#0b0b0b", "#52514e"

# %% [markdown]
# ## 1. Inputs
#
# Building-level hazards and risks for every map (03, `counts` variant: the at-risk sets
# and hazards do not depend on the variant), vulnerability groups (03), buildings with
# their census section, and Urban Atlas 2018.

# %%
risk = pd.read_parquet(RESULTS / "building_risk.parquet", filters=[("variant", "==", "counts")])
group = pd.read_csv(RESULTS / "vulnerability_by_building.csv").set_index("ID")["vulnerability_group"]
buildings = gpd.read_file(CITY, layer="buildings").to_crs(CRS).set_index("ID")
ua = gpd.read_file(URBAN_ATLAS).to_crs(CRS)
ua["code"] = ua["code_2018"].astype(str)
greenable = ua.loc[ua["code"].isin(GREENABLE)].geometry.union_all()

ids = group.index.intersection(buildings.index)
zones = buildings.loc[ids].geometry.buffer(RADIUS)
room = pd.Series(zones.intersection(greenable).area.to_numpy() / zones.area.to_numpy(), index=ids)
cent = gpd.GeoDataFrame(geometry=buildings.loc[ids].geometry.representative_point(), crs=CRS)
landuse = gpd.sjoin(cent, ua[["class_2018", "geometry"]], how="left", predicate="within")
landuse = landuse[~landuse.index.duplicated()]["class_2018"]
print(f"{len(ids):,} assessed buildings; greenable land within {RADIUS:.0f} m: "
      f"median {room.median():.1%}")

# %% [markdown]
# ## 2. Every map, both risks: least vs most vulnerable fifth

# %%
def weighted(x: pd.Series, w: pd.Series) -> float:
    return float(np.average(x, weights=w)) if w.sum() > 0 else np.nan


rows = []
for (cl, rp), g in risk[risk["land_cover"].isin([PLANNED, GREEN])].groupby(["climate", "rp"]):
    p = g[g["land_cover"] == PLANNED].set_index("ID")
    q = g[g["land_cover"] == GREEN].set_index("ID").reindex(p.index)
    if p.empty or q.isna().all().all():
        continue
    for r, h in RISKS.items():
        at = p[r] > 0
        for k in GROUP_LABEL:
            m = at & (group.reindex(p.index) == k)
            w = p.loc[m, "R"]
            hp, hg = p.loc[m, h], q.loc[m, h]
            rows.append({"climate": cl, "rp": rp, "risk": r, "group": k,
                         "buildings": int(m.sum()), "residents": float(w.sum()),
                         "greenable_share": weighted(room.reindex(w.index), w),
                         "hazard": weighted(hp, w),
                         "hazard_drop": 1 - float((hg * w).sum() / (hp * w).sum()) if (hp * w).sum() > 0 else np.nan,
                         "share_hazard_drops": float(w[hg < hp - 1e-9].sum() / w.sum()) if w.sum() else np.nan,
                         "share_out_of_risk": float(w[q.loc[m, r] <= 0].sum() / w.sum()) if w.sum() else np.nan})
table = pd.DataFrame(rows)
table.to_csv(RESULTS / "where_vulnerable.csv", index=False)

wide = table.pivot_table(index=["climate", "rp", "risk"], columns="group",
                         values=["greenable_share", "hazard", "hazard_drop", "share_out_of_risk"])
n = len(wide)
counts = {"less room to green (most vulnerable)": int((wide["greenable_share"][5] < wide["greenable_share"][1]).sum()),
          "higher hazard (most vulnerable)": int((wide["hazard"][5] > wide["hazard"][1]).sum()),
          "smaller hazard drop with all-green (most vulnerable)": int((wide["hazard_drop"][5] < wide["hazard_drop"][1]).sum()),
          "fewer taken out of risk (most vulnerable)": int((wide["share_out_of_risk"][5] < wide["share_out_of_risk"][1]).sum())}
for k, v in counts.items():
    print(f"{k}: {v} of {n} comparisons")
(RESULTS / "where_vulnerable_counts.json").write_text(json.dumps({"comparisons": n, **counts}, indent=2))

show = table[(table["rp"].isin([10, 100])) & (table["climate"].isin(["present", "CC_Q90"]))]
print(show.round(3).to_string(index=False))

# %% [markdown]
# ## 3. Where the most vulnerable residents at risk live
#
# Future rainfall (Q90), 100-year storm, planned scenario with ponds, at risk for either
# risk: land use at the building and the census sections holding the residents at risk of
# the two most vulnerable fifths. The sections table is for planners: where to look first,
# not where to build (vulnerability is not validated against impact data).

# %%
p = risk[(risk["land_cover"] == PLANNED) & (risk["climate"] == "CC_Q90") & (risk["rp"] == 100)].set_index("ID")
at = (p["PFRWB"] > 0) | (p["PFRMA"] > 0)
for k in GROUP_LABEL:
    m = at & (group.reindex(p.index) == k)
    share = p.loc[m, "R"].groupby(landuse.reindex(p.index[m])).sum() / p.loc[m, "R"].sum()
    print(f"{GROUP_LABEL[k]}: " + "; ".join(f"{c} {v:.0%}" for c, v in share.nlargest(3).items()))

m = at & (group.reindex(p.index) >= 4)
sec = pd.DataFrame({"CUSEC": buildings.loc[p.index[m], "CUSEC"], "district": buildings.loc[p.index[m], "CDIS"],
                    "R": p.loc[m, "R"], "HWB": p.loc[m, "HWB"], "room": room.reindex(p.index[m])})
sections = (sec.groupby(["CUSEC", "district"])
            .apply(lambda s: pd.Series({"buildings": len(s), "residents_at_risk": s["R"].sum(),
                                        "mean_HWB": weighted(s["HWB"], s["R"]),
                                        "greenable_share": weighted(s["room"], s["R"])}), include_groups=False)
            .reset_index().sort_values("residents_at_risk", ascending=False))
sections.to_csv(RESULTS / "where_vulnerable_sections.csv", index=False)
print(f"{len(sections)} sections; the top 5 hold "
      f"{sections['residents_at_risk'].head(5).sum() / sections['residents_at_risk'].sum():.0%} of these residents")
print(sections.head(10).round(3).to_string(index=False))

# %% [markdown]
# ## 4. Figure
#
# Left: room to green and hazard of the residents at risk, by fifth (future rainfall Q90,
# 100-year storm, risk to well-being). Right: drop of the well-being hazard with all open
# space green, by return period (future rainfall Q90; REACHOUT's all-green 25-year map for
# Q90 is an empty file, so that point is missing).

# %%
sel = table[(table["climate"] == "CC_Q90") & (table["risk"] == "PFRWB")]
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
at100 = sel[sel["rp"] == 100].set_index("group")
for ax, col, title, fmt in [(axes[0], "greenable_share", f"Land that could be greened\nwithin {RADIUS:.0f} m", "{:.0%}"),
                            (axes[1], "hazard", "Well-being hazard at home\n(deeper, wider water = higher)", "{:.2f}")]:
    vals = [at100.loc[k, col] for k in GROUP_LABEL]
    bars = ax.bar([GROUP_LABEL[k] for k in GROUP_LABEL], vals, color=[GROUP_COLOUR[k] for k in GROUP_LABEL])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, fmt.format(v), ha="center", va="bottom", fontsize=9, color=TEXT)
    ax.set_title(title, fontsize=10, color=TEXT)
    ax.set_yticks([])
    ax.grid(False)
    ax.set_ylim(0, max(vals) * 1.25)
    ax.tick_params(colors=MUTED, labelsize=9)
ax = axes[2]
for k in GROUP_LABEL:
    s = sel[sel["group"] == k].sort_values("rp")
    ax.plot(s["rp"].astype(str), 100 * s["hazard_drop"], marker="o", color=GROUP_COLOUR[k], label=GROUP_LABEL[k])
ax.set_title("Hazard drop with all open space green (%)", fontsize=10, color=TEXT)
ax.set_xlabel("return period (years)", color=MUTED)
ax.legend(frameon=False, fontsize=8.5)
ax.tick_params(colors=MUTED, labelsize=9)
for a in axes:
    a.spines[["top", "right"]].set_visible(False)
fig.suptitle("Residents at pluvial flood risk in Logroño (planned NBS + ponds), future rainfall Q90",
             fontsize=11, color=TEXT)
fig.tight_layout()
assert_layout(fig)
fig.savefig(FIGURES / "where_vulnerable.png", dpi=DPI, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## Limitations
#
# - Exploratory: asked after notebook 03's result; counts over maps are not independent.
# - "Room to green" is an Urban Atlas proxy; REACHOUT's all-green layer is not published.
# - SaferRAIN represents greening only as infiltration, without sewers or storage; other
#   measures (storage, drainage, building protection) cannot be assessed with these maps.
# - Vulnerability comes from census-section rates and is not validated against impacts;
#   residents are fixed at 2021.
