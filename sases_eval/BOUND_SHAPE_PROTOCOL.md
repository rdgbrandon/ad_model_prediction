# Shape of the law allowance: offset + slope, and a law with a spec-sheet break

Written before any of these allowances was computed. The certificate is unchanged:
S = max(D - b - beta, 0) with one allowance for all outputs (sphere; the per-output
variant was rejected, perband/FINDINGS.md). b = 0 in the ceiling form. Only beta, and
for rule K the law's centre, change.

## Calibration hops

Per unit, the existing hop sets: wind and solar use the long hops over TRAIN + LAWCAL
(rule E1's); capillary uses the short hops within LAWCAL (rule P's), because a regime
break separates its TRAIN and LAWCAL. Each hop gives a distance d_h and a law residual
z_h = ||zeta_h||.

## Rules

  L    linear (reference): beta = 2 kappa delta, kappa = max_h z_h / d_h
       (= E1 for wind/solar, = P for capillary; numbers as before)
  A    offset + slope: beta = r0 + 2 kappa_A delta
       r0 = max over LAWCAL bins of the ceiling line's own residual (the error already
       present at the calibration boundary); kappa_A = max_h (z_h - r0)_+ / d_h.
       Factor 2 on the rate as in L. Calibration labels only.
  K-L  law with a spec-sheet break, linear allowance: centre_j = min(ceiling line_j, cap_j)
  K-A  same centre, offset + slope allowance
       Wind caps: ln(2050 kW) rated power (Kelmarsh_WT_static.csv), ln(15.0 rpm) maximum
       rotor speed (Senvion MM92 published specification). Solar: current stops rising
       at G_clip = 823 W/m2 (PV_PROTOCOL.md, inverter rating); centre uses min(ln G, ln G_clip).
       Capillary has no spec-sheet break above the ceiling: L and A only, plus C (the
       theory-distance rule behind the headline numbers) for reference.

## Data

Capillary: 7 representations x 19 fits x 2 ceilings (refitted, gated as before).
Wind: 2016-18 development (all previously inspected); 2019 confirmation (opened only
for the per-output test, whose rules did not involve breaks or offsets).
Solar: all years previously inspected - exploratory only. Premise coverage label-only
on all 813 units; certificate on the 2018-19 scored rows, surrogate predictions
recovered from the stored D and e (sign fixed by consistency, asserted).

## Expectations

  H1  Zero bound failures where the premise held, every rule.
  H2  A covers at least as often as L on capillary and solar (an offset dominates there).
  H3  Wind 2019: K-L or K-A reaches premise coverage >= 0.90 in both scenarios, where
      L stays below 0.75 (the breaks are where wind failed).
  H4  Solar above clipping: K rules keep coverage >= 0.90.
  H5  Where coverage is comparable, report the median S/e cost or gain of each rule.
  Every outcome is reported, including those against these expectations.
