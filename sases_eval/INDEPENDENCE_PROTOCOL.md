# Are the scored rows independent, and what sample size do they really carry?

The comparison table reports a 95% Clopper-Pearson interval of [0.991, 1.000]
for SASES, computed as if its 399 rows were 399 independent trials. They are
not obviously so: they are four physical test trials, each scored under 19
surrogate fits, three target representations and up to two calibration splits.
This audit measures how dependent the rows are and recomputes every interval at
the sample size the dependence supports.

## Hold indicators, as on the slide

  SASES consensus      holds when score <= e   (lower bound)
  Calibration maximum  holds when score <= e   (lower reading, as on the slide)
  Raw defect           holds when score >= e   (upper reading, as on the slide)
  OLS error predictor  holds when score >= e   (upper reading, as on the slide)

Rows from `fair_baselines/results.json` (399, the equal-label comparison) and
the premise and validity indicators from `multimodel/results.json` (931).

## Dependence measurements

1. Variance share (eta squared) of the continuous margin (e - score)/e explained
   by each grouping: physical test trial, calibration split, representation,
   surrogate family, and the joint case (representation, split, trial).
2. ICC(1) of that margin within physical test trial, and the Kish design effect
   DEFF = 1 + (m - 1) ICC with the effective sample size N / DEFF.
3. Permutation test of exchangeability: shuffle the trial labels 10,000 times
   and compare the between-trial share of variance with the observed one.
4. For methods that fail somewhere, a permutation chi-square test of whether
   failures are spread across trials or concentrated in some of them.

The binary hold indicator has no variance for a method that never fails, so its
dependence is measured through the continuous margin that drives it. This is a
proxy and is reported as one.

## Intervals reported for every method

Two-sided 95% Clopper-Pearson at: rows as if independent (the slide's choice),
calibration-split cases, physical test trials, and the Kish effective size. At
trial level a trial counts as held only if the method held on every row in it.
Continuous summaries (median score/e, rank correlation) are also given a
leave-one-trial-out range, because a bootstrap over four clusters is too coarse
to mean much.

## What cannot follow

No grouping can manufacture more than four independent physical outcomes. If
the dependence analysis supports a larger effective size than four, that size
is a statement about the margin's variance structure, not about how many
experiments were run, and it is reported as such.
