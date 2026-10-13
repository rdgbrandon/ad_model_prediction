# Current week-3 follow-up

Read [report.txt](week3_followup/report.txt) or
[the three-page PDF](week3_followup/sases_week3_followup.pdf).
These supersede the baseline comparison in the historical week-3 PDF and
predictors/report.txt. Historical numerical outputs are preserved.

- Equal-label rerun: 399 rows, four distinct physical test trials. Strict
  conformal and scalar-error jackknife+ intervals have infinite upper endpoints
  with only 3-4 calibration trials. No sample-maximum clipping is used.
- Equal-label heuristic rank correlations: calibration maximum 0.878; linear
  error regression 0.838; historical SASES consensus 0.790; raw defect 0.777.
  The claim that SASES ranks errors best is not supported by this comparison.
- [Derivation](LAW_RATE_DERIVATION.md): the allowance follows conditionally
  from flux elasticity and bounded spectral departures. Those physical bounds
  have not been independently established. Shape-only targets have ideal slope
  zero; the corrected premise passes all existing endpoints. Piston needs a
  separate physical argument.
- [New-data manifest and acquisition status](external_trials/README.md): a
  distinct 2025 measurement collection was located. No new trials were scored;
  small CSV access is blocked by large archives without byte-range support.

Validation: all seven new tests passed. The 399 refitted surrogate errors,
historical SASES scores and raw defects match the old predictor audit exactly.
All three PDF pages were rendered and visually checked.

From the workspace root:

```powershell
.\.venv\Scripts\python.exe sases_eval\fair_baselines_audit.py
.\.venv\Scripts\python.exe sases_eval\theory_rate_audit.py
.\.venv\Scripts\python.exe sases_eval\discover_physical_trials.py
.\.venv\Scripts\python.exe sases_eval\followup_report.py
.\.venv\Scripts\python.exe -m unittest discover -s sases_eval -p test_fair_baselines.py -v
```
