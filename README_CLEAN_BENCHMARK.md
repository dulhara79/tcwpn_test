# TC-WPN — publication-clean benchmark

Branch: `develop/publication-clean-benchmark`
Component: R26-DS-012 / TC-WPN
Author: Dulhara Kaushalya (IT22130648)

This tree replaces the archived pipeline. The archived code is not deleted; it
stays on `main` and is cited in `docs/AUDIT_OF_ARCHIVED_PIPELINE.md` as the
"before" condition of the benchmark-contamination analysis.

---

## The one-line statement of what changed

In the archived benchmark, a note's **label was partly a function of its
text**, and a patient could appear in the **support and query set of the same
episode**. Both are removed here, and both removals are enforced by tests that
run in CI rather than by a convention.

---

## Run order

Every step writes a JSON report next to its output. Do not proceed past a step
whose report contains a non-zero violation count.

### 0. Environment
```bash
git checkout develop/publication-clean-benchmark
pip install -r requirements.txt
export PYTHONPATH=src
```

### 1. Contract tests (before touching data)
```bash
pytest tests/ -q
```
Expected: all pass. `tests/test_episode_leakage.py` is the 5,000-episode
support/query disjointness proof at K = 1, 3, 5, 10.

### 2. Build the clean cohort
```bash
python scripts/build_clean_cohort.py \
    --task anxiety_vs_psych \
    --out-dir data/clean \
    --stem psych_mimic4 \
    --seed 20260805
```
`--task anxiety_vs_psych` is the **primary** experiment: anxiety versus other
psychiatric illness. Re-run with `--task anxiety_vs_nonpsych --stem nonpsych_mimic4`
to produce the **secondary** (easier) benchmark, which is what the archived
pipeline measured.

### 3. Audit the cohort
```bash
python scripts/audit_cohort.py --cohort data/clean/psych_mimic4_notes.csv
```
This is the table that goes in the paper's Data section. It must show
`Text-derived filtering: NO` on every row and `0` for all three split overlaps.

### 4. Robustness arms (identical patients, blinded text)
```bash
python scripts/blind_cohort.py --cohort data/clean/psych_mimic4_notes.csv \
    --level dx_meds --out data/clean/psych_mimic4_dxmeds_notes.csv
python scripts/blind_cohort.py --cohort data/clean/psych_mimic4_notes.csv \
    --level psych   --out data/clean/psych_mimic4_psych_notes.csv
```
The script refuses to write if the patient set, split assignment, or label
vector changed. That refusal is what makes the robustness comparison paired.

### 5. Tokenise
```bash
python scripts/tokenize_cohort.py --cohort data/clean/psych_mimic4_notes.csv \
    --out-dir data/clean/pkl --stem psych_mimic4
```

### 6. Freeze episode plans
```bash
for K in 1 3 5 10; do
  python scripts/make_episode_plans.py --pkl-dir data/clean/pkl \
      --stem psych_mimic4 --k $K --seed 42
done
```
Plans are frozen to disk **before** any model runs. Every model and every
ablation then sees the identical episodes, which is the precondition for the
paired DeLong test to be valid.

### 7. Shallow baselines first
```bash
python scripts/run_shallow_baselines.py --pkl-dir data/clean/pkl \
    --plan-dir data/clean/plans --stem psych_mimic4
```
**Stop here and read the numbers.** If TF-IDF is at or above the neural models,
that is the headline result and the paper changes shape. Do not run the full
grid before looking.

### 8. Train
```bash
for CFG in protonet tcwpn_full; do
  for K in 1 3 5 10; do
    python scripts/train.py --config configs/$CFG.yaml --k $K --seed 42 \
        --stem psych_mimic4
  done
done
```
One seed first. Expand to five seeds only after the K-sweep looks sane.

### 9. Ablations
```bash
for CFG in protonet protonet_temp temporal_only pcw_only temporal_pcw tcwpn_full; do
  python scripts/train.py --config configs/$CFG.yaml --k 5 --seed 42 --stem psych_mimic4
done
```

### 10. Evaluate and compare
```bash
python scripts/evaluate.py --stem psych_mimic4 --k 5 --split test
python scripts/compare_models.py --results results/psych_mimic4 --k 5
```
`compare_models.py` runs the paired DeLong test over patient-level score
vectors. Report the p-value it produces, whichever direction it points.

---

## Naming change you must carry into the paper

`confidence_weight` is renamed `prototype_consistency_weight` throughout.

The quantity is `w_i^C = exp(beta * cos(z_i, p~_c))` — the cosine similarity of
a support note to the preliminary prototype of its own class. That measures how
typical a note is of its class centroid. It is not a confidence in the label, it
is not calibrated, and it carries no uncertainty semantics. Calling it
"confidence" invites exactly one reviewer question, and there is no good answer
to it.

The architecture keeps the name TC-WPN for continuity with the registered
project. Define the C as *consistency* on first use and never use the word
"confidence" for this term again.

---

## What is deliberately absent

| Archived construct | Status |
|---|---|
| `has_psychiatric_content()` keyword gate | removed |
| `assign_anxiety_confidence()` | removed |
| `penalize_control_noise()` | removed |
| `label_confidence`, `training_weight`, `section_quality` | removed from every record |
| `curriculum_filter()` purity phases | removed |
| `*_high_conf` splits | removed |
| prescription- and OMR-derived labels | removed |
| MIMIC-III mixed into training | removed (MIMIC-III reserved for cross-dataset transfer) |

`tests/test_no_text_derived_filtering.py` fails the build if any of these
reappears in executable code.
