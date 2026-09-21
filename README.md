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
