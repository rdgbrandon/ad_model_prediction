# Capillary Lab

A local website to rebuild the supplied dataset, run the scientific Python
pipeline, inspect spectra and compare error certificates. No Node dependencies,
frontend build step, external fonts, CDN, or remote service is required.

## Start

From the repository root:

```powershell
.\.venv\Scripts\python.exe web/server.py
```

Open **http://127.0.0.1:8765**. Or run `web/start.ps1`. Keep the terminal running;
Ctrl+C stops the server. Use `--port 8766` if the default port is occupied.
For a fresh installation create `.venv` and install
`sases_eval/requirements-rerun.txt` using Python 3.8-compatible dependencies.
The checked-in dashboard snapshot can be served immediately with standard Python;
running experiments requires the scientific dependencies in that environment.

## Run buttons

- **Refresh the audits:** retrain seven small model/seed variants for the
  ceiling-centred audit, rerun mechanism checks, publish the new dashboard snapshot.
- **Rebuild + evaluate:** additionally decode the local HDF5 and compile Welch
  spectra into `sases_eval/spec.npz` before auditing.
- **Full reproduction:** rebuild and run the older LOTO comparison pipeline as
  well, regenerate both earlier PDF reports, then run the new ceiling audit.
  Usually takes several minutes. The model-specific LOTO refits dominate time.

Jobs are serialized. The runner uses an allowlist of Python scripts, never shell
commands supplied by the browser. It binds only to localhost, checks Host/Origin
and a request header, and exposes only listed artifacts. Each script has a
30-minute timeout. Do not expose this development server to the internet.

The live dashboard snapshot is replaced atomically only after successful work.
Pipeline scripts update their working artifacts in place, so a failed job may
leave partial working outputs even though the last published dashboard is kept.
Downloads refer to working artifacts; use the snapshot's embedded results for
the last published view if a run fails. Existing historical reports remain
available; the PDF download is explicitly labelled as the prior mechanism report.

## Scientific interpretation

The new score is distance from the prediction to a ball centred on the labelled
calibration ceiling extrapolated with the fitted slope. Its radius retains the
previous fixed growth rate. It uses no test labels, requires an already-labelled
calibration ceiling, and drops the prior heuristic anchor-error subtraction.
The reverse-triangle bound is conditional on target-tube coverage. This differs
from the older anchor-law-residual coverage metric; neither is population-validated.

The site also shows the newer multi-rule score: a separate rule is fitted on
every subset of at least three calibration trials and the strongest resulting
bound is reported. That comparison can never come out negative, because the
single full-calibration rule is one of the candidates. Its gain is modest and
model-dependent (linear 0.742 -> 0.781; larger network run 1, 0.110 -> 0.154;
small network unchanged), comes from subset selection rather than the weighted
blend, and is structurally impossible at the 146 mW ceiling, which has only one
eligible subset. It also assumes the target lies in every selected ball at once.
The page states each of these next to the numbers. See
`sases_eval/consensus/FINDINGS.md`.

Canonical 192 mW, MLP(8), seed 0: mean S/e rises from 0.298 (LOTO anchor) and
0.747 (labelled anchor) to 0.809 (labelled ceiling). Three of three test tubes
cover, giving a nominal one-sided 95% CP lower bound of 0.368. The 146 mW
configuration has four test trials and bound 0.473. Both use an already-viewed
corpus and uncertain drive-to-flux coupling. No score threshold or rate was
optimized on the new audit. See `sases_eval/CEILING_PROTOCOL.md`.

The radius slider is a hypothetical geometric illustration only. It does not
change the fixed candidate, rerun a model, or change the measured result tables.
Colours in the corpus plot correspond to the currently selected canonical split.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s sases_eval -p test_ceiling_audit.py -v
.\.venv\Scripts\python.exe -m unittest discover -s sases_eval -p test_consensus_audit.py -v
.\.venv\Scripts\python.exe -m unittest discover -s web -p test_server.py -v
node --check web/app.js
node web/test_frontend.cjs
```

The last test requires the local server. It executes the real JS with a minimal
DOM and live API, checks all result selections and slider extrema. It does not
replace visual browser inspection. Browser automation was unavailable in the
creation session. The CSS includes desktop and narrow-screen layouts.
