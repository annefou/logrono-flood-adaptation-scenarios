# DISCOVERY — handoff for the Logroño flood-adaptation scenarios

Written 2026-10-10 at the end of the session that produced the Logroño replication
(github.com/annefou/logrono-pluvial-flood-replication). Everything below was checked in
that session; treat it as a starting point and re-verify anything before it goes into a
nanopub draft (`docs/verify-before-drafting.md`).

**First:** this repository is still uninitialised (`.template-uninitialised` is present).
Run `/init-template` before anything else. The chain here is **question-rooted (PICO)** —
there is no single upstream paper being replicated — see `docs/chain-decision-tree.md`.

## What this repository is for

Building-level pluvial flood risk in Logroño (Spain) under **future rainfall** and with the
city's **planned nature-based solutions (NBS)**, using the same open framework and data as the
replication. Candidate PICO question (refine with Anne in Phase 1):

> *In Logroño, do the planned nature-based solutions reduce the number of residents in high
> pluvial-flood-risk buildings under present and future 100-year rainfall, compared with no
> measures?*

It also asks how much heavier the **storms that actually flooded Logroño (2018–2024)** would be
in a +2 °C climate, using the Destination Earth Climate DT storylines.

## Prior nanopublications — connect to them

This work builds on two published FORRT chains on the same paper and two coverage nanopubs.
Use the template's own mechanism so the new chain is linked to them, not just mentioned:

1. **During `/init-template`**, when asked whether this work extends a prior FORRT chain, give
   the **Logroño CiTO** URI below. It is stored in `CITATION.cff` `references:`.
2. **Then run `/import-from-nanopub https://w3id.org/sciencelive/np/RAoFYugT7OVk5eoHuxKCO9HeqA08jMfSn7TeUxwZcbezE`**
   (entry point B, `docs/nanopub-chain-discovery.md`). It writes
   `nanopubs/imported/CHAIN_SUMMARY.md` (gitignored, regenerable) with each chain's scope,
   method, deviations, verdict and limitations — through the Logroño CiTO's `extends` it also
   reaches the Hamburg chain.
3. **In Phase 5**, the new CiTO should cite the Logroño Outcome (e.g. `usesConclusionsFrom` or
   `extends` — the scenarios build on its validated hazard component and its caveats), the
   paper with a method relation (`usesMethodIn`; this chain does not re-test the paper's claim),
   and its data (`usesDataFrom` REACHOUT; Climate DT). Check the relation list with the
   `vocabulary` tool (`cito_relation`).

**Logroño replication** (2026-10-10; verdict *partially supported*, CiTO *qualifies* the paper and
*extends* the Hamburg chain; repository = release v0.1.1, 10.5281/zenodo.23285198):

```
01 quote    https://w3id.org/sciencelive/np/RAbgREdIegl6pbTP_E4E2Eg9JR28whinZDteeGueXg1Wc
02 aida     https://w3id.org/sciencelive/np/RAPjP2vEln1AzhH3QpkUK6lRB99xicwcRkdUp35bxk9U4
03 claim    https://w3id.org/sciencelive/np/RAQDtKtTjDH3tbUuBwmzk2mWYe7vyMKHMI1cquwB-Pltk
04 study    https://w3id.org/sciencelive/np/RABBJpiR9zQUaRlSclmmv5wvIJr8wWl_hyo-NBK2o10pI
05 outcome  https://w3id.org/sciencelive/np/RAzO2FoYqdwvPCDDkfVmf-SKOl2mUpsf_qZeje0i_LP_U
06 citation https://w3id.org/sciencelive/np/RAoFYugT7OVk5eoHuxKCO9HeqA08jMfSn7TeUxwZcbezE
```

**Hamburg reproduction** (2026-10-09; *validated*, CiTO *confirms*; release v0.1.1,
10.5281/zenodo.23270558): Outcome https://w3id.org/sciencelive/np/RA6V_jAy2OFjYBwQMOH92fIM6199bjez7hRkY90vkxx7U,
CiTO https://w3id.org/sciencelive/np/RAI00BYTAPLTsNoY19DGNKF04vAjTuVv6K3WbYmo055CA
(all URIs: `nanopubs/PUBLISHED.md` in annefou/hamburg-pluvial-flood-replication).

**Geographic coverage** ("Document geographical coverage" template):
- Logroño, La Rioja, Spain — https://w3id.org/sciencelive/np/RAzds1z9t2ac7XFvx_Hsv18__p5nUTNA0NHIsskSyLVPQ
  (cites the replication's v0.1.0 release). This repository's own study area is the same
  municipality: publish a new coverage nanopub citing **this** repository's release once it has
  one (same WKT, `nanopubs/geo/logrono.wkt` in the replication repo), rather than reusing it.
- Hamburg, Germany (the paper's area) — https://w3id.org/sciencelive/np/RA1NTaGnBgz1AFkx-Xbpl8FLq16t6wINM-XyP4PrsXnK8
  (an earlier bounding-box version, RAXrw7VY…, is superseded and disapproved by the author).

## Decisions already taken with Anne

1. **Separate repository** from the replication: different claim and chain (question-rooted),
   the replication stays frozen at its release, and DestinE generation-2 data need credentials
   (the replication is fully open, no credentials).
2. **Method library: `building-climate-risk` v0.2.1**, pinned by tag in `pixi.toml`:
   ```toml
   [pypi-dependencies]
   building-climate-risk = { git = "https://github.com/annefou/building-climate-risk", tag = "v0.2.1" }
   ```
   v0.2.1 (10.5281/zenodo.23285504; concept 10.5281/zenodo.23282970) splits city-wide
   polygons automatically before overlays (~55× faster, results unchanged), so the manual
   100 m tiling in the replication's `03_analysis.py` is no longer needed. Its tests check
   every index against the authors' ArcGIS output (social vulnerability exact; hazard and
   risk to the third/fourth decimal; classes 37/37). Hazard-agnostic core; heat is planned
   as a later module.
3. **The authors' class rule** (iterated means) is kept as in the replication — but see
   method point 1 below: for comparing scenarios the breaks must be fixed from the baseline.
4. **HEALPix (healpix-geo, WGS84 ellipsoid, NESTED) is an add-on product only**: aggregate
   risk, flooded share and impacts to cells (level ~17, ~50 m), written as GRID4EARTH / EOPF
   Zarr, plus a per-cell impact comparison as a sensitivity check. Not used for the risk
   computation itself (it would resample flood depths).
5. **Everything recorded as code** (Anne's requirement): no result may depend on scratchpad
   exploration; every rule found while exploring goes into a notebook before it is relied on.
6. **Commits**: with the Claude co-author trailer; work step by step; no subagents.

## Reuse from the replication (don't copy — depend)

- **Inputs**: the replication's release **v0.1.1** (10.5281/zenodo.23285198; concept
  10.5281/zenodo.23284600). Download it and run its `01_data_download` + `02_data_clean`, or
  call its Snakefile up to `data/interim/logrono.gpkg`: 6,315 Cadastre buildings with
  residents (census sections shared by dwellings), census proxies, block-gap streets, Urban
  Atlas water, the 13 recorded impact places (`data/impacts/`, press reports, verbatim quotes)
  and the Cadastre street register. Re-run, don't copy files.
- **Replication result** (FORRT chain published 2026-10-10, `nanopubs/PUBLISHED.md` there):
  *partially supported*. The open 2 m flood map places recorded impacts at the 84th percentile
  of 512 streets (p ≤ 0.0001); street scale beats census sections (84th vs 69th, p = 0.010);
  building-level risk indices agree only weakly; social vulnerability is not testable with
  impact records. Outcome: https://w3id.org/sciencelive/np/RAzO2FoYqdwvPCDDkfVmf-SKOl2mUpsf_qZeje0i_LP_U
- **Finding to carry over**: with the paper's count-based indicators the social-vulnerability
  index follows building size almost exactly (Spearman 0.962 with residents; 0.059 with census
  rates), so building size enters risk twice. Rates leave the risk ranking unchanged but change
  the hotspots (5 → 21 well-being, 10 → 28 mobility). Report scenario results for both.
- **Climate DT extraction**: `annefou/extreme-precipitation-climatedt-replication` (Polytope
  polygon feature on HEALPix level 10, `avg_tprate`, `stream=clte`, IFS-NEMO SSP3-7.0,
  1991–2010 vs 2030–2049, return levels by duration). Consider moving it into a shared library.
- **Geometry script**: the replication's `scripts/geo_coverage_wkt.py` (OSM boundary → WKT that
  fits the coverage template's 1,500-character cap). Logroño's coverage nanopub already exists:
  https://w3id.org/sciencelive/np/RAzds1z9t2ac7XFvx_Hsv18__p5nUTNA0NHIsskSyLVPQ

## Data — verified sources

### REACHOUT scenarios (in `PluvialFloodMap_Logrono.zip`, Zenodo 10.5281/zenodo.14035876, CC BY 4.0)
Embedded metadata (SaferRAIN, 15-min uniform rain, Green-Ampt, no storage tanks), RP100:

| Folder | Rain (RP100) | Infiltration layer |
|---|---|---|
| `Baseline` | 26.77 mm | `32632_Logrono_PERM_sr` |
| `Baseline_CC_Q50` / `_Q90` | 31.25 mm (+17 %) / 38.99 mm (+46 %) | same |
| `NBSplanned` | 26.77 mm | `NBSPlanned_PERM_sr` |
| `NBSplanned_plus` | 26.77 mm | `NBSPlanned_PERM_sr` (**metadata identical to NBSplanned** — find the difference in REACHOUT documentation before interpreting) |
| `Allgreen` | 26.77 mm | `32632_Logrono_PERM_sr_NBStest` |
| `*_CC_Q50` / `*_CC_Q90` | 31.25 / 38.99 mm | per scenario |

- The archive is 254 MB (12.5 GB unzipped): extract only the rasters needed. MD5
  `324f1558766b10b613815b9e15d37a58`.
- **Grids differ**: Baseline and Allgreen 8230 × 9604; the CC and NBS rasters 5696 × 8002 —
  compare on the common footprint only.
- **CRS**: EPSG:32632 (UTM zone 32, ~11° from Logroño; the model really ran there). Don't
  resample depths: polygonise thresholds on the native grid, reproject the polygons to
  EPSG:25830 (as the replication's `02_data_clean.py` does). Remove water bodies (Urban Atlas
  class 50000): the rain-on-grid model fills the Ebro's bed.
- **Defect**: `Allgreen_CC_Q90/D_RP25_Q90.tif` is 0 bytes in the archive (worth reporting to
  Staccione & Pal, with the CRS labelling).

### Destination Earth (checked 2026-10-10)
- **Climate DT storylines** (released 18 May 2026): continuous simulations "from 2017 to the
  present", IFS-FESOM ~10 km, large-scale circulation nudged to ERA5 above the boundary layer,
  in three climates — 1950s-like, present, +2 °C (~2050s); five members per scenario. All four
  Logroño storms (2018-09-17, 2021-09-01, 2023-06-21, 2024-10-16) fall inside. Precedents:
  Valencia DANA 2024 (egusphere-2025-5929), Central European floods 2024. Output frequency for
  the storylines is not stated — check on the platform. Sources: GMD 19, 2821, 2026;
  https://destine.ecmwf.int/news/new-destine-climate-digital-twin-simulations-available/
- **Climate DT generation-2 projections**: 1990–2049, ~5 km, hourly, ICON + IFS-FESOM +
  IFS-NEMO, HEALPix; DOI 10.21957/79c6af3105. Cross-check of REACHOUT's EURO-CORDEX uplift.
  Request keys: follow `DOMAIN.md` § Destination Earth Climate DT and the polytope-examples repo.
- **Impact-sector indicators** (extreme precipitation, hydrology): announced 18 May 2026 for
  "the coming months" — release not confirmed; check the platform.
- **Not usable here**: Extremes DT on-demand 500–750 m runs (forecasts for selected events);
  the "Precipitation-to-Flood Signals" pilot (Italy only, river flooding); the "Disaster Risk
  Mitigation & Climate Adaptation" use case (Deltares; coastal/compound). Its open tools SFINCS
  (fast flood model incl. pluvial) and Delft-FIAT (building damage) are candidates for an
  alternative hazard model and an economic-damage complement.
- Access: DestinE generation 2 needs *upgraded access* (Anne has it). Put Polytope credentials
  in CI secrets; the workflows' `if:` must test `env.`, not `secrets.` (see `ci.yml`).

## Method points that must be handled

1. **Fix the class breaks from the baseline.** The authors' iterated-mean classes are relative
   to each map's own distribution; recomputing them per scenario can hide a uniform increase.
   Compare absolute risk, or classes with the baseline's breaks.
2. **Scenarios, not predictions** — conditional on design storms.
3. **15 min vs hourly**: Climate DT gives hourly at best; use relative changes (deltas), never
   absolute grid-cell values, and state the sub-hourly scaling assumption.
4. **Storylines at ~10 km** cannot place a convective cell on a street: compare regional event
   maxima (e.g. heaviest 1–3 h around Logroño) as ratios between climates; map the scaled storm
   to the REACHOUT return period with the matching rainfall (an approximation — say so).
5. **Return levels from 20-year windows**: RP2–RP25 are robust, RP100 is a long extrapolation.
6. **People fixed at 2021** unless INE population projections are added.
7. **No sewer network** in SaferRAIN; NBS only as an infiltration change.

## Lessons from the replication session (save time)

- **CI**: cache the immutable REACHOUT archive (`actions/cache`, key on its MD5); retry every
  API call and file download (Zenodo answered 504 / non-JSON transiently). Each push cancels the
  running Jupyter Book build — pause pushes for ~25 min when the book must deploy.
- **Dockerfile**: the template's pixi base image has **no git**, so a git-pinned
  `building-climate-risk` fails the Docker build. Add before `pixi install`:
  `RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*`
- **Overpass/Nominatim** are flaky: fetch OSM features once with a fixed query and commit the
  response (ODbL); record the query in the file.
- **Cadastre**: zoning labels carry a trailing space (`'MANZANA '`); building floors only in
  `buildingpart` (max per `<localId>_partN`); the Addresses GML uses the
  `urn:x-inspire:specification:gmlas:Addresses:3.0` namespaces.
- **Release**: bump `version:` in `CITATION.cff` and `codemeta.json` before tagging (the release
  workflow only sets the RO-Crate version); Zenodo must be enabled for the repo first.
- **Chain draft**: never hand-written; `pixi run build-chain-draft`, then `validate_chain_draft`
  until `readyForWizard: true`; the AIDA's "Supported by datasets" must be **bullet lines** or the
  builder drops it. Give the wizard a commit-pinned **jsDelivr** URL
  (`https://cdn.jsdelivr.net/gh/annefou/<repo>@<commit>/nanopubs/chain-draft.json`) — raw GitHub
  links are cached, and `github.com/.../blob/...` pages are not accepted.
- **Geographic coverage**: paste a WKT (the form's location search stores a bounding box);
  the coverage template caps WKT at 1,500 characters. A repo's own study area can be published by
  citing the repo's Zenodo version DOI and quoting its description.
- **verify_chain**: released forrt-research-mcp 0.1.2 can judge a *neighbouring* chain's verdict
  when the CiTO `extends` another chain; PR #12 (ScienceLiveHub/forrt-research-mcp) fixes it.
  The production `/np/constellation` returned HTTP 500 on 2026-10-10; the dev API worked.

## Credits to carry over

Framework: Vogelbacher, von Szombathely, Lennartz, Poschlod, Sillmann (2026, NHESS,
10.5194/nhess-26-2765-2026). Flood maps: Andrea Staccione, Jeremy S. Pal (REACHOUT). Buildings,
parcels, addresses: Dirección General del Catastro. Census: INE. Urban Atlas: EEA / Copernicus
Land Monitoring Service. Climate DT: ECMWF, the Climate DT consortium (led by CSC), Destination
Earth. Replication and building-climate-risk: Anne Fouilloux.
