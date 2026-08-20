# TC-WPN Phase 6B -> next experiment (pre-registration)

run under investigation : tcwpn_full_k5_seed42
frozen test AUROC       : 0.7379  (2,278 patients, threshold 0.26931)
amended verdict         : NO_SINGLE_ROOT_CAUSE
selected intervention   : MAX_CHUNKS

WHY THIS ONE
  Part D: 188 currently-misclassified patients (24.5% of all errors) have anxiety terminology only beyond the 512-token window.

THE ONE CHANGE
  Change ONLY max_chunks 1 -> 4 in tokenize_cohort.py. Same cohort, same patient
  split, same labels, same five seeds, same K, same architecture, same training
  settings. NOTE: the pkl changes, so the store fingerprint changes and the
  episode plans MUST be rebuilt -- which means the frozen baseline has to be
  re-scored on the new plans for the paired test to remain valid.

WHAT STAYS FROZEN
  cohort, patient splits, labels, seeds 42-46, K=5, evaluation plans (unless the
  pipeline itself changes, in which case the baseline is re-scored too),
  architecture, optimiser, learning rate, dropout, threshold selection procedure.

METRIC AND COMPARATOR
  Primary   : patient-level AUROC on the frozen episode plans.
  Comparator: tcwpn_full 0.7377 +/- 0.0031 ; aux_only 0.7371 +/- 0.0081.
  Secondary : PR-AUC, sensitivity, specificity, Brier, ECE, and the anxiety-blinded
              arm -- an improvement that vanishes under blinding is lexical, and the
              blinding gap is already 0.7379 -> 0.6284.

DECISION RULE (fixed now)
  Seeds     : 42, 43, 44, 45, 46. Selection on VALIDATION only; test scored ONCE.
  Success   : paired mean delta AUROC >= +0.020 AND paired p < 0.05 AND >= 4/5 seeds improved.
  Failure   : anything else. A delta below the 0.0199 baseline seed spread is noise.
  Either way, the result is reported.

NOT ALLOWED
  - more than one change at a time
  - re-selecting the threshold on test
  - dropping a disagreeing seed
  - reporting the best of several attempted interventions
  - using anx_coded_this_adm to rebalance training data (it is label-derived)
  - chasing the proposal's 0.80
