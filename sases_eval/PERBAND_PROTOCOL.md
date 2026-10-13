# Per-output law allowance: the same three-term certificate, applied per output

Written before any per-output certificate was computed. Motivation: on the
capillary corpus the law residual is concentrated in the bands above ~4 kHz
(law_bound/fig_capillary.png, panel d), yet one scalar allowance is charged
against all 12 bands. Nothing below is tuned to data: every per-output rule is
the existing rule with the norm moved inside, and the factor 2 is kept.

## The certificate stays a sum of three things

Current (sphere):   S = max(D - b - beta, 0),     D = ||y_hat - c||, premise ||zeta|| <= beta
Per output j:       S_j = max(D_j - b_j - beta_j, 0),   D_j = |y_hat_j - c_j|
Combined:           S = || (S_1, ..., S_m) ||_2

Premise: |zeta_j| <= beta_j for every j. Then |e_j| >= D_j - |zeta_j| >= S_j for
each j, so e = ||e_vec|| >= ||S_vec|| = S. The sphere certificate is the special
case of one shared allowance. In the ceiling form used throughout these audits the
centre is built from measured LAWCAL labels, so b = 0 (b_j = 0); the three-term
form is kept so the anchor form drops in unchanged.

## Rules, sphere and per-output

  C    beta = ||q - q_th|| delta            beta_j = |q_j - q_th,j| delta
  P    beta = 2 max_h ||zeta_h||/d_h delta    beta_j = 2 max_h |zeta_h,j|/d_h delta   (short hops in LAWCAL)
  E1   as P over long hops across TRAIN+LAWCAL (wind only; capillary has a regime
       break between TRAIN and LAWCAL, solar is one output)
  E3   sphere: split-conformal 90% quantile of ||zeta|| at the bin over the fleet
       per-output: JOINT split-conformal. Fleet units alternate (by sorted name)
       into a scale half and a score half; sigma_j = median |zeta_j| over the scale
       half at that bin; score = max_j |zeta_j| / sigma_j over the score half;
       beta_j = q_hat sigma_j, q_hat the 90% conformal quantile (infinite, i.e.
       abstain, when fewer than 9 scores). Joint coverage target 0.90, the same
       as the sphere rule's.

## Data

Capillary: 7 target representations x 19 surrogate fits x 2 ceilings (146, 192 mW),
the multimodel sweep, refitted and gated against multimodel/rows.csv (S and e to 1e-8).
Wind: Kelmarsh 2016, 2017, 2018 = DEVELOPMENT (all previously inspected). Kelmarsh
2019 = CONFIRMATION, not opened before this protocol; built with the unchanged
build_wind/wind_audit code. E3 fleets: 2016 other-turbine-other-month units; 2017
from 2016; 2018 from 2016-17; 2019 from 2016-18. Wind surrogate predictions are
refitted with wind_audit's own loop and gated against the stored raw defect.
Solar: one output, so per-output = sphere identically; reported as a check only.

## Reported, every rule and dataset

Premise coverage, validity (S <= e), failures where the premise held (Proposition 1
says 0), median S/e, silent rate (S <= 0.01), and paired against the sphere rule:
share of rows where per-output S > sphere S and the median ratio.

## Expectations

  H1  Zero failures where the per-output premise held, every rule and dataset.
  H2  Capillary: per-output S/e above sphere S/e for C and P, with validity no lower.
  H3  Wind: per-output premise coverage within 5 points of the sphere rule's for
      P, E1, E3, with higher median S/e.
  H4  Wind 2019: per-output E3 joint coverage >= 0.90 below rated and rated.
  Every outcome is reported, including those against these expectations.
