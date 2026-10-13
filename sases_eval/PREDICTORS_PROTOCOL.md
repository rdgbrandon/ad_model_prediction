# Sixteen columns - fourteen error-predictors and two references - scored
# against the measured error

The certificate answers one question: how wrong is this surrogate at this input,
when the input lies outside the training band? It is not the only method that
claims to. This audit puts it beside every competitor that can be computed on
this corpus and scores them all the same way.

## What each method may use

TRAIN labels (12-54 mW) and LAWCAL labels (106 mW up to the configuration's
ceiling) are available to any method. The TEST trial's label is never available
to any method; it is read only afterwards, to score. Splits stay grouped by
trial.

## The methods, fixed before the run (fourteen, plus two reference columns)

Lower bounds on the error:
  sases_ceiling     S from the ceiling certificate (the incumbent)
  sases_consensus   S from the multi-subset consensus bound
Point signals from the law:
  defect_raw        ||g(x) - law centre||, before any allowance is subtracted
  law_gap_train     same, with the law fitted on TRAIN only; no LAWCAL labels
Disagreement:
  seed_ensemble     spread of five mlp16x16 refits at x (the existing competitor)
  family_ensemble   spread of the other surrogate fits at x, this fit excluded
  bootstrap_trials  spread of eight refits on trial-level bootstrap resamples
Residual and conformal, from TRAIN:
  loto_conformal    conformal quantile of leave-one-trial-out errors; constant in x
  loto_slope        LOTO error regressed on that fold's extrapolation distance,
                    evaluated at the test distance
  jackknife_plus    grouped jackknife+ radius from the same LOTO residuals
  insample_rmse     trial-level in-sample error; constant in x
Variance and geometry, no labels at x:
  gp_sigma          Gaussian-process posterior sd at x, scaled to the target norm
  blr_sigma         Bayesian ridge predictive sd, per band, normed
  leverage          in-sample error times sqrt(1 + h(x)) from the linear design
References:
  distance          |ln P_test - ln P_train_top| alone
  constant          1.0 for every row: the no-information null

## Scoring

Primary: Spearman correlation with the measured error, computed two ways, because
they ask different questions and only one of them is easy.
  within-trial  across surrogate fits at a fixed test trial - which model is worse
  within-model  across test trials for a fixed surrogate fit - which input is harder
Secondary, for the methods that claim a bound: the fraction of rows on the right
side of the measured error, and the mean absolute slack. Calibration ratio
median(predicted / measured) for the methods on the error's own scale.

A method that only tracks the extrapolation distance will do well within-trial
and badly within-model, or the reverse; reporting one number would hide that.
The `constant` null fixes the floor: any method that does not beat it on both is
not predicting accuracy, it is predicting the corpus.

## Scope and what does not follow

Three representations (`ctr12`, `ctrshape`, `pist12` - the canonical one, the one
with the level removed, and the one with a different observable), the 19 surrogate
fits of MULTIMODEL_PROTOCOL.md, both canonical configurations. Refit cost is the
reason for three rather than seven; representation-invariance was already
established in `multimodel/FINDINGS.md`.

There are still four distinct test trials. Within-model correlations therefore
rest on three or four points each and are reported with that stated, not as
evidence of anything about a population. Report every method, including the ones
that beat the certificate.
