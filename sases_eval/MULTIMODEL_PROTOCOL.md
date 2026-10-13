# Many surrogates, many target representations: fixed before the run

Retrospective extension of the ceiling and consensus audits. Nothing about the
corpus, the splits or the certificate changes. What changes is (a) which
regression family plays the surrogate and (b) how the target vector is built
from the raw series.

## Corpus and splits: unchanged

Same 21 trials, one apparatus, already inspected. TRAIN 12-54 mW, LAWCAL
106-146 mW (`canonical_146`) or 106-192 mW (`canonical_192`), TEST above the
LAWCAL ceiling. Splits grouped by trial. No new trials are created, and no
representation, model, seed or split is counted as an independent trial.

## Target representations

Seven window-level representations, all built from series stored at the full
115.2 kHz frame rate, so that no representation's bandwidth depends on drive
power:

  ctr12     centre pixel, 12 log bands, 500 Hz - 20 kHz  (the existing target)
  ctr24w    centre pixel, 24 log bands, 200 Hz - 48 kHz
  ctrlin8   centre pixel, 8 linear bands, 500 Hz - 20 kHz
  ctrshort  centre pixel, 2048-sample windows, 12 log bands, 1 - 20 kHz
  ctrmed    centre pixel, canonical bands, median-averaged Welch segments
  ctrshape  centre pixel, canonical bands, band mean removed (spectral shape only)
  pist12    piston (spatially uniform height) series, canonical band geometry

Excluded in advance: anything built from `wave`, `field` or the stored spatial
spectra. This package stores those with a per-trial time decimation D and
spatial cut K that both vary with drive power, so a power law fitted to them
would partly be a law about the compression budget.

## Models

Declared in full before the run: `linear`, `poly3`, `knn5`, `krr_rbf`, `rf200`,
`gbrt`, `mlp8`, `mlp16x16`, `mlp32x32`. Seeds 0-2 for the stochastic families
(`mlp*`, `rf200`, `gbrt`), a single fit for the deterministic ones. `linear`,
`mlp8` and `mlp16x16` keep their existing definitions exactly. No model is
added, dropped or retuned after seeing a test residual.

## Certificate

The ceiling-centred certificate and the multi-subset consensus bound are
imported from `ceiling_audit.py` and `consensus_audit.py`, not reimplemented:
centre = y_top + q*delta, radius = ||q - 0.5||*delta, S = max(||prediction -
centre|| - radius, 0), and the consensus bound is the strongest bound over all
LAWCAL subsets of size >= 3 plus the weighted-ball blend. Calibration labels and
predictions only; test labels are read afterwards, to audit coverage.

## Reproduction gate

On `ctr12` with `linear`, `mlp8` and `mlp16x16` this harness must reproduce the
stored `ceiling/results.json` and `consensus/results.json` values of S, e and
the consensus bound to 1e-8. If it does not, the run is void and nothing from it
is reported.

## Reporting

Report per representation, model, seed and configuration: S, e, S/e, the
consensus bound and its single-region baseline, target-ball coverage and the
thinnest margin. Report failures, abstentions and negative results. Coverage
counts are descriptive; the representations share trials, so no population
coverage claim follows from any of them, and a representation that fails is
evidence about the representation, not a candidate for removal.
