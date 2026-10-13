# Learned law allowances: neural network and Kolmogorov-Arnold network

Written 3 October 2026, before any learned allowance was fitted or scored, and
before Kelmarsh 2018 was downloaded or opened.

## Question

The law allowance beta decides whether the SASES bound holds. Every rule so far
is a formula: C (theory distance), P (paper Eq. 5), E1 (long-hop kappa'), E2
(E1 + quadratic curvature), S (spec sheet, solar), E3 (per-bin conformal quantile
over other units). Can a model trained on data - a multilayer perceptron (NN) or
a Kolmogorov-Arnold network (KAN) - give an allowance that covers the law
residual at least as reliably while being tighter, and so makes the certificate
more informative? On wind, can it also remove E3's abstentions in the rated region?

## The rule every allowance obeys (unchanged)

beta at a test bin may use only labels available at deployment: the scored unit's
own TRAIN and LAWCAL bins, and labelled residuals from OTHER units in the training
pool. Never the scored unit's test-bin labels.

## Two families

A. Calibration-only (negative control). For each unit, fit an NN and a KAN to its
   own 8 labelled bins (TRAIN + LAWCAL, output vs ln x), extrapolate to the test
   bin, and use the departure of that extrapolation from the certificate's LAWCAL
   line as a curvature allowance, exactly as E2 does with a quadratic:
       A-NN, A-KAN:  beta = max(E1, 2 x ||g(u_t) - c(u_t)||).
   Expectation: no material gain over E1 on wind. A regime change outside the
   calibration band leaves no trace in the calibration labels, so no model fitted
   to them can recover it, however flexible.

B. Fleet-trained with conformal calibration. Learn the scale of the law residual
   from other units, then calibrate it conformally:
       sigma(x) = exp(m(x)),  m fitted to ln ||zeta|| by squared loss,
       score    s = ||zeta|| / sigma(x)                      (normalised residual),
       beta(x)  = CV+ quantile at level 1 - alpha of sigma_k(x) s_i  over the
                  training points i, with K = 5 folds grouped by unit,
       Mondrian by band: scores come only from training bins in the same band as
                  the test bin (wind: A, gap 10.5-11.5, B; solar: A, gap, B).
   alpha = 0.10. Models m:
       F0    no model: sigma = delta (a fleet-fitted rate, beta = k x delta)
       F-lin ridge regression on the features
       F-GBT gradient-boosted trees (200 trees, depth 2, rate 0.05, subsample 0.8)
       F-NN  MLP 16x16, relu, L2 1e-2, L-BFGS
       F-KAN KAN [d, 4, 1], cubic B-splines on 5 intervals over [-2.5, 2.5] of the
             standardised input, SiLU base term, ridge and second-difference
             penalties, Adam, 3000 full-batch steps. Implemented in numpy
             (kan.py, gated by test_kan.py's finite-difference gradient check).
   Features, all computed from the unit's own TRAIN and LAWCAL labels plus the
   test input:
       wind:  delta, ln U_t, q_P, q_omega (LAWCAL slopes), ln P and ln omega at
              the ceiling bin, quadratic curvature of each output over the 8
              labelled bins, E1 kappa', RMS residual of the LAWCAL line fit.
       solar: delta, ln G_t, q, ln I at the ceiling, curvature, E1 kappa', RMS
              LAWCAL residual, sin and cos of the calendar month.
   Reference rules recomputed on the same pools: C, P, E1, E3.

## Pools and years

Development (results may change hyperparameters; any change is recorded below):
   wind:  train 2016 -> score 2017
   solar: train 2017 -> score 2018;  train 2017-2018 -> score 2019
Confirmation (no change after this point):
   wind:  train 2016-2017 -> score Kelmarsh 2018, a year not yet downloaded.
          The unchanged pipeline (build_wind, wind_audit via run_wind_year) builds
          its records and nine surrogates.
   solar: train 2017-2019 -> score 2022-2023, label-only premise coverage.
          These years were opened before (pv/report.txt prints coverage by year
          for the formula rules); no learned rule has been fitted to or scored on
          them. This is weaker than the wind confirmation and is reported as such.

## Reported for every rule

Premise coverage (share of test unit-bins with ||zeta|| <= beta) with 95%
Clopper-Pearson interval, coverage on committed bins and abstention share,
median beta / ||zeta|| (tightness), and with the stored raw defects: validity
(S <= e), median S/e and silent share (S <= 0.01).

## Predeclared expectations

  L1  Proposition 1: zero bound failures where the premise held, every rule.
  L2  A-NN and A-KAN do not raise wind below-rated coverage above 0.75 or rated
      coverage above 0.10 (they cannot see the kink).
  L3  Every fleet rule reaches coverage >= 0.90 within sampling error in both
      wind scenarios on 2018, with no abstention.
  L4  At least one feature-based fleet rule (F-lin, F-GBT, F-NN, F-KAN) is tighter
      than E3 and F0 (lower median beta/||zeta||, higher median S/e) at equal
      coverage. If none is, a learned model adds nothing over a quantile table.
  L5  F-NN and F-KAN do not beat F-GBT or F-lin by a margin larger than the
      differences among seeds; the tabular baselines must be in the comparison.

## Development log (filled in during development, before confirmation)

Recorded 3 October 2026 after the development run (learned/dev.json, dev.log) and
before Kelmarsh 2018 was built or opened. Gates passed: C/P/E1/E3 reproduce
wind/allowance.json (2017) and pv/premise.json (2018, 2019).

What development showed:
  - Wind: every fleet rule covers >= 0.88 in A and >= 0.97 in B. F0 (no model,
    pooled rate) removes E3's 24% abstention in B and is the most informative
    rule there (median S/e 0.78 vs E3 0.68). No feature model beats F0 in B.
  - L2 is FALSIFIED in development: A-NN covers wind at 1.000 / 1.000. Cause: its
    tanh units saturate beyond the calibration data, so it extrapolates a plateau,
    and wind does plateau. A-KAN covers 0.92 / 0.86 for the same reason, weaker.
    This is an inductive bias that happens to match the physics, not information
    learned from the data.
  - Solar 2017 -> 2018: feature models fail (F-lin 0.55, F-GBT 0.71) or explode
    (F-NN beta/zeta up to 1e5): 2017 covers only Aug-Dec, so January-July inputs
    are outside the training support. NN and KAN vary strongly with seed.

Changes made for confirmation (nothing else changes):
  1. Rule Z added, calibration-only, from a physical assumption rather than a fit:
     beyond the ceiling each output keeps rising but no faster than the fitted
     law, 0 <= y_j(u) - y_j,top <= q_j delta. Then |zeta_j| <= q_j delta and
         Z:  beta = ||q|| x delta.
     It is the principled form of what A-NN did by accident. It is valid exactly
     when its assumption holds: saturating systems (wind) yes; systems whose
     output rises faster than the law past the ceiling (solar below clipping) no.
     On development: wind 1.000 / 1.000, solar 2018 A 0.643, 2019 A 0.821.
  2. Learned scales are clipped to the range of the training targets,
     sigma in [min ||zeta||, max ||zeta||] over the training fold. Conformal
     validity holds for any fixed sigma, so this changes width, not the guarantee;
     it stops out-of-support inputs from producing absurd allowances.
  3. F-NN and F-KAN are reported as the geometric-mean ensemble of seeds 0-2
     (F-NN-ens, F-KAN-ens) alongside the single seeds, to separate model effect
     from seed effect (L5).

Expectations added for confirmation:
  Z1  Z covers >= 0.90 in both wind scenarios on 2018.
  Z2  Z covers < 0.90 on solar below clipping in 2022-2023 (its assumption fails).
  L2  is replaced by: A-NN covers wind 2018 at >= 0.90 in both scenarios (the
      saturation bias persists); A-KAN does not exceed A-NN.
