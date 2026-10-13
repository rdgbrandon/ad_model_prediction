# How accurately does the certificate report the error it bounds?

Validity asks whether S <= e. This audit asks a different question: taken as a
statement about how wrong each surrogate is, how accurate is that statement?
Three readings, scored separately, because the method is honest in one and
deliberately not in another.

## 1. As a point estimate of the error

Bias, mean absolute error and median relative error of S against e. S is a lower
bound, so a negative bias is built in and is reported, not corrected. A scale
calibrated version c*S is also reported, with c the median ratio e/S fitted by
leaving one test trial out. That calibration reads test labels and could not be
performed at deployment; it is an upper reference on what a rescaled certificate
could achieve, never a usable method.

## 2. As an ordering of surrogates

At each case, all 19 surrogate fits are ranked by S and compared against their
ranking by e: the fraction of model pairs placed in the correct order, the ties,
and whether the single worst surrogate is identified. Ties created by the
certificate falling silent (S = 0) are counted as no call, not as errors, and
their rate is reported alongside.

## 3. As a detector of unreliable surrogates

Within each case a surrogate is "bad" if its error exceeds the median error over
the 19 fits at that same case, a within-case threshold so that representations
with different target scales stay comparable. S is scored as a detector by
ROC AUC and by precision and recall at the operating point S > 1, the
non-vacuity threshold already used in the earlier audits.

## Scope

931 ceiling-form rows over seven representations, plus the Proposition 1 anchor
rows for contrast. No refits; every quantity is recomputed from stored results.
Four distinct test trials, one apparatus: these are measurements of how the
certificate behaves on this corpus and license nothing about a population.
Report every reading, including the ones where a competitor or a rescaled
variant is more accurate.
