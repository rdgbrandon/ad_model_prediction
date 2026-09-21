# Testing the certificate outside the capillary corpus

Protocol: `EXTERNAL_PROTOCOL.md`, written and committed before any external
test label was read. Reproduce with `python sases_eval/external_audit.py`.

Four sets of real measurements and four families where the answer is known in
advance. 23 distinct measured test levels, against 3-4 in all previous work.
Three allowance rules, all scored on everything:

| Rule | Radius | Origin |
|---|---|---|
| A | `\|\|q_cal - q_train\|\| * delta` | generic replacement for the KZ exponent |
| B | A `+ b_cal` (max law-fit residual on calibration) | A, plus the boundary term from `RERUN_PROTOCOL.md` item 4 |
| C | `\|\|q_cal - 0.5\|\| * delta` | the incumbent, unchanged from `CEILING_PROTOCOL.md` |

## Results

| Dataset | Levels | Test levels | A cov / (S/e) | B cov / (S/e) | C cov / (S/e) |
|---|---:|---:|---|---|---|
| capillary_psdt | 20 | 7 | 0.857 / 0.750 | **1.000** / 0.682 | 0.714 / 0.793 |
| capillary_psdk | 20 | 7 | 0.750 / 0.618 | 0.750 / 0.540 | 0.607 / 0.743 |
| yacht | 14 | 4 | 0.300 / 0.688 | 0.600 / 0.635 | **1.000** / 0.423 |
| airfoil | 16 | 5 | 1.000 / 0.901 | 1.000 / 0.885 | 1.000 / 0.900 |
| **pooled measured** | | **23** | **0.778** / 0.725 | **0.864** / 0.665 | **0.765** / 0.750 |

Nominal one-sided 95% Clopper-Pearson lower bounds on distinct test levels
covered by every configuration: A 0.222, B 0.335, C 0.296. These remain
nominal; levels within a dataset are not independent.

## 1. The original capillary result reproduces, and was split-dependent

Restricted to the original split (ceiling 146 or 192 mW, test 250-350 mW), the
incumbent still covers **42/42**. Nothing earlier was wrong.

Swept over every admissible ceiling instead, on the same 20 recordings, the
incumbent covers **0.714**. The 100% was a property of the two hand-chosen
ceilings, not of the corpus.

The failures are not where one would guess. They are at **short** extrapolation
from a **low** ceiling:

| Ceiling | Test | delta | Radius | Residual | Covered |
|---:|---:|---:|---:|---:|---|
| 106 mW | 125 mW | 0.16 | 0.62 | 1.79 | no |
| 106 mW | 350 mW | 1.19 | 4.52 | 6.33 | no |
| 54 mW | 350 mW | 1.87 | 16.22 | 9.08 | yes |
| 192 mW | 350 mW | 0.60 | 4.05 | 2.12 | yes |

The radius vanishes as delta goes to zero; the law's error at the ceiling does
not. At a 106 mW ceiling the law is already off by 1.79 before any
extrapolation begins, and no multiple of delta can cover a constant. Coverage
across distance bins is non-monotone (C: 0.78, 0.56, 0.83, 0.87), so
extrapolation distance is **not** the variable that governs failure. The
quality of the calibration fit is.

Adding the boundary term (rule B) fixes exactly this case and lifts the
capillary corpus to **1.000 over all 28 ceiling/test combinations**. The
capillary work had already identified this term and the ceiling construction
had dropped it.

## 2. The falsification test failed for A and B, and half-passed for C

Pre-registered condition: on `synth_break`, coverage must fall relative to
`synth_loglinear`.

| Family | Law | A | B | C |
|---|---|---|---|---|
| synth_loglinear | exact | 0.000 | 0.267 | 1.000 |
| synth_break | violated (slope jump) | 0.200 | 0.400 | 0.667 |
| synth_curved | violated (quadratic) | 1.000 | 1.000 | 1.000 |
| pde_burgers | unknown | 0.800 | 0.900 | 0.900 |

**Rules A and B are anti-discriminating.** They cover the broken family *more
often* than the family where the law is exactly right. The reason is
structural: their radius is proportional to how much the slope changes between
two measured regions, so a badly behaved law buys itself a bigger allowance.
Coverage under A and B measures slope instability, not correctness. Both are
rejected.

**Rule C, the incumbent, is the only rule that moves the right way** on a slope
break: 1.000 to 0.667. It still misses smooth curvature entirely (`synth_curved`
1.000), so it detects a kink and not a bend.

## 3. What the incumbent's radius is actually made of

On capillary calibration the fitted slope has norm 13.34. Distances to
candidate references: 0 gives 13.34, **0.5 gives 11.93**, 1 gives 10.61. The
reference moves the radius by about 20%; the fitted slope sets the rest.

So the KZ exponent is not carrying the construction. Rule C works better than
A and B because a fixed reference keeps the radius from collapsing when the law
is good, not because 1/2 is physically right. This is consistent with the
earlier mechanism audit, which found other reference exponents worked too, and
puts a number on it.

## 4. Where it transfers and where it does not

`airfoil` is the clean success: 1.000 under all three rules with S/e ~0.90, at
delta up to 1.15. Sound pressure level across 27 configurations drifts smoothly
and log-linearly with frequency, which is what the construction assumes.

`yacht` splits the rules hardest: A covers 0.300, C covers 1.000 but pays for it
with S/e 0.423 — the lowest informativeness of any measured dataset. Residuary
resistance rises very steeply with Froude number, so the fitted slope is large
(rate 5.94), which under C inflates the radius until it covers almost anything.

`capillary_psdk`, the second observable on the same recordings, is the weakest
measured case (0.607-0.750). The construction's behaviour depends on which
observable is predicted, not only on the apparatus.

## Bottom line

Testing at scale did not confirm the method; it located its failure mode. The
allowance must not vanish at zero extrapolation distance, and it must not be
proportional to the drift it is supposed to police. The incumbent avoids the
second trap only by using a fixed reference, and avoids the first not at all —
which is why it loses 29% of capillary cases once the ceiling is allowed to
move.

The honest summary of coverage outside the original split is **0.765-0.864 over
23 distinct test levels**, not the 1.000 that 3-4 levels suggested. The
construction is real but considerably less reliable than the capillary corpus
implied, and no combination of these rules both covers the good case and
rejects the bad one.
