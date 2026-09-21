# A tighter bound from the same labelled data

The new certificate uses the already-labelled law-calibration ceiling directly:

`centre = y_ceiling + q_high * delta`

`radius = ||q_high - 0.5|| * delta`

`S = max(||prediction - centre|| - radius, 0)`

If the true target lies in this ball, the reverse triangle inequality proves
that its prediction error is at least S. There is no LOTO calibration claim.
This target-ball premise differs from coverage of the old anchor-law residual.
The growth budget is unchanged and was not optimized on the rerun audit.

## Canonical comparisons: MLP(8), seed 0

| Law ceiling | Old LOTO anchor mean S/e | Labelled anchor mean S/e | New labelled ceiling mean S/e | Target-ball coverage | Nominal CP lower |
|---|---:|---:|---:|---:|---:|
| 146 mW | 0.105 | 0.589 | **0.685** | 4/4 | 0.473 |
| 192 mW | 0.298 | 0.747 | **0.809** | 3/3 | 0.368 |

The input labels and fitted law remain the same. Using the ceiling directly
removes two triangle-inequality penalties. In fact, for the same law and growth
budget this certificate is at least as large as the previous score with an
exact labelled-anchor error allowance, for arbitrary model predictions; a
randomized algebraic test checks that dominance. Comparison with the older
LOTO heuristic is empirical, since it need not upper-bound the anchor error.

For the 22-split sweep, duplicate anchors are unnecessary: 29 split-trial rows
reuse 3 test trials. All target balls cover, nominal lower bound 0.368, and mean
S/e is 0.891. These overlapping configurations are not independent validation.
The direct ceiling construction is also interpretable as distance from a
calibration-derived prediction region, so it should not be presented as a new
symmetry theorem or as proof that the KZ exponent is uniquely correct.

Seven model/seed combinations were freshly fitted. The complete scalar rows,
predictions, target spectra, centres, margins, code hash, dataset hash and
protocol hash are in `results.json`; scalar rows are in `rows.csv`.

The website at `http://127.0.0.1:8765` can rebuild the supplied HDF5 dataset and
rerun this analysis. Start it with `.venv/Scripts/python.exe web/server.py` from
the repository root. The dataset remains small, previously inspected, from one
apparatus, and measured trial means are not noise-free physical ground truth.
