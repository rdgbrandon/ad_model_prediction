# Paper revisions supported by the rerun

These are replacements/additions for `ad_proposal_week_2.pdf`, not instructions
copied from the reviewer. The numerical supplement is generated separately from
the current run by `report_theory_audit.py`. The original PDFs are retained.

## Sections 2 and 3: narrow the novelty claim

Physics-based reliability signals do not universally require target labels.
Gopakumar et al.'s [Calibrated Physics-Informed Uncertainty Quantification](https://arxiv.org/html/2502.04406v2)
calibrates PDE residuals without labelled solutions, assuming a specified
governing operator and exchangeable PDE conditions. Its guarantee concerns
residual-space coverage; it should not be described indiscriminately as a bound
on solution error. Our narrower object is a per-input lower bound on surrogate
error, conditional on separate anchor-error and approximate-law allowances.

Wang et al.'s [A General Theory of Correct, Incorrect, and Extrinsic Equivariance](https://arxiv.org/html/2303.04745v2)
already derives regression approximation-error lower bounds from symmetry
mismatch and variation over group orbits. We do not claim the first connection
between symmetry and error lower bounds. Our construction instead attributes an
observed defect to one input using an anchor and an explicit law-residual
allowance; its algebraic step is a triangle inequality.

Standard split conformal prediction needs calibration/test exchangeability,
not necessarily similarity between training and deployment distributions.
[Uncertainty Quantification of Surrogate Models using Conformal Prediction](https://arxiv.org/abs/2408.09881)
reports OOD results while explicitly retaining calibration/test exchangeability.
Do not conflate training shift with calibration shift.

Additional relevant comparisons are [Berman et al.](https://arxiv.org/abs/2510.21691)
on calibration-error bounds under equivariance, [Xu et al.](https://arxiv.org/html/2605.01868v1)
on branched-flow transport for conditional conformal prediction, and
[Lust and Condurache's GIT](https://arxiv.org/abs/2307.02672) on transformation-based
classification error detection. These study calibration, transported prediction
sets, or detection rather than this conditional per-input regression lower bound.
The flow analogy is conceptual; it is not evidence that a physical anchor
automatically inherits their guarantees.

## Sections 5 and 6: sample size and reporting

The 348 Setup C configurations reuse only three distinct high-power test trials;
they are a sensitivity sweep, not 348 independent validation observations.
The alternative 146 mW ceiling adds the 192 mW trial, giving four distinct test
trials in that configuration. Seeds and windows add no independent trials.
Do not attach a binomial confidence bound to a pooled fraction over overlapping
splits and anchors. Instead report counts for a fixed configuration or define
one success event per trial (for example, success under every swept configuration).
The latter is a different, stricter estimand and must be labelled accordingly.

All rerun coverage tables pair trial counts with one-sided 95% Clopper-Pearson
lower bounds. These are nominal IID-binomial reference bounds, because the
corpus samples chosen powers from one apparatus rather than independent random
deployments. Even 3/3 gives only 0.368, and 4/4 only 0.473. Neither establishes
population coverage of 0.90. With zero failures, at least 29 independent trials
are needed for the corresponding lower bound to exceed 0.90.

## Section 6.6: retrospective factor of two

The historical factor of two was declared after inspecting the same corpus,
including a test-derived sufficient factor of 1.79. Calling it a round number
does not remove that dependence. Retain it only as a retrospective sensitivity
comparison. The new theory candidates are fitted using calibration arrays only,
but the study as a whole remains exploratory because its test corpus was
previously inspected. No new coefficient was optimized against the rerun audit.

## Section 7: theory-informed allowance and its limits

The capillary Zakharov-Filonenko spectrum has amplitude proportional to the
square root of energy flux and frequency dependence proportional to
frequency^(-17/6). See the [original capillary-wave paper](https://doi.org/10.1007/BF00915178)
and the explicit spectrum in [Kochurin and Russkikh](https://arxiv.org/html/2501.18970v2).
The proposal's reference [7] has the wrong title: it should be *Weak turbulence
of capillary waves*, not *Weak turbulence of a plasma in a magnetic field*.

Writing energy flux as proportional to drive power^gamma gives a log-PSD power
slope gamma/2 in each fixed band. We evaluate gamma=1 as an explicit assumption,
not as an experimentally established coupling law. The fitted slopes in this
code are power slopes, so comparing them to -17/6 would compare different
quantities.

Let u0 be the law-calibration ceiling, q_high the fitted slope vector and
r(u)=y_anchor-y(u)-c(u)-c0. Then r'(u)=q_high-y'(u). If
norm(y'(u)-q_high) <= k throughout the extrapolation interval, integration and
the triangle inequality give norm(r(u)) <= norm(r(u0)) + k*(u-u0).
The new candidate sets k=norm(q_high-0.5*ones) and uses the observed calibration
boundary norm(r(u0)). This is exact under an ideal constant KZ derivative and
conditional under a derivative envelope. Theory alone does not prove that
envelope for a driven, finite, dissipative experiment, especially across a
regime transition. Therefore label this a theory-informed empirical audit,
not a derived and verified universal physical bound.

## Section 7: anchor guarantee correction

Applying a split-conformal order statistic to leave-one-trial-out residuals
from different fitted models does not by itself give split-conformal coverage
for the final model at a selected boundary anchor. The existing LOTO b is
therefore retained as a heuristic comparator. A second variant uses the
measured final-model error at the already-labelled anchor. That quantity is
available without test labels and is exact for the empirical trial-mean target;
it does not bound an unknown noise-free target without measurement uncertainty.
Neither variant supports the proposal's unconditional statement that alpha
controls anchor-error coverage in this experimental design.

Also correct the sample-size arithmetic in Section 8: at alpha=0.10 the first
interior finite-sample quantile is n=19 (rank 18), not n=20. A finite quantile
first exists at n=9. These rank facts do not supply missing exchangeability.

## New reproducibility and artifact section

We provide portable spectrum construction, the archived pre-rerun arrays,
fixed candidate definitions, grouped split lists, all calibration fits,
per-case audit rows, environment versions, input/code SHA-256 hashes, and tests
for leakage and the conditional inequality. The spectrum arrays were rebuilt
from the supplied 50 MB HDF5 and checked against the archived arrays. Exact
commands and scope are in `README_RERUN.md`; measured outcomes are in
`rerun/results.md` and `rerun/results.json`.

The source corpus is Orosco, Connacher and Friend's
[UC San Diego deposit](https://doi.org/10.6075/J0WW7HVJ). This evaluation uses a
lossy repackaging, not a rerun of the original 320.7 GB reduction; the reduction
scripts are not distributed. The target is the mean of window-level natural
log band-averaged temporal PSDs, not log of a mean PSD. Welch parameters are
8192-sample windows, stride 4096, 2048-sample segments with half overlap, Hann
window and linear detrending; 12 logarithmic bands span 500 Hz to 20 kHz.
