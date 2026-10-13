# Does training a surrogate on the law blind the certificate that checks it?

The certificate is one-sided: a surrogate whose errors respect the law it is
checked against cannot be caught. Physics-informed training (Raissi et al.
2019; Beucler et al. 2021) is designed to produce exactly such surrogates. So
far this blind spot is supported only by a hard-coded model whose defect is zero
by construction. This audit measures it on surrogates that are trained, softly
and to varying strength, toward the law.

## The surrogate

A two-layer tanh network of width 16, trained by L-BFGS in plain numpy
(`pinn.py`; gradient verified against finite differences in `test_pinn.py`).
Loss = mean squared error on the TRAIN windows (12-54 mW) + w x the squared law
residual  f(u + du) - f(u) - q du  on 40 unlabelled collocation pairs spanning
ln(54 mW) to ln(400 mW), + weight decay 1e-4. The physics term uses no labels;
it constrains the surrogate only where it has no data, as a physics-informed
network would. No LAWCAL or TEST target enters the surrogate.

## Three laws to train toward, fixed now

  certificate law   q = slopes(LAWCAL), the exact law the ceiling certificate
                    checks against. Training toward it is the blind-spot test.
  training law      q = slopes(TRAIN), the law visible in the training band,
                    extrapolated. Uses no labels beyond the surrogate's own.
  KZ theory         q = 0.5 in every band, the textbook weak-turbulence
                    exponent the certificate's growth radius is centred on.

Penalty weights w = 0, 0.01, 0.1, 1, 10, 100, 1000. Seeds 0, 1, 2.
Representations ctr12 and pist12. Splits canonical_146 and canonical_192.

## Predeclared expectations

  H1  Manipulation check: the surrogate's own law residual falls as w rises, in
      every arm. If it does not, nothing else here is interpretable.
  H2  Blind spot: in the certificate-law arm, S/e falls as w rises - the
      certificate sees a smaller share of the error once the surrogate has been
      trained on the law it checks. Falsified if S/e is flat or rising.
  H3  Wrong law: in the KZ arm, where 0.5 is far below the measured slopes,
      the error grows with w and the certificate grows with it.

Validity must hold wherever the premise holds; the code asserts it.

## What is reported

For every arm, weight, seed, representation, split and test trial: e, S, the
consensus bound, the raw defect, S/e, the silent rate S <= 1, the surrogate's
own law residual and its training error. Every outcome is reported, including
one that falsifies H2 - a result in which physics-informed training does not
blind the certificate is as publishable as one in which it does.

Four distinct test trials on one apparatus, as everywhere in this repository.
