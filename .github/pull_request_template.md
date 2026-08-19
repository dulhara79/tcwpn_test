<!--
Title must follow Conventional Commits, e.g.
  feat(sampler): enforce patient-disjoint episode construction
  fix(eval): correct bootstrap CI for macro-F1
  exp(phase4): prototype cosine divergence diagnostic
-->

## What changed

<!-- One paragraph. What does this PR do and why. -->

## Type

- [ ] `feat` — new capability
- [ ] `fix` — bug fix
- [ ] `exp` — experiment / ablation run
- [ ] `refactor` — no behaviour change
- [ ] `docs` — documentation only
- [ ] `chore` / `ci` — tooling

## Research validity

<!-- Delete rows that do not apply. These exist because this pipeline has
     previously shipped label leakage and patient-overlap bugs. -->

- [ ] No new label leakage path introduced (support/query sets stay disjoint)
- [ ] Patient-level disjointness preserved in episode sampling
- [ ] Test-set filtering unchanged, or the change is justified below
- [ ] Seeds and config recorded for any reported number
- [ ] Leakage certificate regenerated if the cohort/sampler changed

## Monorepo impact

Merging this to `main` triggers `sync-to-monorepo`, which mirrors the tree into
`R26-DS-012:Anxiety_Detection_TC_WPN/research-pipeline` via `sync/tcwpn/main`.

- [ ] No restricted data added (`data/`, MIMIC-IV/NHSL extracts, `*.csv`, weights)
- [ ] Notebook outputs stripped (`nbstripout`)
- [ ] Mirror dry-run in CI reviewed — file count and size look right

## Checks

- [ ] `ruff check` and `black --check` pass locally
- [ ] `pytest` passes locally