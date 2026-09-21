# Combining calibration-only rules: a modest, model-dependent gain

The previous audit scored a prediction against one region built from the whole
law-calibration set. This one builds a region from **every subset of at least
three** calibration trials, then reports the strongest resulting lower bound.
Weights for a blended region are chosen from the prediction, centres and radii
only. No test label enters a region or its selection.

## What improved

Mean fraction of measured error lower-bounded (`S/e`), canonical 192 mW:

| Model / run | One rule | Several rules | Change |
|---|---:|---:|---:|
| Straight-line | 0.742 | **0.781** | +3.9 pts |
| Larger NN, run 1 | 0.110 | **0.154** | +4.4 pts |
| Larger NN, run 0 | 0.080 | **0.113** | +3.3 pts |
| Larger NN, run 2 | 0.680 | 0.684 | +0.4 pts |
| Small NN, runs 0-2 | 0.806 | 0.806 | +0.0 pts |

All 78 audited rows keep `S <= e`. Target-ball coverage is 3/3 and 4/4 on the
canonical splits (nominal one-sided 95% CP lower bounds 0.368 and 0.473).

## Three limits on reading that as progress

**The comparison cannot come out negative.** The full calibration set is itself
one of the candidate subsets, so taking the strongest candidate is bounded below
by the previous score. `test_consensus_audit.py` asserts this. A zero change is
the floor of the comparison, not an experimental failure.

**The weighted blend contributes essentially nothing.** Across all 78 rows the
blended region beat the best single region by at most 8.2e-4 distance units,
against measured errors near 13. Nearly all the gain comes from one subset,
`{51, 54, 57} mW` — the one that drops the lowest calibration power, which fits
a slope closer to the 1/2 reference and so earns a smaller radius. The
weighted-ball construction in `consensus_audit.py` is sound but is not what
produced the improvement; subset selection is.

**One configuration could not improve at all.** `canonical_146` has three
calibration trials, hence exactly one subset of size >= 3. Its +0.0 pts is a
definition, not a measurement. Only `canonical_192` (four trials, five subsets)
and the sweep splits (5, 16 or 42 subsets) have any choice to make.

## The premise is strictly stronger

The single-rule bound needs one region to contain the true spectrum. This bound
needs **all** of them to, simultaneously — 5 regions on `canonical_192`, up to
42 on the widest sweep split. That premise did hold on every audited row, but
the thinnest margin falls to 0.20 distance units on the sweep, against 1.12 and
1.92 on the canonical splits. Tightening the bound tightens the assumption that
carries it.

The evidence base is unchanged: the same 3-4 distinct test trials, one
apparatus, a corpus already inspected. Extra models, seeds and overlapping
splits reuse those trials and add no independent validation. Nothing here
supports a population coverage claim.

Reproduce with `python sases_eval/consensus_audit.py`; the protocol fixed before
the run is `CONSENSUS_PROTOCOL.md`, hashed into `results.json`.
