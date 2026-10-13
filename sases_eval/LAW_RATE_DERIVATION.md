# What weak-turbulence theory supplies, and what remains unproved

Reference [7] in the week-3 PDF has the wrong title. The intended paper is
V. E. Zakharov and N. N. Filonenko, *Weak turbulence of capillary waves*,
J. Appl. Mech. Tech. Phys. 8(5), 37-40 (1967),
https://doi.org/10.1007/BF00915178 . The author's archive is
https://zakharov75.itp.ac.ru/static/local/zve75/zakharov/1967/1967-03-art3A10.10072FBF00915178.pdf .
The frequency-domain form is also written explicitly in equation (2) of
https://arxiv.org/html/2501.18970v2 .

## Derivation for an ideal capillary surface spectrum

Write epsilon for cascade energy flux, distinct from electrical drive power P.
In the stationary, isotropic, three-wave capillary inertial range,

    S_eta(omega; epsilon) = C epsilon^(1/2) (sigma/rho)^(1/6) omega^(-17/6).

For fixed frequency bands, fluid properties and transfer function, taking the
logarithm of band-averaged PSD gives

    y_b(u) = a_b + (1/2) log epsilon(exp(u)),   u = log P.
    dy/du = (gamma(u)/2) 1,   gamma(u) = d log epsilon / d log P.

Thus the 1/2 exponent is a flux exponent. It is a drive-power exponent only
under the extra assumption epsilon(P)=cP. An input-dependent spectral shape,
dissipation cutoff, transfer function, finite-window log-PSD estimation error,
or nonstationarity is not bounded by the exponent alone.

## Conditional allowance proposition

Let the true target be absolutely continuous and obey

    y'(u) = (gamma(u)/2) 1 + r'(u),
    gamma_minus <= gamma(u) <= gamma_plus,
    ||r'(u)||_2 <= eta

throughout the full extrapolation interval. Let y0 be the measured ceiling
label, ||y(u0)-y0|| <= b0, and q any slope fitted on calibration labels.
Then, for u>=u0,

    ||y(u) - [y0 + q(u-u0)]||_2 <= b0 + kappa (u-u0),
    kappa = max(||q - gamma_minus*1/2||_2,
                ||q - gamma_plus*1/2||_2) + eta.

Proof: integrate y'-q from u0 to u, apply the triangle inequality, bound
||q-gamma*1/2|| by its maximum at the endpoints (convexity), then add the
ceiling measurement error. Distance from any surrogate prediction to this ball
is consequently a lower bound on its error. This proves the implication; it
does not establish the physical premises for this apparatus.

The previously used kappa=||q-0.5|| is exactly the special case gamma=1,
eta=0, b0=0. It therefore has a conditional derivation, but it is NOT a
finite-sample bound supplied by weak-turbulence theory. Its q still comes from
calibration labels. There is no justified, fully theory-determined numerical
rate for these measurements without independent bounds on gamma, eta and b0.
Taking eta=0 is an idealization, not an estimated uncertainty of zero.

## Targets matter

For the spectral-shape target, H=I-11^T/B removes the common log level.
H1=0, so the ideal derivative of Hy is ZERO, not 0.5 in each band. The
corresponding rate is ||q_shape||+eta_shape. The historical subtraction of 0.5
in ctrshape is a heuristic inflated radius with no KZ interpretation.
For piston displacement, a separate measurement/operator model is needed;
the surface-elevation spectrum does not automatically justify the same rate.
Other surface PSD representations retain reference 0.5 only when their
bands lie in the inertial range and estimator corrections are controlled.

## What would close the theory gap

Measure or bound energy-flux versus drive elasticity; establish the inertial
range over the deployment interval; independently bound departures and ceiling
measurement error. Freeze those inputs before reading new test labels. A
maximum observed secant residual on four already viewed trials is not a
uniform derivative bound and cannot replace these missing inputs.

The accompanying theory_rate_audit.py checks the idealized, target-corrected
premise on existing trial targets. This is a falsification diagnostic, not a
fit of eta and not a new population-level coverage experiment.
