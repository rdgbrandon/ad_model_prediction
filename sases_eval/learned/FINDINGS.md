# Learned law allowances (NN, KAN) against the formula rules

Protocol: `LEARNED_ALLOWANCE_PROTOCOL.md` (development log records the three changes
made before confirmation). Report: `output/pdf/sases_law_allowance_learned.pdf`.
Numbers: `learned/dev.json`, `learned/confirm.json`, worked examples `learned/derivation.json`.

## Confirmation, wind 2018 (never opened before; train 2016-17)

| rule | below rated: coverage / valid / S/e | rated: coverage / valid / S/e |
|---|---|---|
| E1 (own data, long-hop rate) | 0.781 / 0.884 / 0.93 | 0.011 / 0.196 / 1.22 |
| **Z (own data, monotone saturation, beta = ‖q‖δ)** | **1.000 / 1.000 / 0.60** | **1.000 / 1.000 / 0.48** |
| A-NN (own-data MLP) | 1.000 / 1.000 / 0.79 | 1.000 / 1.000 / 0.52 |
| E3 (fleet per-bin quantile) | 0.878 / 0.946 / 0.95 | 0.970 / 0.983 / 0.86 |
| F0 (fleet rate x delta) | 0.903 / 0.951 / 0.93 | 0.884 / 0.925 / 0.86 |
| F-GBT (fleet, boosted-tree scale) | 0.910 / 0.956 / 0.94 | 0.996 / 0.998 / 0.86 |
| F-NN (fleet, MLP scale, 3 seeds) | 0.979 / 0.983 / 0.91 | 0.993 / 0.997 / 0.82 |
| F-KAN (fleet, KAN scale, 3 seeds) | 0.948 / 0.977 / 0.94 | 0.996 / 1.000 / 0.83 |

## What it means

- A model fitted to a unit's own calibration bins cannot see a break outside them.
  The own-data MLP covers wind only because tanh saturates (it extrapolates a
  plateau, and wind plateaus). Rule Z states that assumption openly and covers wind
  2018 completely from own data alone; it fails on solar below clipping (0.85-0.86)
  because current rises faster than the law there.
- Fleet-trained NN and KAN scales are valid (conformal) but no better than boosted
  trees; all learners recover the same convex sigma(delta). Their gain on wind 2018 is
  robustness (E3 slipped to 0.878, F0 to 0.884), not tightness. KAN is seed-stable on
  wind (spread 0.003), not on solar (up to 0.13).
- Solar: nothing beats E1 (0.964 / 0.998 in 2023). Feature-based fleet models fail
  (0.62-0.82 below clipping in 2023); featureless ones collapse in 2022 (0.46-0.51).
  Solar years are not exchangeable.

Verdicts: L1, L2 (revised), L3, L5, Z1, Z2 hold; L2 (original) falsified in
development; L4 not supported as stated.
