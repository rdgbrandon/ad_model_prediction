# Feedback-driven rerun protocol

Written before running the new candidate audit. This is a retrospective analysis
of a previously inspected corpus, not a preregistered or fresh test set.

Keep the existing 12 log PSD bands, grouped trials, low-power training data,
two-regime fitted law, 146/192 mW canonical ceilings and Setup C split sweep.
Use MLP(8), MLP(16,16), and linear models with seeds 0, 1, 2 (linear once).
Never count seeds, anchors, windows, or overlapping splits as independent trials.

Compare four fixed allowance rules without selecting a winner on test labels:
1. Existing Setup C calibration holdout 90th-percentile rate times delta.
2. Twice that rate (historical, post-test-informed sensitivity comparison).
3. Theory slope: norm(q_high - 0.5 * ones) times delta.
4. Theory boundary: the same slope plus the measured law residual at the
   calibration ceiling for the actual anchor. This nonzero boundary term repairs
   the unsupported assumption that the residual vanishes at delta=0.

The 1/2 exponent concerns energy-flux amplitude, not the -17/6 frequency slope.
It applies to drive power only if energy flux is proportional to drive power.
The slope gap is a candidate derivative bound, not a theorem: outside calibration,
the true derivative must stay within that distance from the fitted derivative.
No safety multiplier will be tuned to the new audit.

Report legacy LOTO b as a heuristic. Also report the measured error at the
already-labelled anchor, which is exact only for the trial-mean benchmark target.
This latter diagnostic uses no test labels and requires a labelled anchor at
deployment; it is not a population conformal guarantee.

Primary audit: law coverage and margin by distinct test trial in each canonical
configuration. Sensitivity: all 22 Setup C splits x 12 anchors, with pooled
descriptive rates and worst-configuration success per unique test trial.
Compute one-sided 95% Clopper-Pearson bounds on trial success counts only;
these are nominal binomial reference bounds because power-selected trials from
one apparatus need not be IID. Report usefulness and S/e alongside coverage.

Rebuild spectra from the supplied HDF5 and compare to saved arrays. Save package
versions, SHA-256 hashes, parameters, fits and every audited row. Test the
triangle inequality, boundary term, abstention, and test-label isolation.
