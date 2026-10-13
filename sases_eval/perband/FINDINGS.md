# Per-output law allowance: tested and rejected. The sphere allowance is kept.

Protocol: `PERBAND_PROTOCOL.md`. Code: `perband_audit.py` (numbers), `perband_figures.py` and
`perband_bound_plots.py` (figures). Report: `perband/report.txt`.

**Decision: the certificate keeps one law allowance for all outputs,**
S = max(D - b - beta, 0), premise ||zeta|| <= beta. The per-output variant
S_j = max(D_j - b_j - beta_j, 0), S = ||S_vec|| is not adopted.

## Why

| | sphere (kept) | per-output |
|---|---|---|
| Proposition 1, failures where premise held | 0 | 0 |
| Capillary rule P (146 mW): premise / validity | 0.61 / 0.76 | 0.00 / 0.53 |
| Capillary rule C (146 mW): premise | 1.00 | 0.29 |
| Wind 2019 rule P below rated: premise / validity | 0.55 / 0.72 | 0.41 / 0.66 |
| Wind 2019 rule E1 below rated: premise / validity | 0.72 / 0.83 | 0.51 / 0.81 |
| Wind 2019 rule E3 below rated: premise / validity | 0.90 / 0.94 | 0.89 / 0.93 |
| Median per-output S / sphere S | 1 | 1.01-1.03 |

Wind 2019 was downloaded after the protocol was written and is the unseen
confirmation year; wind 2016-18 and capillary are development and agree.

The per-output premise is harder to satisfy (every output must be covered) and
each per-output allowance is estimated from one to ten calibration hops, so it
misses the outputs where the law's error sits (capillary bands above ~5 kHz). Where
it does hold, it claims only 1-3% more of the error. Solar has one output, so the
two forms are identical there.

## For the paper

One sentence: a per-output allowance, the same three-term certificate applied
output by output, was tested and rejected; it lowered premise coverage on both
multi-output systems and raised the median score by at most 3%.
