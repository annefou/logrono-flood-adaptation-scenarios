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
        f"{RESULTS}/scenario_summary.csv",


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
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 02_data_clean.py"


# ---------- 03: Building-level risk under every scenario ----------
rule analysis:
    input:
        f"{RESULTS}/reachout_inventory.csv",
        f"{RESULTS}/hazard_cell_changes.csv",
    output:
        f"{RESULTS}/scenario_summary.csv",
        f"{RESULTS}/class_transitions.csv",
        f"{RESULTS}/hotspot_fate.csv",
        f"{RESULTS}/impact_places_scenarios.csv",
        f"{RESULTS}/building_risk.parquet",
    shell:
        f"cd {{NOTEBOOKS}} && jupytext --to notebook --execute 03_analysis.py"
