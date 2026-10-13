# Lower-bounding surrogate error on capillary-wave spectra

A surrogate model predicts the temporal power spectrum of a driven liquid
surface at a drive power it was never trained on. This repository asks a
narrower question than "is the prediction accurate?":

> Using only **already-labelled calibration measurements**, can we certify that
> a given prediction is wrong by **at least** some amount?

The construction is a reverse triangle inequality. Calibration measurements at
lower powers, extrapolated along a fitted power law, define a ball that should
contain the true spectrum. Any prediction outside that ball must be wrong by at
least its distance to the ball:

```
centre = labelled calibration ceiling + fitted slope x log-power distance
radius = ||fitted slope - 1/2|| x log-power distance
S      = max(||prediction - centre|| - radius, 0)
```

`S` is a lower bound on the prediction's error **conditional on the true
spectrum lying inside that ball**. No test label enters `S`; test labels are
read afterwards only to audit whether the premise held.

## What the audits found

| Audit | Question | Result |
|---|---|---|
| `rerun/` | Do the earlier anchor-based allowances hold up? | The law-approximation allowance, not the anchor error, is the binding constraint |
| `ceiling/` | Does scoring against the labelled calibration ceiling beat the anchor heuristic? | Yes: mean `S/e` 0.298 → 0.809 at 192 mW, MLP(8) |
| `mechanism/` | Is the growth assumption doing real work, or is it triangle-inequality slack? | Growth fits inside the allowance on all 29 checks; endpoint audits cannot exclude interior failure |
| `consensus/` | Does combining rules from calibration subsets tighten the bound? | A modest, model-dependent gain — with three caveats below |
| `external/` | Does any of it work on other datasets, and at more test levels? | **Partly. Coverage is 0.77-0.86 over 23 test levels, not the 1.00 that 3-4 levels suggested** |

**The newest result.** Fitting a separate rule on every subset of at least
three calibration trials and reporting the strongest bound raised the fraction
of measured error we can lower-bound from **74.2% to 78.1%** for the linear
model and from **11.0% to 15.4%** for one larger-network run. The small network
barely moved. Read [`sases_eval/consensus/FINDINGS.md`](sases_eval/consensus/FINDINGS.md)
before quoting those numbers, because:

1. **The comparison cannot come out negative.** The original single rule is one
   of the candidates, so the reported maximum is bounded below by it.
2. **The weighted blend contributes essentially nothing** (≤ 8.2e-4 distance
   units against errors near 13). The gain comes from selecting one subset —
   the one dropping the lowest calibration power.
3. **One configuration could not improve at all.** With three calibration
   trials there is exactly one eligible subset, so its zero change is a
   definition rather than a measurement.

The bound also requires a **stronger premise** than before: the true spectrum
must lie in *all* the selected balls at once (5 on the canonical split, up to
42 on the widest sweep). It did on every audited row, but the thinnest margin
falls to 0.20 distance units.

## The generalization result

[`sases_eval/external/FINDINGS.md`](sases_eval/external/FINDINGS.md) is the
most important result here and the least flattering. Run on four sets of real
measurements (capillary temporal and spatial spectra, Delft yacht resistance,
NASA airfoil self-noise) plus families where the right answer is known:

- The original capillary split still covers **42/42**. Nothing earlier was
  wrong. But swept over every admissible calibration ceiling on the *same*
  recordings, the incumbent covers **0.714**. The 100% belonged to two
  hand-chosen ceilings.
- Failures cluster at **short** extrapolation from a **low** ceiling, not at
  long range. The radius vanishes as the extrapolation distance goes to zero;
  the law error at the ceiling does not. Restoring the boundary term from
  `RERUN_PROTOCOL.md` lifts the capillary corpus back to 1.000.
- A pre-registered falsification test was **failed** by both generic rules:
  they cover a deliberately broken law *more* often than an exact one, because
  their allowance is proportional to the drift it is meant to police. Only the
  incumbent fixed reference moves the right way, and even it misses smooth
  curvature.
- The KZ exponent is not doing the work: moving the reference from 0 to 1
  changes the radius by about 20%, while the fitted slope supplies the rest.


## Plain-language summary

[`How_Wrong_Is_The_Guess.pdf`](How_Wrong_Is_The_Guess.pdf) explains all of this
without jargon, for readers with no background in the area: what was measured,
how the bound works, what the numbers say, and how the approach compares with
conformal prediction, ensembles, physics-residual methods and certified PINN
error bounds. Rebuild it with `python make_summary_pdf.py`, which reads the
committed results so its figures and numbers cannot drift from the audits.

## Read this before drawing conclusions

The corpus is **20 experiments from one apparatus**, already inspected before
these audits were written, with only **3-4 distinct high-power test trials**.
Extra models, seeds and overlapping splits reuse those same trials and add no
independent validation. 3/3 successes give a nominal one-sided 95% lower
coverage limit of 0.368 — and that figure assumes IID trials, which
power-selected trials from one rig need not be. **No population coverage claim
is supported here.** The 448 analysis windows are overlapping slices of 20
recordings, not 448 experiments.

Each audit's protocol was written before it ran and is hashed into its
`results.json`: `RERUN_PROTOCOL.md`, `CEILING_PROTOCOL.md`,
`MECHANISM_PROTOCOL.md`, `CONSENSUS_PROTOCOL.md`.

## Layout

```
sases_eval/
  sases.py capillary2.py piecewise.py honest_beta.py setupc.py   core certificate + splits
  theory_audit.py ceiling_audit.py consensus_audit.py mechanism_audit.py
  build_dataset.py            HDF5 -> 12-band log PSD per window (spec.npz)
  report_theory_audit.py report_mechanism.py                     PDF supplements
  test_*.py                   unit tests for each audit
  spec.npz                    derived spectra; every audit runs from this alone
  rerun/ ceiling/ mechanism/ consensus/    protocols, results.json, findings
web/                          local dashboard over the published results
dataset/                      provenance and checksums only (see below)
```

## Run it

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r sases_eval/requirements-rerun.txt
.\.venv\Scripts\python.exe -m unittest discover -s sases_eval -p "test_*.py"
.\.venv\Scripts\python.exe sases_eval/ceiling_audit.py
.\.venv\Scripts\python.exe sases_eval/consensus_audit.py
.\.venv\Scripts\python.exe sases_eval/mechanism_audit.py
```

Python 3.8.10; `sases_eval/rerun/environment-lock.txt` records the exact
environment. The dashboard:

```powershell
.\.venv\Scripts\python.exe web/server.py    # http://127.0.0.1:8765
```

It serves the checked-in snapshot immediately and can re-run the pipeline from
the browser. It binds to localhost, runs only an allowlist of scripts, and
should not be exposed to a network.

## Dataset

The 50 MB HDF5 is **not redistributed here**. It is a CC-licensed deposit from
UC San Diego — cite the original authors, not this repository:

> https://doi.org/10.6075/J0WW7HVJ

`dataset/` keeps the provenance notes, checksums and the official `decode.py`.
To rebuild spectra from the raw recordings, place `b200_50MB.h5` in `dataset/`
(SHA-256 in `dataset/CHECKSUMS.sha256`) or set `SASES_DATASET` to its
directory, then run `sases_eval/build_dataset.py`. Every audit in this
repository runs from the checked-in `spec.npz` without that step.


## Seven datasets, published limits and neural PDE surrogates (October 2026)

`Seven_Datasets_Certificate.pdf` is the current report: the certificate
S(x) = [D − b − β]₊ with every equation, every law-allowance method (when it
works, evidence, citations), and one section per dataset.

| Study | Protocol | Code | Result |
|---|---|---|---|
| Wind replication (Kelmarsh) | `WIND_PROTOCOL.md`, `WIND_ADDENDUM.md` | `build_wind.py`, `wind_audit.py` | `wind/FINDINGS.md` |
| Data-driven allowances, fleet conformal | `ALLOWANCE_PROTOCOL.md` | `allowance_audit.py` | `wind/ALLOWANCE_FINDINGS.md` |
| Clean-law solar test (PVDAQ 9068) | `PV_PROTOCOL.md`, `PV_DEVIATIONS.md` | `build_pv.py`, `pv_audit.py` | `pv/FINDINGS.md` |
| Learned (MLP, KAN) allowances | `LEARNED_ALLOWANCE_PROTOCOL.md` | `learned_allowance.py`, `kan.py` | `learned/FINDINGS.md` |
| Per-output allowance (rejected) | `PERBAND_PROTOCOL.md` | `perband_audit.py` | `perband/FINDINGS.md` |
| Law with a published cap (K-L) | `BOUND_SHAPE_PROTOCOL.md` | `bound_shape_audit.py` | `bound_shape/FINDINGS.md` |
| Frozen allowance at the cap (K-S1) | `SATURATING_PROTOCOL.md` | `saturating_audit.py` | `saturating/FINDINGS.md` |
| Seven datasets, three-term certificate | `MULTI_DATASET_PROTOCOL.md` | `multi_audit.py` | `multi/report.txt` |
| Ranking 9–100 surrogates | — (exploratory) | `ranking_audit.py` | `ranking/report.txt` |
| Ablation of D, b, β | — (exploratory) | `ablation_multi.py` | `ablation_multi/results.json` |
| Shrink after the cap (K-S3), Kelmarsh 2021 | `KS3_PROTOCOL.md` | `ks3_audit.py` | `ks3/report.txt` |
| Neural PDE surrogates (FNO, CNN, MLP) | `PDE_PROTOCOL.md`, `PDE_ADDENDUM.md` | `pde_surrogates.py` | `pde/report.txt` |
| Machine-level bootstrap intervals | — | `bootstrap_ci.py` | `multi/bootstrap.json` |

`sases_eval/reproduce.py` runs every step in order (`--report` rebuilds only
summaries, figures and the PDF). Two environments: `.venv` (Python 3.8,
`requirements-rerun.txt`) for the audits and `.venv-torch` (Python 3.11,
PyTorch CPU, numpy, scipy, matplotlib) for `pde_surrogates.py`. The report
scripts use the Times New Roman fonts in `C:/Windows/Fonts`.

**Data.** Processed records (`wind/**/records.npz`, `pv/records.npz`,
`multi/*_records.npz`) are committed, so every audit reruns without the raw
archives. To rebuild them, download into `external_data/` (not committed):
Kelmarsh and Penmanshiel SCADA (Cubico, Zenodo 16807551 and 16807304,
CC-BY-4.0), Hill of Towie 2019 (RES, Zenodo 22662930, CC-BY-4.0), La Haute
Borne (ENGIE, Etalab Open Licence 2.0, via NREL OpenOA), and PVDAQ systems
9068 and 2107 (NREL, OEDI 2023 Solar Data Prize). Row-level caches (`*.pkl`)
and trained PDE models (`pde/models/*.pt`) are regenerated by the scripts;
PDE training is deterministic.
