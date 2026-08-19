# TC-WPN Phase 6 — pre-registration
run under investigation : tcwpn_full_k5_seed42
frozen test AUROC       : 0.7379   (2,278 patients, threshold 0.26931)
root-cause verdict      : EMBEDDING_AND_MODEL

HYPOTHESIS
  The weighting changes discrimination materially
  (AUROC weighted - uniform = +0.0009, error flip rate 6.24%),
  so prototype construction is where the errors are produced and a corrected
  weighting/support-composition should improve them.

THE ONE CHANGE
  Modify ONE of: support-set composition, the distance function, temperature
  initialisation, or consistency_passes. Everything else, including the data
  pipeline and the encoder, is untouched.

METRIC AND COMPARATOR
  Primary  : patient-level AUROC on the frozen episode plans.
  Comparator: the Phase 3B five-seed benchmark already in the repo —
              aux_only 0.7371 +/- 0.0081, tcwpn_full 0.7377 +/- 0.0031.
  Secondary : PR-AUC, sensitivity, specificity, Brier, ECE; and the anxiety-blinded
              arm, because an improvement that vanishes under blinding is lexical.

DECISION RULE (fixed now, not after the result)
  Seeds        : 42, 43, 44, 45, 46 — the same five, on the same frozen plans.
  Selection    : validation only. Test is scored ONCE, after the val decision.
  Success      : paired mean delta AUROC >= +0.020 vs the frozen baseline AND
                 paired DeLong / paired t p < 0.05 AND >= 4/5 seeds improved.
  Failure      : anything else. A delta below the 0.0199 seed-to-seed spread
                 of the baseline is noise and will be reported as no effect.
  Either way   : the result goes in the paper. A negative result here is publishable;
                 a positive result obtained by trying many changes is not.

WHAT IS EXPLICITLY NOT ALLOWED
  - changing more than one thing at a time
  - re-selecting the threshold on test
  - dropping a seed that disagrees
  - reporting the best of several attempted interventions
  - pursuing 0.80 because the proposal mentioned it
