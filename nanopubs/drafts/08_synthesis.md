# 08 — Research Synthesis (optional)

> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> Use this template only when this chain is **one of several** testing facets of a shared underlying property. The Synthesis names the cross-cutting conclusion and lists the multiple Outcomes as supporting sources.

**Form heading:** *"Science Live Research Synthesis — Synthesise findings across multiple replication outcomes with conclusions, recommendations, conditions, and limitations."*

## Field-by-field draft

<!-- field: synthesis -->
### Short URI suffix for synthesis ID (text input, required)

Slug. Use kebab-case.

```
logrono-flood-adaptation-scenarios-synthesis
```

<!-- field: label -->
### Label (text input, required)

A one-line summary.

```
Logroño flood adaptation: future rainfall raises building-level flood risk; planned nature-based solutions offset little; untargeted greening favours the less vulnerable
```

<!-- field: conclusion -->
### Conclusion of the synthesis (textarea, required)

The aggregate finding across the underlying outcomes.

```
Three FORRT chains from one shared analysis of building-level pluvial flood risk in Logroño (Spain), under REACHOUT's flood scenarios, give one picture. (1) Heavier future design rainfall puts more residents in buildings at pluvial flood risk in every case examined (all return periods from 2 to 200 years, both EURO-CORDEX future scenarios, each risk index): +1.5 to +5.9 % under the median scenario and +5.0 to +9.5 % under the 90th percentile; today's 100-year storm becomes a 50- or 25-year storm. The Destination Earth Climate DT supports the median scenario's order of magnitude and places the 90th percentile at the high end. (2) REACHOUT's planned nature-based solutions offset only a small part of this: they reduce the number of residents at risk by less than 4 %, only for frequent storms, and not at all during the 100- and 200-year storms. (3) Converting all open space to green surfaces takes about 9 to 21 % of the residents at risk out of risk, but mainly the less socially vulnerable ones: in all 40 comparisons the residents taken out of risk are less vulnerable than those who remain, and the most vulnerable fifth benefits least. Together: climate change raises flood risk for Logroño's residents, the measures planned so far do little against it in this model, and greening placed without regard to vulnerability mainly protects those who need it least.
```

<!-- field: recommendation -->
### Recommendations (textarea, required)

Actionable guidance for practitioners.

```
Plan for today's 100-year flood risk arriving with a 25- to 50-year storm, and assess adaptation under both a median and a high-end rainfall scenario. Prioritise nature-based solutions where socially vulnerable residents are at risk — in Logroño, mainly the historic centre — rather than where open space happens to be available; city-wide greening alone mainly benefits the less vulnerable. Before relying on the planned measures, test them with a flood model that represents storage, overflow and the sewer network, and with the measures' actual layout: in a fill-and-spill model without sewers their effect is small, partly because of the model. Publish the layout of planned measures and the scenario data openly, so that their effect can be checked and compared.
```

<!-- field: conditions -->
### Conditions under which the synthesis applies (textarea, required)

Scope: data types, methods, domains, regions, time periods.

```
Logroño municipality (La Rioja, Spain), every residential building inside the area modelled by all REACHOUT scenarios (4,540 buildings with residents). Hazard: REACHOUT SaferRAIN pluvial flood maps (2 m, 15-minute design storms, return periods of 2 to 200 years) for the current green cover, REACHOUT's planned scenario with and without extra ponds, and all open space green; present rainfall from station data and future rainfall scaled by EURO-CORDEX changes (2041-2070, median and 90th percentile), checked against the Destination Earth Climate DT (IFS-NEMO SSP3-7.0 projections to 2049 and storylines of 2017-2024 at +2 °C). Risk: the Vogelbacher et al. (2026) framework (social vulnerability x exposure x hazard) through building-climate-risk v0.2.1, residents from the 2021 census, vulnerability from census-section indicators; classes with present-day limits. All three chains use the same analysis release (10.5281/zenodo.23298913).
```

<!-- field: limitations -->
### Limitations of the synthesis (textarea, required)

What was not tested? What might not generalise?

```
The three findings come from one analysis and one flood model; they are consistent with each other by construction and are not independent confirmations. SaferRAIN is a fill-and-spill model without sewers on 15-minute design storms; it represents nature-based solutions only as infiltration and terrain changes, which likely understates storage and drainage effects. The future rainfall is a scaling of observed design storms; REACHOUT's factors cannot be reproduced exactly from its EURO-CORDEX file and the Climate DT check is single-model and hourly. Social vulnerability comes from census-section rates and was not validated against impact data; residents are fixed at 2021; 1,851 residents near the edge of the modelled area are left out. The all-green scenario is a bound, not a plan, and REACHOUT's planned scenario may differ from what the city builds. Results are scenarios for one city and may not transfer to cities with other terrain, drainage or social geography.
```

<!-- field: date -->
### Completion date (text input, required)

```
2026-10-11
```

<!-- field: source -->
### Supporting sources (text input, required)

Each entry is a URL — typically the FORRT Outcome URIs being synthesised. Pull from `nanopubs/PUBLISHED.md` (and/or registries from sibling repos).

```
https://w3id.org/sciencelive/np/RA0Xdfwi2iNgVwH3KD4Bx5-pZ4JqKAt3-I4iyJSojbfCg
https://w3id.org/sciencelive/np/RAYfm7-Pxkf34WyNY81poZJ-_6z7kqROLOS_NUTGiXNTM
https://w3id.org/sciencelive/np/RA7f_o-KNPr1Rq2OPPJD47XcUYtPvIRF4rRDqFg-tsZgA
```

<!-- field: topic -->
### Topic (search/select, required)

Provide labels (not QIDs).

- flood risk (Q2288778)
- climate change adaptation (Q260607)
- nature-based solutions (Q2421934)
- social vulnerability (Q581445)

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 08.
