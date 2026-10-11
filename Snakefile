# Snakefile — orchestrates the scenario pipeline end-to-end.
#
# Each rule wraps a notebook executed via jupytext (the notebook stays the source
# of truth and the Snakefile just sequences them).
#
# Usage:
#   snakemake --cores 1                  # run everything
#   snakemake --cores 1 -n               # dry run

NOTEBOOKS = "notebooks"
DATA = "data"
RESULTS = "results"
FIGURES = "figures"


rule all:
    input:
        f"{FIGURES}/main_result.png",
        f"{RESULTS}/cordex_match.csv",


# ---------- 01: Data download ----------
# Fetches the Logroño replication release (Zenodo) and runs its pipeline up to the
# city inputs; see CLAUDE.md § Self-contained data.
rule data_download:
    output:
        f"{DATA}/raw/sources.json",
    log:
        f"{RESULTS}/logs/01_data_download.log",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 01_data_download.py 2>&1 | tee ../{{log}}"


# ---------- 02: Scenario inventory and flood extents ----------
rule data_clean:
    input:
        f"{DATA}/raw/sources.json",
    output:
        f"{RESULTS}/reachout_inventory.csv",
        f"{RESULTS}/hazard_cell_changes.csv",
        # Not committed (unlike the tables): a fresh checkout must re-run 01-02
        # before 03, even though the committed results make the tables look done.
        f"{DATA}/interim/domain.gpkg",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 02_data_clean.py"


# ---------- 03: Building-level risk under every scenario ----------
rule analysis:
    input:
        f"{DATA}/raw/sources.json",
        f"{DATA}/interim/domain.gpkg",
        f"{RESULTS}/reachout_inventory.csv",
        f"{RESULTS}/hazard_cell_changes.csv",
    output:
        f"{RESULTS}/scenario_summary.csv",
        f"{RESULTS}/class_transitions.csv",
        f"{RESULTS}/hotspot_fate.csv",
        f"{RESULTS}/impact_places_scenarios.csv",
        f"{RESULTS}/building_risk.parquet",
        f"{RESULTS}/vulnerability_comparisons.csv",
        f"{RESULTS}/vulnerability_by_building.csv",
        f"{RESULTS}/impact_places_local_depth.csv",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 03_analysis.py"


# ---------- 04: Rainfall change (EURO-CORDEX, Climate DT) ----------
# The Climate DT sections read the monthly files written by scripts/retrieve.py
# (hours of requests, DestinE credentials). Their result tables
# (climatedt_projection_change.csv, storyline_*.csv) are committed and deliberately
# NOT declared as outputs: Snakemake deletes a rule's outputs before re-running it,
# and without the DestinE data (CI) the notebook falls back to those committed files.
rule climate:
    input:
        f"{RESULTS}/reachout_inventory.csv",
    output:
        f"{RESULTS}/cordex_match.csv",
        f"{RESULTS}/cordex_factors.csv",
        f"{RESULTS}/healpix_membership.csv",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 04_climate.py"


# ---------- 05: Figures ----------
rule figures:
    input:
        f"{DATA}/raw/sources.json",
        f"{RESULTS}/cordex_match.csv",
        f"{RESULTS}/scenario_summary.csv",
        f"{RESULTS}/vulnerability_by_building.csv",
        f"{RESULTS}/climatedt_projection_change.csv",
        f"{RESULTS}/storyline_change.csv",
    output:
        f"{FIGURES}/main_result.png",
        f"{FIGURES}/land_cover_rp100.png",
        f"{FIGURES}/rainfall_change.png",
        f"{FIGURES}/priority_map.png",
        f"{FIGURES}/method.png",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 05_figures.py"
