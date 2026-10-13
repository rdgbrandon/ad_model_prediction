# K-S3: a tighter law allowance beyond the cap, confirmed on Kelmarsh 2021

Written before Kelmarsh 2021 was downloaded or opened. Motivation (seen on 2016-2020, so those
years are development): beyond the published cap the K-S1 allowance is 6-14x the real law error,
because it stays frozen at the size it reached at the knee, where the law is worst.

## Rule

Law: the capped law c_j(x) = min(ybar_j(a*) + q_j delta, ln cap_j) (caps 2050 kW, 15.0 rpm).

  K-S1  beta = 2 kappa min(delta, delta*)                          (reference, unchanged)
  K-S3  delta <= delta*:  beta = 2 kappa delta                      (identical to K-S1)
        delta >  delta*:  beta = min( 2 kappa delta* ,  q90_fleet(bin) )

q90_fleet(bin) is the split-conformal 90% upper quantile (ceil((n+1) 0.9)-th smallest) of the law
error ||y(n) - c(n)|| against each unit's own capped law, over all units of EARLIER years at the
same wind-speed bin; infinite (so K-S3 = K-S1) when fewer than 9 units have that bin. For year Y the
pool is every Kelmarsh unit of 2016..Y-1. Mondrian by bin (Vovk et al. 2005). No label of the scored
unit enters beta.

Certificate: S = max(D - b - beta_T, 0) with the anchor at the top training bin (three-term,
MULTI_DATASET_PROTOCOL.md), and the measured-anchor form S_c = max(||f(x) - c(x)|| - beta, 0).
Nine surrogate families, seed 0, fitted per unit on TRAIN records.

## Data

Development: Kelmarsh 2017-2020 (fleet pools from 2016 onward). Confirmation: Kelmarsh 2021,
downloaded after this file was written, run through the unchanged pipeline (fleet = 2016-2020).

## Expectations, judged on 2021

  H1  Zero bound failures where the premise held.
  H2  K-S3 premise coverage beyond the cap (11.5-14.5 m/s) >= 0.90.
  H3  Beyond the cap, median beta / ||zeta|| for K-S3 at most half that of K-S1, and median S/e
      (both forms) higher than K-S1's.
  H4  Below the cap K-S3 equals K-S1 (by construction; checked).
  Every outcome is reported.
