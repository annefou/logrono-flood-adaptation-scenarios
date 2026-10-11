# Logroño flood-adaptation scenarios

> **Building-level pluvial flood risk in Logroño (Spain) under future rainfall and nature-based solution scenarios** — the shared analysis behind three FORRT nanopublication chains.
>
> Method: [Vogelbacher et al. (2026), NHESS](https://doi.org/10.5194/nhess-26-2765-2026), through [building-climate-risk v0.2.1](https://doi.org/10.5281/zenodo.23285504). City inputs: [Logroño replication v0.1.1](https://doi.org/10.5281/zenodo.23285198).

For every residential building in Logroño, risk = social vulnerability × exposure × flood hazard is computed under the [REACHOUT flood scenarios](https://doi.org/10.5281/zenodo.14035876) — present and future design rainfall, current green cover, the planned nature-based solutions and an all-green city — and the future rainfall is checked against the [Destination Earth Climate DT](https://doi.org/10.21957/79c6af3105).

![How building-level risk is computed](figures/method.png)

## The notebooks

1. **Data download** — the Logroño replication's release and its city inputs.
2. **Flood scenarios** — what REACHOUT's archive contains, the modelled domain, the flood extents.
3. **Building-level risk** — every scenario and return period; who is affected; recorded impact places.
4. **Rainfall change** — EURO-CORDEX and the Destination Earth Climate DT.
5. **Figures**.

## Findings

1. Heavier future design rainfall increases the number of residents living in buildings at pluvial flood risk.
2. REACHOUT's planned nature-based solutions reduce the number of residents at risk by less than 4 %, only for frequent storms.
3. Converting all open space to green mainly takes less socially vulnerable residents out of risk.

Each finding is published as its own FORRT nanopublication chain; see [`nanopubs/PUBLISHED.md`](nanopubs/PUBLISHED.md). These are model scenarios, not predictions — see the limitations in the notebooks and the chains.

## Reproduce

```bash
git clone https://github.com/annefou/logrono-flood-adaptation-scenarios.git
cd logrono-flood-adaptation-scenarios
pixi install
pixi run snakemake --cores 1
```

## Citation

Cite this analysis via [`CITATION.cff`](CITATION.cff) → DOI [10.5281/zenodo.23298912](https://doi.org/10.5281/zenodo.23298912), and the method paper [10.5194/nhess-26-2765-2026](https://doi.org/10.5194/nhess-26-2765-2026).

Climate DT: *this data is created based on data of the European Union, using the Destination Earth Platform, but has been modified by Anne Fouilloux.*
