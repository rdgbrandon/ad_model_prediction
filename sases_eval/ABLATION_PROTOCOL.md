# Which error terms is the certificate actually paying for?

Proposition 1 subtracts two allowances from one defect:

    S = [ D - b - beta ]+ / ||A||,      ||A|| = 1 here.

Each subtraction is a claim about a different error source: b about the
surrogate's error at the anchor, beta about the law's departure from the real
system. This audit turns each term off and on and measures what the corpus says
each one buys. No refitting is involved: D, b, beta, zeta and e are already
stored per row in `rerun/audit_rows.csv`, so every variant is an exact
recomputation of the same audited quantities.

## The factorial

Terms subtracted, counted as "parameters used":

  0   S = D                        the bare defect
  1   S = [D - b]+                 anchor allowance only
  1   S = [D - beta]+              law allowance only
  2   S = [D - b - beta]+          Proposition 1 as written
  3   S = [D - b - m*beta]+        plus the declared safety multiplier m

Crossed with the sources already present in the audit:

  b      legacy_loto (conformal leave-one-trial-out) | labelled_anchor
  beta   fitted kappa' | 2x declared | theory slope | theory slope + boundary
  m      0, 0.5, 1, 1.5, 2, 3 applied to the fitted kappa'
  anchor single predeclared | maximum over all admissible anchors

## What is measured for every cell

  validity        fraction of rows with S <= e, the bound's own claim
  beta coverage   fraction with ||zeta|| <= beta, the premise Proposition 1 needs
  licensed        validity restricted to the rows where the premise held
  non-vacuity     fraction with S > 1
  informativeness mean and median S/e
  rank            Spearman correlation with e across the surrogate fits

Abstentions are counted, never silently dropped: the 112 rows where kappa' is
not estimable are reported as abstentions in every cell that needs a fitted
beta.

## What the result can and cannot say

Validity is already known to be non-discriminating on this corpus, so a cell
that keeps validity 1.000 has not thereby been shown correct; it may only show
that e is large. The informative comparison is therefore between cells, along
the trade between informativeness and the premise coverage that licenses it,
and not the absolute value of any single column.

Four distinct test trials, one apparatus. This audit re-slices rows that
already exist; it adds no new evidence and cannot raise the effective sample
size. Report every cell, including those where dropping an allowance looks
better than keeping it.
