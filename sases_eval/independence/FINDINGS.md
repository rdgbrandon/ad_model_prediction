# The 399 rows are not 399 trials: what the comparison actually supports

The comparison slide quotes a 95% interval of [0.991, 1.000] for SASES, computed
as if its 399 rows were independent. They are not, and the interval is replaced
here by intervals at the sample size each claim really has. Protocol
`INDEPENDENCE_PROTOCOL.md`; 10,000 permutations per test.

## The rows are dependent, mostly by surrogate

Share of the variance of the margin `(e - score)/e` explained by each grouping:

| grouping | SASES | Calibration max | Raw defect | OLS |
|---|---:|---:|---:|---:|
| physical test trial | 0.028 | 0.022 | 0.032 | 0.032 |
| calibration split | 0.078 | 0.052 | 0.063 | 0.008 |
| representation | 0.066 | 0.024 | 0.147 | 0.123 |
| **surrogate fit** | **0.389** | **0.461** | **0.298** | **0.276** |
| case (repr, split, trial) | 0.210 | 0.134 | 0.332 | 0.212 |

Rows are **not exchangeable** across surrogate fits (permutation p = 0.0001 for
every method, the resolution limit) nor across test trials (p = 0.004 to 0.034).
The dominant dependence is which surrogate is being scored, not which experiment.

A Kish correction on test trial alone gives an effective size near 105 and is
**misleading**, because it ignores the larger surrogate effect. The crossed
estimate, `Var(mean) ~ s2_fit/19 + s2_trial/4 + s2_res/399`, gives an effective
size of **32 to 41** for an average over these rows.

## Two claims, two sample sizes

"The bound holds on a new experiment" and "the bound holds for a new surrogate"
are different claims, generalising over different units:

| | test trials | surrogate fits | surrogate families |
|---|---:|---:|---:|
| **SASES** | **4/4** [0.398, 1.000] | **19/19** [0.824, 1.000] | **9/9** [0.664, 1.000] |
| Calibration maximum | 0/4 [0.000, 0.602] | 12/19 [0.384, 0.837] | 5/9 [0.212, 0.863] |
| Raw defect | 0/4 [0.000, 0.602] | 11/19 [0.335, 0.797] | 3/9 [0.075, 0.701] |
| OLS error predictor | 0/4 [0.000, 0.602] | 7/19 [0.163, 0.616] | 3/9 [0.075, 0.701] |

A unit counts as held only if the method held on every row in it. Intervals are
two-sided 95% Clopper-Pearson.

**Replace [0.991, 1.000] with 4/4 trials, [0.398, 1.000].** That is the honest
interval for the claim the slide is making. The evidence across surrogates is
considerably stronger — 19 of 19 fits, [0.824, 1.000] — but it is evidence about
surrogates on these four experiments, not about new experiments.

## Paired tests against each baseline

The same trials and fits score every method, so the correct comparison is an
exact sign test on the units where two methods disagree. One-sided p:

| SASES vs | per trial (4) | per fit (19) | per family (9) |
|---|---:|---:|---:|
| Calibration maximum | 0.0625 | **0.0078** | 0.0625 |
| Raw defect | 0.0625 | **0.0039** | **0.0156** |
| OLS error predictor | 0.0625 | **0.0002** | **0.0156** |

**With four test trials no comparison can be significant.** SASES holds on all
four trials and every competitor fails on all four, yet the paired p is 0.0625
— the smallest value four units can produce. This is arithmetic, not a weak
result, and it is the single clearest statement of why a second dataset is
needed.

Across surrogates the advantage is significant. Against calibration maximum,
the strongest competitor, it is significant per fit (p = 0.008) but not per
family (p = 0.0625), because its failures are confined to four families.

## Competitors fail by surrogate type, not by experiment

| | linear | poly3 | knn5 | krr_rbf | rf200 | gbrt | mlp8 | mlp16x16 | mlp32x32 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SASES | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Calibration max | 0.00 | 0.00 | 0.00 | **1.00** | 0.00 | 0.00 | 0.19 | 0.14 | 0.02 |
| Raw defect | 0.24 | **1.00** | 0.00 | **1.00** | 0.00 | 0.00 | 0.11 | 0.11 | 0.60 |
| OLS | 0.33 | **1.00** | 0.00 | 0.52 | 0.00 | 0.00 | 0.21 | 0.38 | 0.63 |

Failure rates by family. Failures are spread evenly across test trials
(concentration p = 0.20 to 1.00) but sharply concentrated by family
(p = 0.0001). Calibration maximum fails on every `krr_rbf` row; the raw defect
and OLS fail on every `poly3` row. The baselines' failures are systematic
properties of particular surrogate types, which a practitioner choosing a
surrogate could not anticipate from calibration data.

## The summaries are not carried by any single trial

Dropping each test trial in turn moves SASES's median score/e within
0.669-0.727 and its rank correlation within 0.782-0.805. Calibration maximum's
rank correlation stays at 0.856-0.904 in every case — its ranking advantage
over SASES is robust, not an artefact of one trial.

## For the slide

> **Bound holds:** every row (399/399), every surrogate (19/19 fits,
> 95% CI [0.824, 1.000]) and every test experiment (4/4 trials,
> 95% CI [0.398, 1.000]). Against each baseline: significant across
> surrogates (paired p ≤ 0.008); not testable across experiments, where four
> trials cannot reach p < 0.0625.

Reproduce with `python sases_eval/independence_audit.py` then
`python sases_eval/report_independence.py`.
