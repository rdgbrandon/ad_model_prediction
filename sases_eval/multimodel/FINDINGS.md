# Nine surrogates, seven target representations: the score is the problem

`multimodel_audit.py` re-runs the ceiling certificate and the multi-subset
consensus bound across nine regression families (seeds 0-2 for the stochastic
ones, 19 fits in all) and seven window-level target representations, on the
unchanged `canonical_146` and `canonical_192` splits. 931 rows. The certificate
code is imported from `ceiling_audit.py` and `consensus_audit.py`, not rewritten,
and the reproduction gate in `test_multimodel_audit.py` confirms that the harness
reproduces every stored ceiling and consensus number on `ctr12` to 1e-8
(`linear`, `mlp8`, `mlp16x16`, 49 rows).

## What is stable across all of it

* **The premise held in all 931 rows.** The true trial-mean target stayed inside
  the calibration-centred growth ball for every model, seed, representation and
  test trial, at a median 36% of the radius to spare.
* **Validity is still non-discriminating.** `S <= e` in 931/931 rows, as before,
  because `e` exceeds `S` by a wide absolute margin whatever the model does.
* **The certificate goes quiet exactly where the surrogate is good.** 133 rows
  score `S <= 1`, and they concentrate on `mlp16x16` and `mlp32x32` fits with
  mean error 4-10. This reproduces the setup-C behaviour on every representation.
* **The multi-rule gain reproduces, and stays small.** Mean `S/e` rises by
  +0.008 to +0.025 depending on representation (`ctr12` linear: 0.742 -> 0.781,
  matching the stored consensus audit exactly). The weighted blend still
  contributes nothing anywhere: at most 3.6e-3 distance units over all 931 rows.
  `canonical_146` gains 0.000 in every representation and every model — with
  three calibration trials there is exactly one admissible subset, so that zero
  is still a definition, not a measurement.

## What the sweep newly exposes

**`S/e` rewards bad models.** The best-looking scores in the entire sweep belong
to `poly3`, at 0.94-0.97 — a cubic in `ln P` whose extrapolation error is 195 to
302, against 5-20 for every other family. The reason is visible in the absolute
slack: within one representation, `e - S` is nearly constant across models
(2.4-3.9 for `ctr12`, against a mean ball radius of 5.2), so the ratio is
mostly a statement about the denominator. Across the 19 fits, Spearman
`rho(S/e, e)` is +0.63 to +0.93: the worse the surrogate, the better its
certificate looks. Rank models by `e - S` at matched `e`, never by `S/e`.

**The gain from combining rules is smaller than the seed noise.** The mean
consensus gain in `S/e` is 0.017; the mean standard deviation of `S/e` across
three seeds of the same stochastic family is 0.082, reaching 0.32. `mlp16x16` on
`ctr12` spans 0.08 to 0.68 across seeds alone. A +0.02 effect measured against
that spread is not separable from which random initialisation the surrogate drew.

**Representation matters far less than model choice.** Pooled `S/e` moves over
0.66-0.79 across the seven representations, against 0.16-0.97 across the nine
model families. Band count (8, 12 or 24), band spacing, window length, median-
versus mean-averaged Welch segments and even switching the observable from the
centre pixel to the piston series all leave the qualitative picture unchanged.

**One representation strains the growth reference.** `ctrshape` (band mean
removed, spectral shape only) leaves the least slack in the premise: margin/radius
falls to 0.089 at worst, against 0.31-0.35 for the others. Its band slopes run
-2.3 to +3.3, so `kappa = ||q - 0.5||` is no longer a budget around a physical
flux exponent — the 0.5 reference is a property of the level, and this
representation has had the level removed. Its numbers are reported but should not
be read as a fifth-and-sixth vote for the amplitude representations.

## What none of it shows

The seven representations are seven views of the same series from the same 21
trials on one apparatus. They are robustness checks against preprocessing
choices, not replications. There are **four distinct test trials** in the whole
sweep (`_57_1`, `_60_1`, `_63_1`, `_66_1`); coverage of 1.000 is one fact about
those four trials, observed 233 times. Nothing here moves the sample size, and
no population coverage claim follows.

Representations built from `wave`, `field` or the stored spatial spectra were
excluded in advance, and should stay excluded: this package stores those with a
per-trial time decimation `D` (32 at 12 mW, 4 at 350 mW) and spatial cut `K` that
both vary with drive power, so a power law fitted to them would be partly a law
about the compression budget.

Reproduce with `python sases_eval/build_datasets.py` then
`python sases_eval/multimodel_audit.py`; the protocol fixed before the run is
`MULTIMODEL_PROTOCOL.md`, hashed into `results.json`. Tables:
`report_multimodel.py` (`report.txt`) and `analyse_multimodel.py`
(`diagnostics.txt`).
