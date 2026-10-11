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
# # 03 — Building-level risk under every flood scenario
#
# **Method**: `building-climate-risk` v0.2.1 (pinned in `pixi.toml`) with the settings of
# the Logroño replication (v0.1.1), unchanged: TOPSIS weights children 0.3 / elderly
# singles 0.7, welfare 0.5 / education 0.5, SVI 0.5 / 0.5; threshold 0.25 × mean, exponent
# 2; HWB ring 2 m over depths ≥ 30…100 cm; HMA rings 5 / 15 / 30 m at 30 cm.
#
# Only the hazard changes between scenarios: social vulnerability and exposure (residents
# fixed at the 2021 census) are the same in every scenario.
#
# **Classes.** The authors' rule (three iterated means) sets the class limits from each
# map's own distribution of risk, so a uniform increase of risk would leave the classes
# unchanged. Every scenario is therefore classed twice:
#
# - `fixed` — with the limits of the present-climate Baseline of the same return period
#   (the comparison used for scenario results);
# - `own` — with the authors' rule applied to the scenario itself (as the paper would).
#
# **Indicators.** Both versions from the replication: counts per building (the paper's
# definition, under which social vulnerability largely re-counts residents) and
# census-section rates.
#
# Every scenario × return period × indicator version is computed and written; nothing is
# selected here. This notebook only measures. Interpretation belongs in the Outcome.

# %%
import json
import platform
import time
from importlib.metadata import version
from pathlib import Path

import building_climate_risk as bcr
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from building_climate_risk.hazards import pluvial

# %%
RAW = Path("../data/raw")
REPLICATION = Path(json.loads((RAW / "sources.json").read_text())["replication"]["path"])
CITY = REPLICATION / "data/interim/logrono.gpkg"
FLOODS = Path("../data/interim/floods")
RESULTS = Path("../results")
CRS = "EPSG:25830"
DEPTHS_CM = list(range(30, 101, 10))
HOT = 3  # "high" and "very high" classes: the replication's hotspots

SPEC = {
    "vulnerability": {"sensitivity": {"columns": ["C", "ES"], "weights": [0.3, 0.7]},
                      "coping": {"columns": ["WR", "EDQ"], "weights": [0.5, 0.5]},
                      "svi_weights": [0.5, 0.5], "threshold": 0.25, "exponent": 2.0},
    "risks": {"PFRWB": {"exposure": "R_G", "hazard": "HWB"},
              "PFRMA": {"exposure": "R", "hazard": "HMA"}},
    "classes": {"iterations": 3},
}
RISKS = list(SPEC["risks"])

inventory = pd.read_csv(RESULTS / "reachout_inventory.csv")
maps = inventory[inventory["status"] == "ok"][["land_cover", "climate", "rp"]].reset_index(drop=True)
print(f"{len(maps)} usable maps of {len(inventory)}")


def scenario(land_cover: str, climate: str) -> str:
    return land_cover if climate == "present" else f"{land_cover}_{climate}"


def city(layer: str) -> gpd.GeoDataFrame:
    return gpd.read_file(CITY, layer=layer)


buildings = city("buildings")
streets = city("streets").geometry
print(f"{len(buildings):,} buildings, {int((buildings['R'] > 0).sum()):,} with residents")

# %% [markdown]
# **Domain.** Every scenario was modelled only inside the common domain written by 02
# (cells modelled in every map). A building's hazards are known only if its widest ring
# (30 m) lies inside it; the others are excluded from the risk assessment.

# %%
domain = gpd.read_file(Path("../data/interim/domain.gpkg"), layer="domain").geometry.iloc[0]
buildings["in_domain"] = buildings.geometry.buffer(30.0).within(domain)
out = buildings[~buildings["in_domain"]]
print(f"outside the domain: {len(out):,} buildings, {int((out['R'] > 0).sum())} with residents "
      f"({out['R'].sum():,.0f} of {buildings['R'].sum():,.0f} residents)")

# %% [markdown]
# ## 1. Hazards for every map
#
# The rings around each building do not depend on the flood map, so they are built once
# with the library's own functions and reused; the result is checked against
# `pluvial.hazard_wellbeing` and `pluvial.mobility_fractions` on the present-climate
# Baseline, 100-year storm.

# %%
fp = buildings.geometry
RINGS = {"hwb": bcr.rings_without_buildings(fp, 2.0),
         "near": bcr.rings_without_buildings(fp, 5.0),
         "inner": bcr.clip_to(bcr.rings_without_buildings(fp, 15.0), streets),
         "outer": bcr.clip_to(bcr.annulus(fp, 15.0, 30.0), streets)}


def floods_of(land_cover: str, climate: str, rp: int) -> dict[int, gpd.GeoSeries]:
    gpkg = FLOODS / f"{scenario(land_cover, climate)}.gpkg"
    return {d: gpd.read_file(gpkg, layer=f"rp{rp}_{d}").geometry for d in DEPTHS_CM}


def hazards(floods: dict[int, gpd.GeoSeries]) -> pd.DataFrame:
    fr = {"f_near": bcr.covered_fraction(RINGS["near"], floods[30]),
          "f_inner": bcr.covered_fraction(RINGS["inner"], floods[30]),
          "f_outer": bcr.covered_fraction(RINGS["outer"], floods[30])}
    hwb = sum(bcr.lognormal_cdf(bcr.covered_fraction(RINGS["hwb"], floods[d])) for d in DEPTHS_CM)
    return pd.DataFrame({"HWB": hwb, "HMA": pluvial.hazard_mobility(fr), **fr}, index=buildings.index)


t0 = time.time()
check_floods = floods_of("Baseline", "present", 100)
check = hazards(check_floods)
print(f"one map: {time.time() - t0:.0f} s")
ref_hwb = pluvial.hazard_wellbeing(fp, check_floods, buffer=2.0)
ref_hma = pluvial.hazard_mobility(pluvial.mobility_fractions(fp, check_floods[30], streets))
assert np.allclose(check["HWB"], ref_hwb) and np.allclose(check["HMA"], ref_hma)
print("cached rings reproduce the library's hazards exactly")

# %%
hz = []
for m in maps.itertuples():
    h = check if (m.land_cover, m.climate, m.rp) == ("Baseline", "present", 100) else \
        hazards(floods_of(m.land_cover, m.climate, m.rp))
    hz.append(h.assign(ID=buildings["ID"].values, land_cover=m.land_cover, climate=m.climate, rp=m.rp))
hz = pd.concat(hz, ignore_index=True)
hz.to_parquet(RESULTS / "hazards.parquet", index=False)
print(f"{len(maps)} maps in {time.time() - t0:.0f} s")

# %% [markdown]
# ## 2. Risk and classes
#
# Risk is assessed over the buildings with residents, as in the replication, inside the
# domain (above).

# %%
#
# Social vulnerability does not depend on the flood map, so it is ranked (TOPSIS) over all
# residential buildings of the city, as in the replication; risk and its classes are then
# computed over the buildings inside the domain.

# %%
all_residents = buildings[buildings["R"] > 0].reset_index(drop=True)
sections = city("sections").set_index("CUSEC")
RATE_COLS = ("C", "ES", "WR", "EDQ")
VARIANT_DATA = {
    "counts": all_residents,
    "rates": all_residents.assign(**{k: all_residents["CUSEC"].map(sections[f"{k}_rate"]) for k in RATE_COLS}),
}
V = SPEC["vulnerability"]
SVPF = {v: pd.Series(bcr.social_vulnerability(
            d, sensitivity_cols=V["sensitivity"]["columns"], sensitivity_weights=V["sensitivity"]["weights"],
            coping_cols=V["coping"]["columns"], coping_weights=V["coping"]["weights"], svi_weights=V["svi_weights"],
            threshold=V["threshold"], exponent=V["exponent"])["SVPF"].to_numpy(), index=d["ID"])
        for v, d in VARIANT_DATA.items()}
residents = all_residents[all_residents["in_domain"]].reset_index(drop=True)
VARIANTS = {v: residents.assign(SVPF=SVPF[v].reindex(residents["ID"]).to_numpy()) for v in VARIANT_DATA}
hz_res = hz[hz["ID"].isin(residents["ID"])].set_index(["land_cover", "climate", "rp", "ID"])


def assess_map(data: pd.DataFrame, lc: str, cl: str, rp: int) -> pd.DataFrame:
    """Risk = SVPF (city-wide ranking) x exposure x hazard of this map; classes by the authors' rule."""
    h = hz_res.loc[(lc, cl, rp)].reindex(data["ID"])
    out = pd.DataFrame({"ID": data["ID"].values, "R": data["R"].values, "R_G": data["R_G"].values,
                        "SVPF": data["SVPF"].values, "HWB": h["HWB"].to_numpy(), "HMA": h["HMA"].to_numpy()})
    for r, spec in SPEC["risks"].items():
        out[r] = bcr.risk(out["SVPF"], data[spec["exposure"]].to_numpy(float), out[spec["hazard"]])
        out[f"{r}_class_own"] = bcr.risk_class(out[r], bcr.iterated_means(out[r], SPEC["classes"]["iterations"]))
    return out.assign(land_cover=lc, climate=cl, rp=rp)


# %% [markdown]
# **Check against the replication.** Inside the domain, the present-climate Baseline
# (RP100) is the replication's own flood map with the replication's rule, so every
# building's hazards must equal those in the replication's published `risk_buildings.csv`.
# So must social vulnerability (ranked city-wide, as there). Classes may differ only because
# the residential buildings near the domain edge are left out of the class limits (the
# authors' rule is relative to the buildings classed).

# %%
published = pd.read_csv(REPLICATION / "results/risk_buildings.csv").set_index("ID")
mine = hz_res.loc[("Baseline", "present", 100)].reindex(residents["ID"])
theirs = published.reindex(residents["ID"])
assert np.allclose(mine["HWB"], theirs["HWB"], atol=1e-9) and np.allclose(mine["HMA"], theirs["HMA"], atol=1e-9)
assert np.allclose(VARIANTS["counts"]["SVPF"], theirs["SVPF"], rtol=1e-9)
print(f"hazards and social vulnerability of all {len(residents):,} residential buildings in the domain "
      "equal the replication's")
base_here = assess_map(VARIANTS["counts"], "Baseline", "present", 100).set_index("ID")
check = pd.DataFrame({r: [int((published[f"{r}_class"] >= HOT).sum()), int((base_here[f"{r}_class_own"] >= HOT).sum()),
                          int(((published[f"{r}_class"] >= HOT) & published.index.isin(base_here.index)).sum())]
                      for r in RISKS}, index=["replication (all residential buildings)", "here (inside the domain)",
                                              "replication hotspots inside the domain"])
check.to_csv(RESULTS / "check_replication_hotspots.csv")
print(check.to_string())

# %% [markdown]
# **Fixed limits.** For the 100-year storm with the paper's indicators (counts), the limits
# are the replication's published ones (its baseline over all residential buildings), so this
# study's baseline hotspots are the replication's. For other return periods and for the
# rates version, which the replication did not publish, the limits come from this study's
# present-climate Baseline inside the domain.

# %%
REPLICATION_LIMITS = {r: bcr.iterated_means(published[r], SPEC["classes"]["iterations"]) for r in RISKS}
print({r: [round(x, 4) for x in b] for r, b in REPLICATION_LIMITS.items()})

risk = []
for variant, data in VARIANTS.items():
    per_map = {(m.land_cover, m.climate, m.rp): assess_map(data, m.land_cover, m.climate, m.rp)
               for m in maps.itertuples()}
    for (lc, cl, rp), out in per_map.items():
        ref = per_map[("Baseline", "present", rp)]
        for r in RISKS:
            if variant == "counts" and rp == 100:
                breaks = REPLICATION_LIMITS[r]
            else:
                breaks = bcr.iterated_means(ref[r], SPEC["classes"]["iterations"])
            out[f"{r}_class_fixed"] = bcr.risk_class(out[r], breaks)
        risk.append(out.assign(variant=variant))
risk = pd.concat(risk, ignore_index=True)
keep = ["variant", "land_cover", "climate", "rp", "ID", "R", "R_G", "SVPF", "HWB", "HMA"] + \
       [f"{r}{s}" for r in RISKS for s in ("", "_class_own", "_class_fixed")]
risk[keep].to_parquet(RESULTS / "building_risk.parquet", index=False)
print(f"{len(risk):,} building × map × variant rows")

# %% [markdown]
# ## 3. Scenario summary
#
# Per indicator version, risk, map: buildings and residents in the high classes (with the
# fixed and the own limits), buildings with any risk, total risk, and how many buildings'
# hazard differs from the present-climate Baseline of the same return period.

# %%
def summarise(g: pd.DataFrame, r: str) -> dict:
    exposure = "R_G" if r == "PFRWB" else "R"
    return {"buildings_hot_fixed": int((g[f"{r}_class_fixed"] >= HOT).sum()),
            "residents_hot_fixed": g.loc[g[f"{r}_class_fixed"] >= HOT, "R"].sum(),
            "buildings_hot_own": int((g[f"{r}_class_own"] >= HOT).sum()),
            "residents_hot_own": g.loc[g[f"{r}_class_own"] >= HOT, "R"].sum(),
            "buildings_at_risk": int((g[r] > 0).sum()),
            "residents_at_risk": g.loc[g[r] > 0, "R"].sum(),
            "exposed_at_risk": g.loc[g[r] > 0, exposure].sum(),
            "risk_total": g[r].sum()}


base = risk[(risk["land_cover"] == "Baseline") & (risk["climate"] == "present")].set_index(["variant", "rp", "ID"])
rows = []
for (variant, lc, cl, rp), g in risk.groupby(["variant", "land_cover", "climate", "rp"], sort=False):
    b = base.loc[(variant, rp)].reindex(g["ID"])
    for r in RISKS:
        hazard = SPEC["risks"][r]["hazard"]
        changed = ~np.isclose(g[hazard].to_numpy(), b[hazard].to_numpy(), atol=1e-9)
        rows.append({"variant": variant, "land_cover": lc, "climate": cl, "rp": rp, "risk": r,
                     **summarise(g, r), "buildings_hazard_changed": int(changed.sum()),
                     "residents_hazard_changed": g.loc[changed, "R"].sum()})
summary = pd.DataFrame(rows)
summary.to_csv(RESULTS / "scenario_summary.csv", index=False)
show = summary[(summary["rp"] == 100) & (summary["variant"] == "counts")]
print(show.drop(columns=["variant", "rp"]).round(1).to_string(index=False))

# %% [markdown]
# ## 4. Where each building goes: class transitions
#
# For every map, the class of each building under the present-climate Baseline of the same
# return period against its class in the scenario, both with the fixed limits; counted in
# buildings and in residents.

# %%
trans = []
for (variant, lc, cl, rp), g in risk.groupby(["variant", "land_cover", "climate", "rp"], sort=False):
    b = base.loc[(variant, rp)].reindex(g["ID"])
    for r in RISKS:
        t = pd.DataFrame({"from_class": b[f"{r}_class_fixed"].to_numpy(),
                          "to_class": g[f"{r}_class_fixed"].to_numpy(), "R": g["R"].to_numpy()})
        t = t.groupby(["from_class", "to_class"]).agg(buildings=("R", "size"), residents=("R", "sum")).reset_index()
        trans.append(t.assign(variant=variant, land_cover=lc, climate=cl, rp=rp, risk=r))
trans = pd.concat(trans, ignore_index=True)
trans.to_csv(RESULTS / "class_transitions.csv", index=False)

hot_base = trans[trans["from_class"] >= HOT].groupby(["variant", "land_cover", "climate", "rp", "risk"])
fate = hot_base.apply(lambda t: pd.Series({
    "hot_buildings_baseline": t["buildings"].sum(),
    "stay_hot": t.loc[t["to_class"] >= HOT, "buildings"].sum(),
    "leave_hot": t.loc[t["to_class"] < HOT, "buildings"].sum(),
    "residents_leaving_hot": t.loc[t["to_class"] < HOT, "residents"].sum()}), include_groups=False).reset_index()
fate.to_csv(RESULTS / "hotspot_fate.csv", index=False)
print(fate[(fate["rp"] == 100) & (fate["variant"] == "counts")].to_string(index=False))

# %% [markdown]
# ## 5. Who is affected: social vulnerability of the residents at risk
#
# Vulnerability here is the **rates** version (census-section shares of children, elderly
# people living alone, unemployed, residents without higher education): it describes who
# the residents are, where the paper's counts per building mostly describe how many there
# are (§2 of the replication). It is the same in every scenario; only who is reached by
# the water changes. It was not validated against impact data (the replication could not).
#
# Residents are split into five groups of equal size by their building's vulnerability
# (Q1 least, Q5 most vulnerable). A building is at risk when its risk index is above zero.
#
# - **Residents at risk per group**, per land cover, climate and return period.
# - **Newly at risk vs already at risk.** Buildings at risk under a future climate but not
#   at present (same land cover, same return period) against those at risk in both: the
#   residents' mean vulnerability percentile in each, and permutation tests (buildings
#   shuffled between the two sets, 10,000 times, fixed seed), one-sided in each direction:
#   "more vulnerable" and "less vulnerable". Many comparisons are made (land covers ×
#   climates × return periods × risks), so an isolated small p-value is expected by chance;
#   only a direction that holds across return periods is read as a finding.
# - **Taken out of risk by greening all open space** (`Allgreen`) against those remaining
#   at risk, the same way.

# %%
RNG_VULN = np.random.default_rng(20261011)
vuln = risk[(risk["variant"] == "rates") & (risk["land_cover"] == "Baseline") & (risk["climate"] == "present")
            & (risk["rp"] == 100)].set_index("ID")["SVPF"]
order = vuln.sort_values().index
cum = residents.set_index("ID")["R"].reindex(order).cumsum()
percentile = (cum - 0.5 * residents.set_index("ID")["R"].reindex(order)) / cum.iloc[-1]
VULN_PCT = percentile.reindex(vuln.index)
VULN_GROUP = pd.Series(np.minimum((VULN_PCT * 5).astype(int) + 1, 5), index=vuln.index)
pd.DataFrame({"ID": vuln.index, "vulnerability_percentile": VULN_PCT.values,
              "vulnerability_group": VULN_GROUP.values}).to_csv(RESULTS / "vulnerability_by_building.csv", index=False)
print(residents.set_index("ID")["R"].groupby(VULN_GROUP).sum().round(0).rename("residents per group").to_string())


def weighted_mean_pct(ids: pd.Index, weights: pd.Series) -> float:
    w = weights.reindex(ids)
    return float((VULN_PCT.reindex(ids) * w).sum() / w.sum()) if w.sum() > 0 else np.nan


def compare_sets(a: pd.Index, b: pd.Index, weights: pd.Series, n: int = 10_000) -> dict:
    """Resident-weighted mean vulnerability percentile of set a vs set b, and a one-sided
    permutation p-values for 'a is more' and 'a is less vulnerable than b' (buildings shuffled)."""
    observed = weighted_mean_pct(a, weights) - weighted_mean_pct(b, weights)
    pooled = a.append(b)
    w = weights.reindex(pooled).to_numpy()
    wp = w * VULN_PCT.reindex(pooled).to_numpy()
    # every permutation at once: rows of a random assignment of buildings to set a
    in_a = np.argsort(RNG_VULN.random((n, len(pooled))), axis=1) < len(a)
    wa, wpa = in_a @ w, in_a @ wp
    null = wpa / wa - (wp.sum() - wpa) / (w.sum() - wa)
    return {"n_a": len(a), "n_b": len(b), "residents_a": float(weights.reindex(a).sum()),
            "residents_b": float(weights.reindex(b).sum()), "mean_pct_a": weighted_mean_pct(a, weights),
            "mean_pct_b": weighted_mean_pct(b, weights), "difference": observed,
            "p_a_more_vulnerable": float((1 + (null >= observed).sum()) / (1 + n)),
            "p_a_less_vulnerable": float((1 + (null <= observed).sum()) / (1 + n))}


rates = risk[risk["variant"] == "rates"]
weights = residents.set_index("ID")["R"]
group_rows, compare_rows = [], []
for (lc, cl, rp), g in rates.groupby(["land_cover", "climate", "rp"], sort=False):
    for r in RISKS:
        at_risk = g.loc[g[r] > 0, "ID"]
        by_group = weights.reindex(at_risk).groupby(VULN_GROUP.reindex(at_risk)).sum().reindex(range(1, 6), fill_value=0)
        group_rows.append({"land_cover": lc, "climate": cl, "rp": rp, "risk": r,
                           **{f"residents_at_risk_Q{q}": v for q, v in by_group.items()}})
for (lc, rp), g in rates.groupby(["land_cover", "rp"], sort=False):
    present = g[g["climate"] == "present"].set_index("ID")
    for cl in ("CC_Q50", "CC_Q90"):
        fut = g[g["climate"] == cl].set_index("ID")
        if fut.empty:
            continue
        for r in RISKS:
            new = fut.index[(fut[r] > 0) & ~(present[r].reindex(fut.index) > 0)]
            both = fut.index[(fut[r] > 0) & (present[r].reindex(fut.index) > 0)]
            if len(new) and len(both):
                compare_rows.append({"comparison": "newly at risk vs already at risk", "land_cover": lc,
                                     "climate": cl, "rp": rp, "risk": r, **compare_sets(new, both, weights)})
base_rates = rates[(rates["land_cover"] == "Baseline")].set_index(["climate", "rp", "ID"])
for (cl, rp), g in rates[rates["land_cover"] == "Allgreen"].groupby(["climate", "rp"], sort=False):
    ref = base_rates.loc[(cl, rp)]
    g = g.set_index("ID")
    for r in RISKS:
        was = ref.index[ref[r] > 0]
        out_ = was[~(g[r].reindex(was) > 0)]
        stay = was[g[r].reindex(was) > 0]
        if len(out_) and len(stay):
            compare_rows.append({"comparison": "taken out of risk by Allgreen vs remaining", "land_cover": "Allgreen",
                                 "climate": cl, "rp": rp, "risk": r, **compare_sets(out_, stay, weights)})
vuln_groups = pd.DataFrame(group_rows)
vuln_compare = pd.DataFrame(compare_rows)
vuln_groups.to_csv(RESULTS / "vulnerability_groups_at_risk.csv", index=False)
vuln_compare.to_csv(RESULTS / "vulnerability_comparisons.csv", index=False)
print(vuln_groups[(vuln_groups["rp"] == 100) & (vuln_groups["land_cover"].isin(["Baseline", "Allgreen"]))]
      .round(0).to_string(index=False))
print(vuln_compare[vuln_compare["rp"] == 100].round(3).to_string(index=False))

# %% [markdown]
# ## 6. Recorded impact places under each scenario
#
# The replication's measure, per scenario and return period: the flooded share
# (depth ≥ 30 cm) of the open ground (not building, not water) within 20 m of each place
# where recorded storms (2018–2024) caused flooding. Descriptive only.

# %%
water = city("water").geometry


def open_ground(areas: gpd.GeoSeries) -> gpd.GeoSeries:
    """Each area minus buildings and water (the replication's rule, 03_analysis §3)."""
    blocked = pd.concat([buildings.geometry, water], ignore_index=True)
    tree = shapely.STRtree(blocked.values)
    out = []
    for z in areas.values:
        hits = tree.query(z, predicate="intersects")
        out.append(z.difference(shapely.union_all(blocked.values[hits])) if len(hits) else z)
    return gpd.GeoSeries(out, crs=CRS)


reports = city("impact_places")
places = (reports.assign(wkb=reports.geometry.to_wkb())
          .groupby("wkb", sort=False).agg(place=("place", "first")).reset_index())
places = gpd.GeoDataFrame(places[["place"]], geometry=gpd.GeoSeries.from_wkb(places["wkb"].values), crs=CRS)
zones = open_ground(gpd.GeoSeries(places.geometry.buffer(20).values, crs=CRS))
places["zone_in_domain"] = zones.within(domain).values
print(f"{len(places)} places; zone outside the domain: {places.loc[~places['zone_in_domain'], 'place'].tolist()}")

imp = []
for m in maps.itertuples():
    gpkg = FLOODS / f"{scenario(m.land_cover, m.climate)}.gpkg"
    share = bcr.covered_fraction(zones, gpd.read_file(gpkg, layer=f"rp{m.rp}_30").geometry)
    imp.append(pd.DataFrame({"place": places["place"], "zone_in_domain": places["zone_in_domain"],
                             "flooded_share_20m": share,
                             "land_cover": m.land_cover, "climate": m.climate, "rp": m.rp}))
imp = pd.concat(imp, ignore_index=True)
imp.to_csv(RESULTS / "impact_places_scenarios.csv", index=False)
print(imp[imp["rp"] == 100].pivot_table(index="place", columns=["land_cover", "climate"],
                                         values="flooded_share_20m").round(3).to_string())

# %% [markdown]
# ## Provenance

# %%
provenance = {"building-climate-risk": version("building-climate-risk"), "python": platform.python_version(),
              "geopandas": gpd.__version__, "shapely": shapely.__version__, "spec": SPEC,
              "hotspot_classes": f">= {HOT}", "maps": len(maps)}
(RESULTS / "run_provenance.json").write_text(json.dumps(provenance, indent=2))
provenance
