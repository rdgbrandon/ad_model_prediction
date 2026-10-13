# Provenance of the fourteen error-predictors

For each competitor in `predictors_audit.py`: where the method comes from, what
the published version guarantees, and how this implementation departs from it.
The third column is the one that matters for the paper — for most of these, the
citation supports the *estimator* and not the *guarantee*, because the guarantee
assumes something this corpus deliberately violates.

Verify every reference below against the original before it goes into a
bibliography. They are given from memory, and a wrong year in a related-work
section is a reviewer's first free hit.

## Established methods, with a canonical citation (8)

| method | published as | what the citation does and does not license here |
|---|---|---|
| `loto_conformal` | Conformal prediction: Vovk, Gammerman & Shafer, *Algorithmic Learning in a Random World* (2005); split/inductive form in Papadopoulos et al. (2002); regression treatment in Lei, G'Sell, Rinaldo, Tibshirani & Wasserman, *JASA* (2018) | Coverage requires calibration and test points to be **exchangeable**. Here the test point is a drive power outside the calibration range, chosen for that reason. The estimator is conformal; the 1-alpha coverage is not inherited. The covariate-shift extension (Tibshirani, Barber, Candès & Ramdas, NeurIPS 2019) needs a likelihood ratio between training and test covariate distributions, which is undefined when the supports do not overlap — as here. |
| `jackknife_plus` | Barber, Candès, Ramdas & Tibshirani, "Predictive inference with the jackknife+", *Annals of Statistics* (2021) | Same exchangeability requirement; the paper's worst-case 1-2alpha guarantee is for exchangeable data. Grouping the folds by trial is standard practice but does not repair extrapolation. |
| `seed_ensemble` | Deep ensembles: Lakshminarayanan, Pritzel & Blundell, NeurIPS (2017); earlier ensemble-ambiguity decomposition in Krogh & Vedelsby, NeurIPS (1995); query-by-committee in Seung, Opper & Sompolinsky, COLT (1992) | A heuristic uncertainty signal with no coverage claim even in the original. Ovadia et al., NeurIPS (2019), measured that ensemble uncertainty degrades under distribution shift — which is the regime this audit is entirely about, so a poor result here is the expected one, not a surprise. |
| `bootstrap_trials` | Efron, *Annals of Statistics* (1979); Efron & Tibshirani, *An Introduction to the Bootstrap* (1993); neural-network prediction intervals from bootstrap ensembles in Heskes, NeurIPS (1996/97) | Resampling at the trial level is the cluster/block bootstrap (Künsch 1989 for blocks; Field & Welsh, *JRSS-B* 2007 for clusters), correct given the grouped structure. It estimates the sampling variability of the fit, which is not the same quantity as the error at a point outside the sampled range. |
| `gp_sigma` | Rasmussen & Williams, *Gaussian Processes for Machine Learning* (2006) | The posterior sd is exact given the kernel and noise model. Far outside the data the sd reverts to the prior, so the number reports the prior's assumption about smoothness, not evidence from the corpus. |
| `blr_sigma` | Bayesian linear regression: MacKay, *Neural Computation* (1992); Bishop, *PRML* ch. 3 (2006); sklearn's `BayesianRidge` implements the evidence approximation, close to Tipping, *JMLR* (2001) | Predictive variance grows with leverage, which is the right qualitative shape for extrapolation, under a linear-model assumption the surrogates do not share. |
| `leverage` | Hat matrix: Hoaglin & Welsch, *The American Statistician* (1978). Applied as an applicability domain in QSAR: Jaworska, Nikolova-Jeliazkova & Aldenberg, *ATLA* (2005); Netzeva et al., *ATLA* (2005); the Williams plot in Gramatica, *QSAR Comb. Sci.* (2007) | The applicability-domain literature built this to flag points **outside** the domain, not to quantify error once you are outside. Every row in this audit is outside. |
| `distance` | Similarity-to-training-set as an accuracy predictor: Sheridan, Feuston, Maiorov & Kearsley, *J. Chem. Inf. Comput. Sci.* (2004); the OECD applicability-domain guidance generalises it | A deliberately minimal baseline. It is included because if it matches the certificate, the certificate is reporting the extrapolation distance and nothing more. |

## Nearest published relative only, not a citation (2)

| method | closest published idea | why it is not the same thing |
|---|---|---|
| `loto_slope` | Distance-based error models in chemistry and materials ML, e.g. Janet, Duan, Yang, Nandy & Kulik, *Chemical Science* (2019), which calibrates error against latent-space distance | That work fits error against distance in a learned latent space with hundreds of held-out points. Here it is a straight line through twelve leave-one-trial-out residuals against the fold's own power gap, extrapolated past every gap it was fitted on. Cite it as an analogue, not as the method. |
| `family_ensemble` | Disagreement across equally-good models: Breiman's "Rashomon effect", *Statistical Science* (2001); formalised as model-class reliance in Fisher, Rudin & Dominici, *JMLR* (2019) | Those papers study the spread of a *population* of near-optimal models. This column is the spread of eighteen arbitrary sklearn fits of very unequal quality, which is a different object; a `poly3` fit whose extrapolation error is 200 is in the ensemble. |

## Internal to your proposal, with no external citation (4)

`sases_ceiling`, `sases_consensus`, `defect_raw` and `law_gap_train` all come out
of the anchor-symmetry construction and its ceiling variant. Nothing outside your
own drafts defines them, and the audit should say so plainly rather than let them
sit in a table that looks uniformly sourced.

The honest external framing for them is the literature on error bounds under
domain shift — Ben-David, Blitzer, Crammer, Kulesza, Pereira & Vaughan, *Machine
Learning* (2010) is the standard reference for bounding target-domain error using
a divergence between domains. The structural difference is worth stating: those
bounds are *upper* bounds on error given a divergence, while yours is a *lower*
bound derived from a known transformation law, and a lower bound on error is the
rarer and more falsifiable claim. That contrast is a stronger related-work
paragraph than any of the individual citations above.

The physics side does have citations: the Kolmogorov-Zakharov flux exponent
behind `kappa = ||q - 0.5||` traces to Zakharov & Filonenko (1967) for capillary
wave turbulence, and the corpus is Orosco, Connacher & Friend, UC San Diego
Library Digital Collections (2023), DOI 10.6075/J0WW7HVJ.

`insample_rmse` and `constant` are baselines, not methods, and want no citation.

## The sentence this table is really for

Of the fourteen competitors, eight are established methods and six are not, and
for all eight of the established ones the published guarantee assumes
exchangeability, an applicability domain, or a correct generative model —
assumptions this corpus violates by construction, since every scored point is an
extrapolation to a drive power outside the calibration range. So the comparison
in `predictors/` is between one method that claims a bound under an audited
premise and several methods used outside the conditions their own papers state.
Reporting them as peers, with that stated, is the defensible framing; reporting
them as peers silently is not.
