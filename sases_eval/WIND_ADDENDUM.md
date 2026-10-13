# Addendum to WIND_PROTOCOL.md - written AFTER the primary result was seen

The primary run used the ceiling-form growth rate kappa = ||q_cal - q_th||, as
in every capillary audit behind the headline numbers. On the wind data its
premise held on 0 of 2547 rows: the radius is 4.4x (scenario A) and 11.6x
(scenario B) smaller than the law residual it must cover, a fact computed from
labels alone. WIND_PROTOCOL.md and its results are unchanged and stand.

This addendum adds ONE further analysis, chosen because it is the allowance the
paper itself states (Eq. 5) rather than one invented after the fact:

    beta(x) = 2 * kappa'_fit * [ ln(U / U_lawmax) ]+

kappa'_fit is fitted on LAWCAL alone, by leave-the-top-out: with the four
LAWCAL bins in order, fit the law on bins 1-3 and predict bin 4; fit on bins 1-2
and predict bins 3 and 4. Each prediction gives a ratio ||zeta|| / delta.
kappa'_fit is the maximum ratio - the most conservative calibration-only rule in
the paper's Section 6.5 table - and the declared factor of 2 is applied.

The certificate is then S = max(D - beta, 0) on the stored raw defect D, with
the ceiling label as centre exactly as before. No surrogate is refitted and no
test label enters beta. Because this analysis follows the primary result, it is
exploratory: its outcome cannot rescue or replace the predeclared one, and it is
reported as a separate line.
