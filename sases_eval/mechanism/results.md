# Mechanism-checked results

The boundary correction is supported by new ablations and measured-interval checks. The specific KZ exponent is not identified by these data. This remains retrospective.

| Allowance | Pooled coverage | All-config trial success / CP lower | Mean S/e |
|---|---:|---:|---:|
| Boundary only | 0.164 | 0/3 / 0.000 | 0.390 |
| Fitted slope + boundary | 0.997 | 2/3 / 0.135 | 0.209 |
| KZ slope only | 0.296 | 0/3 / 0.000 | 0.402 |
| KZ slope + boundary | 1.000 | 3/3 / 0.368 | 0.240 |
| Reference 0 + boundary | 1.000 | 3/3 / 0.368 | 0.218 |
| Reference 1 + boundary | 1.000 | 3/3 / 0.368 | 0.260 |

Ceiling 146 mW: endpoint 4/4; measured-interval 4/4; maximum interval growth / allowance 0.741.

Ceiling 192 mW: endpoint 3/3; measured-interval 3/3; maximum interval growth / allowance 0.696.

22-split sweep: endpoint 29/29; measured-interval 29/29; maximum interval growth / allowance 0.696.

## Replacement claim

An explicit calibration-boundary residual plus a slope allowance repairs the failed origin-only envelope on this corpus. All measured secant-growth checks pass. The ablations support the boundary correction, while reference exponents 0, 0.5 and 1 are indistinguishable by coverage. These results establish a mechanism-supported retrospective case study, not 90% population coverage or validation of a unique weak-turbulence exponent.

## Reproduce

From the repository root:

```powershell
.\.venv\Scripts\python.exe sases_eval/mechanism_audit.py
.\.venv\Scripts\python.exe -m unittest discover -s sases_eval -p test_mechanism_audit.py -v
.\.venv\Scripts\python.exe sases_eval/report_mechanism.py
```

Raw artifacts: geometry.csv, ablations.csv, growth_checks.json, results.json. MECHANISM_PROTOCOL.md records the fixed diagnostics. The original rule and prior reports are unchanged.
