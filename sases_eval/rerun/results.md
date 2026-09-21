# Theory-informed rerun: measured results

Retrospective audit; same corpus, no new independent trials. MLP(8), seed 0 unless stated.

CP lower bounds below are one-sided 95% nominal IID-binomial references. Power-selected trials from one apparatus need not be IID.

## Canonical 192 mW ceiling

| Allowance | Covered trials | CP lower | S > 1 | Mean S/e | Min margin |
|---|---:|---:|---:|---:|---:|
| Fitted rate | 2/3 | 0.135 | 1.000 | 0.468 | -0.298 |
| Historical 2x | 3/3 | 0.368 | 1.000 | 0.153 | 2.114 |
| Theory slope | 3/3 | 0.368 | 1.000 | 0.372 | 0.438 |
| Theory + boundary | 3/3 | 0.368 | 1.000 | 0.298 | 1.345 |

## Sensitivity sweep: 348 rows, 3 distinct test trials

Trial success here means coverage under every swept configuration; the CP bound does not apply to the pooled rate.

| Allowance | Pooled coverage | All-config trials | CP lower | S > 1 | Mean S/e |
|---|---:|---:|---:|---:|---:|
| Fitted rate | 0.264 | 0/3 | 0.000 | 0.994 | 0.362 |
| Historical 2x | 0.925 | 1/3 | 0.017 | 0.753 | 0.196 |
| Theory slope | 0.296 | 0/3 | 0.000 | 0.991 | 0.402 |
| Theory + boundary | 1.000 | 3/3 | 0.368 | 0.848 | 0.240 |

The review's 0.21 baseline is reproduced at the fixed 54 mW anchor: 6/29 configuration rows (0.207; 3 distinct trials, all-config CP lower 0.000). The 0.264 baseline above additionally sweeps anchors.

## Boundary-term candidate at both ceilings

- 146 mW: k=15.797, boundary=0.682, coverage 4/4 (nominal CP lower 0.473), mean S/e=0.105.
- 192 mW: k=11.926, boundary=0.906, coverage 3/3 (nominal CP lower 0.368), mean S/e=0.298.

## Model sensitivity: theory + boundary, 192 mW ceiling

| Model / seed | b: LOTO / anchor | Mean S/e: LOTO / anchor | Valid trials: LOTO / anchor |
|---|---:|---:|---:|
| mlp8 / 0 | 7.003 / 1.487 | 0.298 / 0.747 | 3/3 / 3/3 |
| mlp8 / 1 | 6.970 / 1.475 | 0.274 / 0.739 | 3/3 / 3/3 |
| mlp8 / 2 | 7.144 / 1.588 | 0.260 / 0.735 | 3/3 / 3/3 |
| mlp16x16 / 0 | 5.632 / 1.394 | 0.000 / 0.000 | 3/3 / 3/3 |
| mlp16x16 / 1 | 4.976 / 1.271 | 0.000 / 0.008 | 3/3 / 3/3 |
| mlp16x16 / 2 | 4.752 / 1.458 | 0.150 / 0.597 | 3/3 / 3/3 |
| linear / 0 | 6.366 / 0.721 | 0.238 / 0.637 | 3/3 / 3/3 |

## Verification and scope

All rebuilt arrays match exactly: True; max absolute spectrum difference 0.0.

Five verification tests pass. Trial-count CP values are nominal references only.

Seven model/seed fits, four allowance rules, two anchor-error modes. Historical ensemble benchmarks were not rerun.

See ../PAPER_REVISIONS.md for corrected theory, related work and guarantee language.
