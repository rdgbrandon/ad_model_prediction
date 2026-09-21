# External-dataset generalization audit

Written and committed before any external test label was read. The question is
whether the ceiling-centred lower bound works outside the capillary corpus, and
whether a coverage rate becomes estimable once there are more than 3-4 distinct
test levels.

## What carries over and what cannot

The capillary construction used the reference exponent 1/2 from a Kolmogorov-
Zakharov energy-flux argument. No such theory exists for an arbitrary dataset,
so it is replaced by a measured reference, fixed here before any run:

    q_ref  = drift slope fitted on the TRAIN region (low control values)
    q_cal  = drift slope fitted on the CALIBRATION region
    centre = y_ceiling + q_cal * delta,  delta = ln(P_test / P_ceiling)
    radius = ||q_cal - q_ref|| * delta
    S      = max(||prediction - centre|| - radius, 0)

The allowance is therefore "the law may drift on the way out by as much as it
already drifted between two disjoint measured regions." This is a declared
rule, not a fitted one. No multiplier will be tuned, and no reference choice
will be revised in response to the audit.

If the true target lies in that ball the reverse triangle inequality gives
S <= ||prediction - truth||. Test labels are read only afterwards, to audit
whether it did.

## Datasets

Each dataset supplies levels of one scalar control, each with a target vector.
Mechanical rules, fixed now:

- Levels are ordered by the control. The lowest 50% (rounded down) train the
  surrogate. Of the rest, the calibration region is every level up to a moving
  ceiling, requiring at least 3 calibration levels. Levels above the ceiling
  are test levels.
- A target that is strictly positive and spans more than one decade is
  log-transformed. Otherwise it is used raw. No per-dataset exceptions.
- Trials are the unit of analysis. Windows, hulls, configurations, seeds and
  overlapping ceilings are never counted as independent trials.

Real measurements:

1. `capillary_psdt` - the original 12-band log temporal PSD, 20 power levels.
   Carried unchanged as the control case.
2. `capillary_psdk` - spatial wavenumber PSD from the same recordings. Same 20
   trials, so it is a second observable, NOT additional evidence.
3. `yacht` - Delft yacht hydrodynamics. 14 Froude numbers, target is residuary
   resistance across 22 hull geometries.
4. `airfoil` - NASA airfoil self-noise. 16 one-third-octave frequencies from
   200 to 6300 Hz, target is sound pressure level across 27 configurations.

Numerical solutions, used for the questions real data cannot answer:

5. `pde_*` - families of 1-D PDE solutions swept over a physical parameter.
   These exist to test whether the coverage check has any power, which requires
   cases where the premise is known to fail. They are mechanism tests and
   supply no evidence about any apparatus.

## Pre-declared outcomes

Recorded before running. The audit is reported whatever it returns.

- The premise is expected to fail somewhere. On the capillary corpus coverage
  was 78/78, which cannot distinguish a sound method from an untested one. A
  dataset where coverage fails is an informative result, not a defect.
- The construction is expected to be weakest where the surrogate is accurate,
  since a small true error hides inside the ball. Low usefulness on an accurate
  model is not a failure.
- On the deliberately broken PDE families, coverage MUST fall. If coverage
  stays high when the drift law is known to be violated, the check is
  non-discriminating and the whole approach fails its most important test.
  This is the pre-registered falsification condition.

## Reporting

Report pooled coverage over DISTINCT (dataset, test level) pairs, with
one-sided 95% Clopper-Pearson bounds, and separately per dataset. These bounds
remain nominal: levels within a dataset share an apparatus or a solver and are
not independent, and extrapolation distance varies across them. Report S/e and
the fraction of cases where S > 0 alongside coverage, never coverage alone.
Report the extrapolation distance delta with every row, since coverage that
holds only at small delta is a much weaker claim.

Do not drop a dataset, level or model after seeing its result. Do not add a
dataset chosen because it worked.
