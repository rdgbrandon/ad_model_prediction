"""Tables and verdicts for the PV clean-law test. Reads pv/*.json only."""
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist

HERE = Path(__file__).resolve().parent
P = json.loads((HERE / 'pv/premise.json').read_text())
ROWS = P['rows']
RULES = ['C', 'P', 'E1', 'S', 'E3_prev', 'E3_loyo']
NAMES = {'C': "C   ceiling theory-distance", 'P': "P   paper Eq.5 (short-hop kappa')",
         'E1': "E1  long-hop kappa'", 'S': 'S   spec sheet (E1 + clipping)',
         'E3_prev': 'E3  fleet, previous year', 'E3_loyo': 'E3  fleet, leave-year-out [dev]'}


def cp(k, n):
    lo = 0.0 if k <= 0 else float(beta_dist.ppf(.025, k, n - k + 1))
    hi = 1.0 if k >= n else float(beta_dist.ppf(.975, k + 1, n - k))
    return '[%.3f, %.3f]' % (lo, hi)


def rule(n):
    print('-' * n)


print('CLEAN-LAW TEST: PV DC CURRENT vs PLANE-OF-ARRAY IRRADIANCE (PVDAQ 9068)')
print('law ln I = 1 x ln G; clipping onset from the spec sheet G_clip = %.0f W/m2' % P['g_clip'])
print('%d test bins from %d combiner-months; years %s'
      % (len(ROWS), len({r['unit'] for r in ROWS}), sorted({r['year'] for r in ROWS})))
qs = np.array([r['q'] for r in ROWS if r['scenario'] == 'A'])
print('fitted LAWCAL slope q: median %.3f, IQR %.3f-%.3f (theory 1)'
      % (np.median(qs), *np.percentile(qs, [25, 75])))

for scen, label in (('A', 'A: 550-800 W/m2, below clipping - the law should hold'),
                    ('B', 'B: 900-1100 W/m2, above the spec-sheet clipping onset')):
    rs = [r for r in ROWS if r['scenario'] == scen]
    z = np.array([r['zeta'] for r in rs])
    print('\n' + '=' * 100 + '\nSCENARIO ' + label + '\n' + '=' * 100)
    print('%d unit-bins from %d combiner-months. Law residual ||zeta||: median %.4f, 90th pct %.4f'
          % (len(rs), len({r['unit'] for r in rs}), np.median(z), np.percentile(z, 90)))
    print('(log units: 0.01 = a 1%% departure of current from proportionality)')
    hdr = '%-36s%9s%18s%13s%14s%9s' % ('allowance rule', 'premise', '95% CI', 'beta/zeta',
                                       'median beta', 'inf')
    print(hdr); rule(len(hdr))
    for ru in RULES:
        cov = np.array([r['covered_' + ru] for r in rs])
        b = np.array([r['beta_' + ru] for r in rs])
        fin = np.isfinite(b)
        ratio = np.median(b[fin] / np.maximum(z[fin], 1e-12)) if fin.any() else float('nan')
        print('%-36s%9.3f%18s%13.2f%14.4f%9.3f'
              % (NAMES[ru], cov.mean(), cp(int(cov.sum()), len(cov)), ratio,
                 np.median(b[fin]) if fin.any() else float('nan'), 1 - fin.mean()))
    print('\n  coverage by year (unit-bins):')
    for ru in ('C', 'P', 'E1', 'S', 'E3_loyo'):
        cells = []
        for y in sorted({r['year'] for r in rs}):
            ry = [r for r in rs if r['year'] == y]
            cells.append('%d %.2f (n=%d)' % (y, np.mean([r['covered_' + ru] for r in ry]), len(ry)))
        print('    %-5s %s' % (ru, '  '.join(cells)))
    print('\n  coverage by combiner, rule E1 (24 combiners):')
    combs = sorted({r['combiner'] for r in rs})
    vals = [np.mean([r['covered_E1'] for r in rs if r['combiner'] == c]) for c in combs]
    print('    min %.2f  median %.2f  max %.2f   combiners >= 0.90: %d/%d'
          % (min(vals), np.median(vals), max(vals), sum(v >= .9 for v in vals), len(vals)))

for year in (2019, 2018):
    f = HERE / 'pv' / ('cert_%d.json' % year)
    if not f.exists():
        print('\n[cert_%d.json not yet available]' % year)
        continue
    C = json.loads(f.read_text())['rows']
    tag = 'declared' if year == 2019 else 'ADDED (PV_DEVIATIONS.md)'
    print('\n' + '=' * 100 + '\nFULL CERTIFICATE, %d (%s): %d rows, %d units, %d surrogates'
          % (year, tag, len(C), len({r['unit'] for r in C}), len({r['model'] for r in C})))
    prem = {(r['unit'], r['bin']): r for r in ROWS if r['year'] == year}
    for scen in ('A', 'B'):
        cs = [r for r in C if r['scenario'] == scen]
        if not cs:
            continue
        print('\nscenario %s   median true error e = %.4f' % (scen, np.median([r['e'] for r in cs])))
        hdr = '%-36s%9s%9s%11s%10s%9s' % ('rule', 'premise', 'valid', 'fail|prem', 'S/e med', 'silent')
        print(hdr); rule(len(hdr))
        for ru in RULES:
            cov = np.array([prem[(r['unit'], r['bin'])]['covered_' + ru] for r in cs])
            S = np.array([r['S_' + ru] for r in cs]); e = np.array([r['e'] for r in cs])
            val = S <= e + 1e-9
            print('%-36s%9.3f%9.3f%11d%10.3f%9.3f'
                  % (NAMES[ru], cov.mean(), val.mean(), int((cov & ~val).sum()),
                     np.median(S / e), np.mean(S <= 0.01)))
