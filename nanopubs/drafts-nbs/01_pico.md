# 01 — PICO Research Question (question-rooted chains, comparative)

> Use this draft instead of `01_quote.md` if your chain is question-rooted with a clear comparator (X vs Y). For descriptive/scoping question-rooted chains, use `01_pcc.md`. See `docs/chain-decision-tree.md`.
>
> Run the pre-flight checklist in `docs/forrt-form-fields.md` § Pre-flight checklist before drafting.
>
> **After choosing the chain shape, delete the two step-1 alternates you aren't using.** Once you've decided this chain is question-rooted-comparative and keep `01_pico.md`, run:
> ```bash
> rm nanopubs/drafts/01_quote.md nanopubs/drafts/01_pcc.md
> ```

**Form heading:** *"PICO Research Question — Define a research question using the PICO framework (Population, Intervention, Comparator, Outcome)"*

## Field-by-field draft

<!-- field: pico -->
### Short ID used as URI suffix (text input, required)

Slug becomes part of the nanopub URI. Use kebab-case.

```
logrono-planned-nbs-flood-risk
```

<!-- field: label -->
### Label for the research question (text input, required)

10-200 characters. Length-bounded.

```
Do Logroño's planned nature-based solutions reduce building-level pluvial flood risk?
```

<!-- field: description -->
### Description of the research question (textarea, required)

One coherent sentence/paragraph that names P, I, C, O inline.

```
In Logroño (Spain), compared with the current green cover, do the nature-based solutions planned by the city (bioswales, ponds, rain gardens and a green corridor) reduce building-level pluvial flood hazard and the number of residents in buildings at risk, under present and future design rainfall?
```

<!-- field: type -->
### Question Type (dropdown, required)

- [ ] causation research question - (Does factor X cause outcome Y?)
- [ ] descriptive research question - (What are the characteristics of X?)
- [x] effectiveness research question - (Does approach X work better than Y?)
- [ ] experience research question - (How do people experience phenomenon X?)
- [ ] prediction research question - (What outcomes can we expect from X?)

<!-- field: populationDescription -->
### Description of the population (textarea, required)

Who/what is being studied. Discipline-level concept — not implementation. See `docs/pico-study-outcome-levels.md`.

```
Residential buildings and their residents in Logroño (La Rioja, Spain), a mid-sized city exposed to pluvial flooding from short, intense rainstorms.
```

<!-- field: interventionGroupDescription -->
### Description of the intervention group (textarea, required)

The intervention or exposure being examined. Discipline-level concept.

```
The nature-based solutions planned for the city through a co-design process: bioswales and ponds, a green corridor, and additional small ponds and rain gardens.
```

<!-- field: comparatorGroupDescription -->
### Description of the comparator group (textarea, required)

The comparison or control condition. Discipline-level concept.

```
The city's current green cover, under the same design rainfall.
```

<!-- field: outcomeGroupDescription -->
### Description of the outcome group (textarea, required)

What outcomes are being measured. The kind of measurement, not the value.

```
Building-level pluvial flood hazard around each residential building, and building-level pluvial flood risk: the number of residents in buildings at risk.
```

## Publication note

After publishing, paste the resulting URI into `nanopubs/PUBLISHED.md` step 01.
