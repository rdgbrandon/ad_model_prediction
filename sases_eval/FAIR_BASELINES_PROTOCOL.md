# Equal-label baseline rerun

Fixed before this rerun; the existing test corpus has already been inspected.
Use ctr12, ctrshape and pist12, all 19 existing model/seed fits, and both
canonical splits. Refit the original surrogate g on TRAIN only, unchanged.
Give all diagnostics exactly the same 3 or 4 labelled LAWCAL trials. Score
only the existing extrapolation TEST trials. No windows count as independent
calibration observations. Save trial identities, scores and jackknife candidates.

Split conformal uses e_i = ||g(log P_i)-Y_i|| and rank ceil((n+1)(1-alpha)).
An out-of-range upper rank is +infinity, never the sample maximum. Alpha=.10.

Jackknife+ predicts the scalar error of the SAME frozen g. This is an explicit
error-regression application, not vector-response jackknife+ refitting g.
Fit ordinary least squares h(log P)->e on the law-calibration trials. For each
left-out trial i, compute r_i=|e_i-h_-i(log P_i)| and candidates
h_-i(log P_test) +/- r_i. Lower rank floor((n+1)*alpha), upper rank
ceil((n+1)*(1-alpha)), with outside ranks -/+infinity. Intersect the resulting
interval with the known error support [0,infinity). Use alpha=.05 for the
general 1-2alpha=90% theorem, and alpha=.10 as a separately labelled nominal
90% sensitivity (general guarantee only 80%). Exchangeability is required
for either theorem and is NOT established for these extrapolation splits.

Also report finite sample-maximum error and full-calibration OLS error
prediction as descriptive heuristics, with no coverage guarantee. These
check equal-label ranking without concealing the strict methods' abstention.
Report lower and upper bounds separately, finite fraction, observed coverage,
and correlation across models at fixed trial. Infinity has no ranking score.
Compare against the unchanged SASES consensus and raw defect. Do not tune
alpha, base learners, slopes, splits or representations using the rerun.

References: https://arxiv.org/abs/1905.02928 (jackknife+); its section 1.1
also describes split conformal and the required corrected quantile.
