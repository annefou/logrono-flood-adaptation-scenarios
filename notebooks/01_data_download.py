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
# # 01 — Data download
#
# The city inputs are not rebuilt here: they come from the Logroño replication
# (Fouilloux 2026, release **v0.1.1**, Zenodo
# [10.5281/zenodo.23285198](https://doi.org/10.5281/zenodo.23285198)), whose published
# FORRT chain validated the hazard component this study builds on. Its source archive is
# downloaded from Zenodo (checked against the MD5 Zenodo publishes) and **its own
# pipeline is run** up to `data/interim/logrono.gpkg`, in its own pinned environment
# (`pixi.lock` of that release). Files are not copied between repositories.
#
# | Component | Source (fetched by the replication's `01_data_download`) | Licence |
# |---|---|---|
# | Flood depths, all scenarios | REACHOUT pluvial flood maps for Logroño, Staccione and Pal (2024), Zenodo [10.5281/zenodo.14035876](https://doi.org/10.5281/zenodo.14035876) | CC BY 4.0 |
# | Buildings, urban blocks, addresses | Spanish Cadastre, INSPIRE, municipality 26900 | CC BY 4.0 |
# | Residents, vulnerability proxies | INE, Censo 2021, indicators per sección censal | INE terms (reuse with attribution) |
# | Water, roads | Copernicus Urban Atlas 2018 (ES018L2), EU-Hydro v1.3 | Copernicus (free, full and open) |
# | Recorded impacts | press reports, curated in the replication repository | see its `data/impacts/` |
#
# The replication's notebook extracts only the REACHOUT `Baseline` folder; the other
# scenarios are read from the same archive in `02_data_clean`.
#
# The Cadastre and INE regenerate their files over time, so a new run may fetch newer
# versions than the replication's release did. Their SHA-256 and `Last-Modified` dates are
# in the replication's source log, which is carried into `data/raw/sources.json` here.
#
# **Requirement:** `pixi` on the PATH (it is in the Docker image), to run the
# replication's pipeline in its own environment.

# %%
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import requests

# %%
RAW_DIR = Path("../data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

REPLICATION = {
    "name": "logrono-pluvial-flood-replication",
    "version": "v0.1.1",
    "doi": "10.5281/zenodo.23285198",
    "concept_doi": "10.5281/zenodo.23284600",
    "record": "23285198",
    "file": "annefou/logrono-pluvial-flood-replication-v0.1.1.zip",
    "license": "MIT (code); data under their own licences",
}
REPLICATION_DIR = RAW_DIR / "replication"
TARGET = "data/interim/logrono.gpkg"


def get(url: str, attempts: int = 5, **kw) -> requests.Response:
    """GET with retries: Zenodo answers 504 / non-JSON transiently."""
    for i in range(attempts):
        try:
            r = requests.get(url, timeout=600, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == attempts - 1:
                raise
            print(f"retry {i + 1} after: {e}")
            time.sleep(10 * (i + 1))


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# %% [markdown]
# ## 1. The replication's release archive

# %%
record = get(f"https://zenodo.org/api/records/{REPLICATION['record']}").json()
entry = next(f for f in record["files"] if f["key"] == REPLICATION["file"])
expected_md5 = entry["checksum"].removeprefix("md5:")
archive = RAW_DIR / Path(REPLICATION["file"]).name

if not archive.exists() or md5(archive) != expected_md5:
    with get(entry["links"]["self"], stream=True) as r, open(archive, "wb") as f:
        shutil.copyfileobj(r.raw, f)
assert md5(archive) == expected_md5, "replication archive does not match Zenodo's MD5"

if not (REPLICATION_DIR / "Snakefile").exists():
    with zipfile.ZipFile(archive) as z:
        top = {n.split("/")[0] for n in z.namelist()}
        assert len(top) == 1, top
        z.extractall(RAW_DIR)
    (RAW_DIR / top.pop()).rename(REPLICATION_DIR)
print(f"{archive.name}: MD5 {expected_md5} verified; extracted to {REPLICATION_DIR}")

# %% [markdown]
# ## 2. Run the replication's pipeline up to the city inputs
#
# Snakemake skips the rules whose outputs are up to date, so a re-run costs nothing.

# %%
env = {k: v for k, v in os.environ.items() if not k.startswith(("PIXI_", "CONDA_"))}
cmd = ["pixi", "run", "--manifest-path", "pixi.toml", "snakemake", "--cores", "1", TARGET]
print(" ".join(cmd))
subprocess.run(cmd, cwd=REPLICATION_DIR, env=env, check=True)
assert (REPLICATION_DIR / TARGET).exists()

# %% [markdown]
# ## Source log

# %%
replication_sources = json.loads((REPLICATION_DIR / "data/raw/sources.json").read_text())
log = {
    "accessed_on": datetime.date.today().isoformat(),
    "replication": {**REPLICATION, "md5": expected_md5, "path": str(REPLICATION_DIR),
                    "city_inputs": TARGET},
    "replication_sources": replication_sources,
}
(RAW_DIR / "sources.json").write_text(json.dumps(log, indent=2, ensure_ascii=False))
print(f"logged to {RAW_DIR / 'sources.json'}")
