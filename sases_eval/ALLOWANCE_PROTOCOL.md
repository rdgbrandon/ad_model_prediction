# Expanding the law allowance from data, without reading the test labels

On the wind replication the allowance failed: the growth radius was 4.4x (below
rated) and 11.6x (rated) smaller than the law residual it had to cover, and the
paper's own Eq. 5 rule covered 45% and 1% of rows. This audit tries three
data-driven expansions of beta.

## Disclosure, before anything else

This protocol is written AFTER the 2016 failure and after seeing label-level
residuals on 2016 - which is how the failure was diagnosed as curvature of the
power curve and rotor-speed saturation near 9 m/s. Anything designed with that
knowledge and scored on 2016 is exploratory. The rules below are therefore
fixed now and CONFIRMED on Kelmarsh 2017, a year not opened before this protocol
was written. Only the 2017 results test the rules; the 2016 results show what
they were designed against.

## The one rule every expansion obeys

beta at a test point may use only labels available at deployment: the unit's
own TRAIN and LAWCAL bins, and - for E3 only - labelled data from OTHER units.
No rule may read the scored unit's own test-bin labels.

## Three expansions, from least to most outside data

  E1  Long-hop kappa' (calibration labels only). The paper's rule fitted kappa'
      on hops shorter than those it is used at. E1 uses all 8 labelled bins
      (TRAIN + LAWCAL): every window of 4 consecutive bins is treated as a
      pseudo-LAWCAL, its line fitted, and every labelled bin above it predicted.
      Ten holdout ratios ||zeta|| / delta, with delta up to ~0.55, covering the
      test range. kappa' = their maximum; beta = 2 x kappa' x delta, the paper's
      declared factor.

  E2  E1 plus extrapolated curvature (calibration labels only). Fit
      y = a + b u + c u^2 to each output over the 8 labelled bins; the departure
      of that quadratic from the certificate's LAWCAL line at the test point,
      Delta(t), is the curvature the line will miss. beta = max(E1, 2 x Delta(t)).

  E3  Fleet-calibrated (other units' labels). The law residual at a given
      wind-speed bin is exchangeable across turbine-months, so beta can be a
      split-conformal upper quantile of that residual over other units:
      beta(t) = the ceil((n+1)(1-alpha))-th smallest ||zeta|| at bin t among the
      calibration units, alpha = 0.10, infinite when n < 9. This gives the
      premise a real probabilistic guarantee - coverage >= 90% over exchangeable
      units - which the declared beta never had. The price is labelled data from
      the extrapolation range, gathered on other units.
        2016 (development): calibration units share neither turbine nor month
             with the scored unit.
        2017 (confirmation): calibration units are all 2016 units - learn the
             allowance from last year's fleet, deploy it this year.

Reference rows, recomputed on the same rows: C, the ceiling theory-distance rule
of the primary run; P, the paper's Eq. 5 rule of WIND_ADDENDUM.md.

## Unchanged

Surrogates, bins, bands, filters and the certificate centre are those of
WIND_PROTOCOL.md; the only differences in 2017 are the year and that all 12
months enter (the farm was in commercial operation throughout). For every rule,
S = max(D - beta, 0) on the stored raw defect D.

## Predeclared expectations, to be judged on 2017

  A1  Zero bound failures on rows where the premise held, under every rule.
  A2  E1 and E2 raise coverage below rated over P, but do not reach 90%:
      calibration-band data contain no trace of the rotor-speed limit.
  A3  Neither E1 nor E2 covers the rated region (scenario B): a plateau cannot
      be extrapolated from below it.
  A4  E3 reaches row-level premise coverage of at least 0.90 in both scenarios,
      within binomial sampling error, and validity at least as high.
  A5  The price of E3 is informativeness: its median S/e is lower than P's,
      and much lower in scenario B.

Every rule is reported with coverage, validity, validity where the premise held,
median S/e and silent rate, at row and unit level, for both years.
