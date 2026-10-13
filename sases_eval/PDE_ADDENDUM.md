# PDE addendum: a localized anchor allowance (post hoc, then confirmed on a fresh test set)

Written after the predeclared run (PDE_PROTOCOL.md), whose result stands: valid 100% / 99.7% / 100%,
but the certificate is positive on only 8% / 36% / 1% of points (median S/e 0), because the anchor
allowance b is one global 97.5% quantile of in-range errors and a heavy error tail dominates it.

## Variant, fixed before the confirmation set is drawn

Under every symmetry used here the invariant z = p * t is unchanged between a test point and its
anchors (advection and adv-diff: b t; diffusion: D t). The solution's difficulty depends on z, so b
is computed per z-bin (Mondrian split conformal, Vovk et al. 2005): the 1,000 calibration points
are cut into 10 equal-count z-bins; b(z) = the (1 - 0.1/m) conformal quantile of the calibration
errors in the bin containing the test point's z. Everything else is unchanged (m = 4 anchors,
beta, A = I, c = 0). Validity of b(z): exchangeability of calibration and anchor inputs within a z-bin.

## Confirmation

A second test set (400 points per system) is drawn with a different random seed after this file
was written; surrogates are retrained identically (same seeds) and saved. Reported on both sets:
the predeclared global b and the localized b(z).

## Expectations (confirmation set)

  A1  Validity with b(z) >= 0.90 on every system.
  A2  Share of points with S > 0 higher with b(z) than with global b, on every system.
  A3  Median S/e over FNO surrogates > 0 on diffusion and adv-diff.
