# An allowance that stops growing once the law reaches its spec-sheet cap

Written before any of these allowances was computed, after the bound-shape audit
(bound_shape/FINDINGS.md) showed that with the break law K the rated-region allowance is
~30x the law residual. The idea was formed after seeing wind 2016-19, so those years are
DEVELOPMENT. Kelmarsh 2020 is the CONFIRMATION year, downloaded after this protocol was
written and run through the unchanged pipeline (build_wind, wind_audit's unit/bin rules,
the nine surrogates).

Certificate unchanged: S = max(D - b - beta, 0), one allowance for both outputs, b = 0.
Centre for every rule: the break law, centre_j = min(TM_top,j + q_j delta, ln cap_j),
caps ln(2050 kW) and ln(15.0 rpm) from the published ratings.

## Rules

  K-L   reference (bound-shape winner): beta = 2 kappa delta, kappa from rule E1's long hops
  K-S1  PRIMARY: beta = 2 kappa min(delta, delta*), delta* = max_j delta*_j, where
        delta*_j = (ln cap_j - TM_top,j) / q_j is the distance at which output j's fitted
        line reaches its cap (infinite if q_j <= 0). Once every output is capped, the law
        is a constant and its error should stop growing with distance; the allowance is
        frozen at its value where the LAST output caps.
  K-S2  SECONDARY, reported: the same with delta* = min_j delta*_j (frozen where the first
        output caps). Expected to under-cover; reported so that the choice of K-S1 is
        not made after looking at the confirmation year.
  L     straight law, straight allowance (rule E1), for scale.

## Expectations, judged on 2020

  H1  Zero bound failures where the premise held.
  H2  K-S1 premise coverage >= 0.90 below rated and in the rated region.
  H3  K-S1 median S/e in the rated region above K-L's, with validity >= 0.95.
  H4  K-S2 covers less than K-S1.
  Every outcome is reported, including those against these expectations.
