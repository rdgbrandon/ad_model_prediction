# Ceiling-centred certificate

Retrospective extension, fixed before this audit. Keep all previous splits,
models, targets and k=norm(q_high-0.5) unchanged. The labelled law-calibration
ceiling is already available when computing the previous boundary term.

For delta=ln(P/P_top), define centre=y_top+q_high*delta, radius=k*delta and
S_ceiling=max(norm(prediction-centre)-radius,0). Compute this using calibration
labels and predictions only. Audit test labels afterwards.

If norm(y_test-centre)<=radius, the reverse triangle inequality proves
S_ceiling<=norm(prediction-y_test). This is the same measured growth assumption
audited in the mechanism study. It does not require the LOTO anchor heuristic.
No change to k or choice of reference exponent will be made based on this audit.

Compare against both prior anchor variants, report each distinct model/seed and
configuration, and do not count repeated anchors as extra trials. The premise
is target-tube coverage, distinct from the earlier anchor-law-residual coverage.
No population claim follows from this retrospective three/four-trial corpus.
