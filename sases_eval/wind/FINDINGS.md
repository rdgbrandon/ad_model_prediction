# Independent replication on wind turbines: the theorem survives, the allowance does not

The certificate was re-run on an unrelated physical system: six Senvion MM92
turbines at Kelmarsh, 10-minute SCADA, May-December 2016 (Kelmarsh wind farm
dataset, Cubico Sustainable Investments Ltd, Zenodo 16807551, CC-BY-4.0).
Forty-eight turbine-months, each a self-contained replication with its own nine
surrogates, law calibration and tests: 2,547 scored rows. Law: P ~ U^3 and
rotor speed ~ U, so in logs q_th = (3, 1). Protocol `WIND_PROTOCOL.md`, fixed
before any certificate was computed on these data.

**The predeclared result is a failure, and it is the most important result in
this repository.**

## The predeclared run: the bound fails on 82% of rows

| | scenario A, 8.5-10.5 m/s | scenario B, 11.5-14.5 m/s |
|---|---:|---:|
| units | 48 | 25 |
| premise held (target inside growth ball) | **0.000** | **0.000** |
| bound held (S <= e) | **0.178** | **0.171** |
| units where the bound held on every row | 0/48 [0.000, 0.074] | 0/25 [0.000, 0.137] |
| median S/e | 1.07 | 1.61 |

The growth radius `||q_cal - q_th|| x delta` — the allowance behind **every
headline number** on the capillary corpus, including the deck's 931/931 and
399/399 — never covered the real law residual. From labels alone, with no
surrogate involved:

| | growth radius given | law residual to cover | shortfall |
|---|---:|---:|---:|
| scenario A | 0.023 | 0.114 | **4.4x** |
| scenario B | 0.068 | 0.800 | **11.6x** |

**Why.** That rate measures how far the fitted exponent sits from theory, not
how far the real system departs from the law. On wind the fitted exponents
(3.06, 0.85) are close to theory (3, 1), so the radius collapses, while the real
residual — power-curve curvature and rotor-speed saturation near 9 m/s — is not
small. On the capillary corpus the measured slopes (1 to 7) were far from the KZ
value 0.5, so the radius was accidentally large (kappa 12 to 19) and the premise
held by default. **The 100% validity on the capillary corpus was a property of
that corpus and that rate, not of the method.**

## The paper's own rule (Eq. 5), run afterwards and labelled post hoc

`WIND_ADDENDUM.md` was written after the primary result and adds one analysis:
the allowance the paper actually states, `beta = 2 x kappa'_fit x delta`, with
kappa' fitted by leave-the-top-out on LAWCAL alone.

| | scenario A | scenario B |
|---|---:|---:|
| beta / law residual (median) | 0.92 | 0.38 |
| premise held | 0.453 | 0.011 |
| bound held | 0.631 | 0.179 |
| **bound held where the premise held** | **783 / 783** | **9 / 9** |
| bound failed where the premise failed | 638 / 945 | 672 / 810 |

Better below rated, still far from a bound; across the rated break it covers
almost nothing, as a smooth allowance must when the physics plateaus.

**But the cross-tab is the result that matters for the theory.** Across both
scenarios the premise held on 792 rows and the bound held on every one of them.
Where the premise failed, the bound failed on 1,310 of 1,755 rows. Proposition 1
is exactly as conditional as it claims — and this is the first time that has
been *tested*. On the capillary corpus the premise never failed, so the
conditional guarantee was never at risk; here it was at risk 1,755 times and
behaved correctly every time.

## The comparison reverses

Scenario A, the lower-bound reading for every method:

| | below e | median score/e | rank correlation |
|---|---:|---:|---:|
| SASES consensus | 0.178 | 1.07 | **0.985** |
| Calibration maximum | **0.995** | 0.65 | 0.955 |
| OLS error predictor | 0.472 | 1.01 | 0.954 |
| Raw defect | 0.165 | 1.07 | **0.986** |

The trivial baseline — the largest surrogate error seen on the calibration bins
— sits below the true error on 99.5% of wind rows and wins every paired test.
It does so for a structural reason: surrogate error grows with extrapolation
distance here, so the calibration maximum is a near-automatic underestimate. It
failed on the capillary corpus precisely where error did not grow (`krr_rbf`).
SASES beats only the raw defect (paired p = 0.02 over units, 0.031 over
turbines, 0.11 over months).

**Ranking survives.** The certificate ranks the nine surrogates by error at
rho = 0.985 below rated and 0.826 across the break — but the raw defect, which
claims nothing, does identically.

## Verdicts on the predeclared hypotheses

| | | |
|---|---|---|
| H1 | bound holds where premise holds; premise holds on most units | **Fails.** Premise held on no row |
| H2 | premise fails in B; bound fails only where premise failed | **Vacuous as predeclared** (premise never held anywhere); **supported** under the post-hoc paper rule, 0 of 792 |
| H3 | SASES below-rate beats every competitor, significant by turbine and month | **Fails.** Calibration maximum wins everywhere |
| H4 | positive rank correlation in A | **Holds**, rho 0.985 — but no better than the raw defect |

One error in the protocol itself: it described scenario A as "the law is
approximately right". For power that is so; for rotor speed it is not — the
rotor reaches its 15 rpm ceiling inside the band, and the label-level residual
splits equally between the two outputs (0.076 each).

## What this means for the paper

1. **Proposition 1 is sound and now independently tested:** zero violations in
   792 rows where its premise held, on a system unrelated to the one it was
   developed on.
2. **The allowance is the method's weak point, and it is not capillary-specific.**
   No calibration-only rule tried covers the law residual reliably once the
   input leaves the calibration band. This confirms, on independent data, the
   proposal's own conclusion that kappa' must come from an external source —
   theory or a solver sweep — rather than from calibration data.
3. **The headline "bound held on 100% of rows" cannot be stated as a property of
   the method.** It holds on the capillary corpus under an allowance that turns
   out to be uncalibrated. On an independent system the same allowance gives
   17.8%.
4. **A trivial baseline must be in every comparison.** The calibration maximum
   beat SASES as a lower bound on wind and lost on capillary; which one wins
   depends on how error grows with distance, which a practitioner cannot know in
   advance.

## Scope

48 turbine-months are far more independent than four capillary trials, but they
share six turbines and eight months, and results are reported clustered by both.
One seed per surrogate family, as declared. The raw archive is not committed;
`build_wind.py` rebuilds `wind/records.npz` from it.

Reproduce: download `Kelmarsh_SCADA_2016_3082.zip` from Zenodo 16807551 into
`external_data/kelmarsh/`, then run `build_wind.py`, `wind_audit.py`,
`report_wind.py` and, for the addendum, `wind_paper_rule.py`.
