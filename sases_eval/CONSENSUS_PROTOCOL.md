# Multiple calibration laws: fixed exploratory comparison

Use every subset of at least three trials from each existing law-calibration
set. Fit its slope, take its highest-power labelled trial as reference, and
retain rate ||q-0.5||. No test label enters a ball or its selection.

Compare the existing full-calibration ball with the maximum of the individual
ball-distance bounds and a weighted-ball bound. Choose weights using only the
prediction, centres and radii. For nonnegative weights summing to one, all balls
imply a ball with centre sum(w*c) and squared radius
sum(w*r^2)-sum(w*||c-centre||^2). A distance to this implied ball is a lower
bound; optimization need not be globally optimal to preserve that implication.

This uses a stronger premise: the target must be in every selected calibration
ball. Audit that premise separately. Do not label additional subsets, windows,
seeds or configurations as independent trials. Keep the previous result and
report failures or abstentions. The corpus has already been inspected.
