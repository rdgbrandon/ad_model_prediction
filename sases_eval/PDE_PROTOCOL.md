# The anchor-symmetry certificate on neural PDE surrogates

Written before any surrogate was trained or any certificate computed. This is the test the
slides ask for: certify a learned surrogate of a solver without calling the solver. The solver
(here an exact analytic solution) is used only afterwards, to score the certificate.

## Systems (1D, periodic on [0, 1), N = 128 grid points)

Initial conditions follow the PDEBench protocol (Takamoto et al., NeurIPS 2022): u0(x) = sum of
two sinusoids A_i sin(2 pi n_i x + phi_i), n_i uniform integer in [1, 8], A_i ~ U(0, 1),
phi_i ~ U(0, 2 pi). Solutions are exact (Fourier), so labels carry no solver error.

| system | PDE | parameter | train range | test range | symmetry T_lambda | law |
|---|---|---|---|---|---|---|
| advection | u_t + b u_x = 0 | speed b | 0.1-1.0 | 1.5, 2, 3, 4 | (b, t) -> (b/lam, lam t) | exact |
| diffusion | u_t = D u_xx | diffusivity D | 0.002-0.02 | 0.03, 0.04, 0.06, 0.08 | (D, t) -> (D/lam, lam t) | exact |
| adv-diff | u_t + b u_x = nu u_xx, nu = 0.003 fixed | speed b | 0.1-1.0 | 1.5, 2, 3, 4 | (b, t) -> (b/lam, lam t) | approximate (nu breaks it) |

Times: train t ~ U(0, 2) (advection, adv-diff), U(0, 1) (diffusion). A test point (u0, p, t) has
admissible anchors lam in [p / p_max, min(t_max / t, p / p_min)] (anchor parameter inside the training range, anchor
time <= training maximum); m = 4 log-spaced anchors in that interval; points without one abstain.

## Surrogates (each fitted once, on the same training set, maps (u0, p, t) -> u(., t))

FNO1d (Li et al., ICLR 2021): modes {8, 16} x width 32 x seeds {0, 1, 2} = 6 models.
1D residual CNN: 2 depths x seeds {0, 1} = 4 models. MLP on (u0, p, t): 2 sizes x 1 seed = 2 models.
12 surrogates per system. Training: 4,000 samples, Adam, 60 epochs, MSE.

## Certificate (slides' notation)

  D(x, lam) = || f(T_lam x) - A_lam f(x) - c_lam ||,  A_lam = I, c_lam = 0 (the symmetry maps outputs to outputs)
  b         = split-conformal (1 - 0.1/m) quantile of ||f - u|| on 1,000 held-out in-range samples
  beta(x)   = 0 for the exact laws; for adv-diff, 2 kappa |ln lam| with kappa the largest symmetry
              residual ||u(p, t) - u(p/lam', lam' t)|| / |ln lam'| over in-range training pairs
  S(x)      = max over admissible lam of [ D - b - beta ]_+ ;  error e = || f(x) - u(x) ||
Norms are RMS over the grid.

## Baselines on the same test points

  Lipschitz certificate: [ ||f(x) - f(x_a)|| - b - L ||(p, t) - (p_a, t_a)|| ]_+, x_a = same u0 at the
     nearest in-range parameters (p_max, same t), L = 2 x the largest ||u(z1) - u(z2)|| / ||z1 - z2||
     over training pairs. A generic Lipschitz law in place of the physical symmetry.
  Split conformal upper bound: q90 of in-range errors, scored as an upper bound on e (coverage).
  Ensemble spread: std across the three FNO seeds of each configuration (ranking only).

## Reported

Validity (S <= e), median S/e, share of points with S > 0, within-point rank correlation of S with
e across the 12 surrogates, and the same for the Lipschitz certificate; conformal coverage.

## Expectations

  P1  Validity >= 0.90 for the exact-law systems (the guarantee is conditional on b only).
  P2  The symmetry certificate is informative (median S/e >= 0.5) where surrogates extrapolate badly.
  P3  The Lipschitz certificate is much less informative than the symmetry certificate.
  P4  In-range conformal upper bounds under-cover out of range.
  P5  adv-diff needs its law allowance: without beta validity drops, with it validity >= 0.90.
  Every outcome is reported.
