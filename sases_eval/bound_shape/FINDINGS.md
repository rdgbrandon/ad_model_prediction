# Shape of the law allowance: a spec-sheet break works, offset + slope does not

Protocol: `BOUND_SHAPE_PROTOCOL.md`. Code: `bound_shape_audit.py`, figure `bound_shape_figures.py`.
Numbers: `bound_shape/report.txt`, `results.json`. Figure: `fig_bound_shape.png`.
The certificate is unchanged (one allowance for all outputs, S = max(D - b - beta, 0)).

## Wind 2019 (the confirmation year)

| rule | below rated: premise / valid / S/e | rated: premise / valid / S/e |
|---|---|---|
| L straight line (= E1) | 0.719 / 0.831 / 0.94 | 0.010 / 0.184 / 1.24 |
| A offset + slope | 0.486 / 0.647 / 0.98 | 0.000 / 0.170 / 1.36 |
| **K-L law with spec-sheet break** | **0.924 / 0.940 / 0.91** | **1.000 / 1.000 / 0.64** |
| K-A break + offset + slope | 0.792 / 0.841 / 0.95 | 0.997 / 0.997 / 0.75 |

Development years agree: K-L covers 0.85-0.96 below rated and 1.000 rated in 2016-18.
Caps are published ratings, not fits: 2,050 kW rated power (Kelmarsh_WT_static.csv),
15.0 rpm maximum rotor speed (Senvion MM92 specification).

## Verdicts

- H1 zero failures where the premise held: **holds**, every rule and system.
- H2 offset + slope covers at least as often as the straight line on capillary and
  solar: **falsified.** It covers less everywhere (capillary 146: 0.61 -> 0.18; solar
  below clipping 0.955 -> 0.826; wind 2019 below rated 0.72 -> 0.49). Removing the
  boundary residual from the hops shrinks the fitted rate, and the factor 2 then only
  doubles the excess; the boundary offset is not what was missing, the growth is.
- H3 wind 2019, a break rule reaches >= 0.90 in both scenarios: **holds** (K-L 0.924
  and 1.000, where L gave 0.719 and 0.010).
- H4 solar above clipping, break rules keep >= 0.90: **holds for K-L** (1.000) but at no
  gain: below clipping K-L is identical to L (823 W/m2 lies above the band), and above it
  the median S/e falls to 0.00-0.23. Current rises faster than the law before clipping,
  so capping it at 823 W/m2 moves the centre the wrong way.

## What it means

The law, not the allowance's formula, was the problem on wind: once the centre stops
at the turbine's published ratings, the ordinary straight-line allowance covers the
unseen year, and the certificate becomes valid in the rated region (median S/e 0.64,
where every calibration-only rule was invalid). Past the cap the allowance is now far
larger than the residual (median beta/||zeta|| ~ 30); an allowance that stops growing
at the cap would be much tighter, but that idea was formed after seeing these results
and needs a fresh year (Kelmarsh 2020 is on Zenodo).

Scope: one wind farm, one solar plant; capillary has no spec-sheet break above its
ceiling, so only L and A apply there. Solar and capillary are exploratory (all years seen).
