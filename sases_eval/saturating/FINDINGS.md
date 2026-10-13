# Freezing the law allowance at the spec-sheet cap: confirmed on Kelmarsh 2020

Protocol: `SATURATING_PROTOCOL.md` (written before any of these allowances was computed).
Code: `saturating_audit.py`, figure `saturating_figures.py` -> `fig_saturating.png`.
Numbers: `saturating/report.txt`, `results.json`.

Certificate unchanged: S = max(D - b - beta, 0), one allowance for both outputs. Centre:
the law with the turbine's published caps (2,050 kW rated power, 15.0 rpm maximum rotor
speed). New allowance K-S1: beta = 2 kappa min(delta, delta*), frozen at the distance where
the last output's fitted line reaches its cap.

## Confirmation year 2020 (downloaded after the protocol; 72 turbine-months)

| rule | below rated: premise [95% CI] / valid / S/e | rated: premise [95% CI] / valid / S/e |
|---|---|---|
| L straight law and allowance | 0.674 [0.616, 0.727] / 0.803 / 0.96 | 0.028 [0.013, 0.051] / 0.200 / 1.25 |
| K-L break law, growing allowance | 0.941 [0.907, 0.965] / 0.954 / 0.92 | 1.000 [0.990, 1.000] / 1.000 / 0.65 |
| **K-S1 break law, frozen allowance** | **0.934 [0.899, 0.960] / 0.949 / 0.92** | **1.000 [0.990, 1.000] / 1.000 / 0.85** |
| K-S2 frozen at the first cap | 0.285 / 0.407 / 1.01 | 0.975 / 0.980 / 0.97 |

## Verdicts (judged on 2020)

- H1 zero failures where the premise held: **holds** (also in every development year).
- H2 K-S1 >= 0.90 in both scenarios: **holds** (0.934 and 1.000).
- H3 K-S1 rated-region S/e above K-L's with validity >= 0.95: **holds** (0.85 vs 0.65, validity 1.000).
- H4 K-S2 covers less than K-S1: **holds** (0.285 below rated).

In the rated region the certificate now proves a median 85% of the surrogate's error
with the premise held on every unit-bin; the straight law there was valid on 20% of rows.

## Limitation found in development: derating

2016 rated region: K-S1 covered 0.747. The turbines ran below rating in their first months
(median rated-bin power 1,762 kW in 2016 vs 2,038 kW in 2017; 21 of the 23 uncovered bins
are May and August 2016). The frozen allowance assumes the machine reaches its published
cap; under derating or curtailment the plateau sits lower and the premise fails. The
growing allowance K-L happened to cover 2016 because it is ~30x too large there. A
deployment needs either a curtailment/derating flag from the SCADA status channels or
the growing allowance in flagged periods.

Scope: one wind farm, six turbines, five years; the improvement is specific to systems
with published operating limits.
