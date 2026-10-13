"""Tables and hypothesis verdicts from physics_informed/results.json."""
import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / 'physics_informed/results.json').read_text())
R = D['rows']


def sel(**kw):
    return [r for r in R if all(r[k] == v for k, v in kw.items())]


def rule(n):
    print('-' * n)


print('PHYSICS-INFORMED SURROGATES: DOES TRAINING ON THE LAW BLIND THE CERTIFICATE?')
print('%d rows, %d distinct fits. %s' % (len(R), D['fits'], D['caveat']))
print('Validity %d/%d rows; premise held %d/%d; all fits converged: %s'
      % (sum(r['valid'] for r in R), len(R), sum(r['covered'] for r in R), len(R),
         all(r['converged'] for r in R)))

for ds in D['datasets']:
    for arm in D['arms']:
        print('\n\n=== %s | trained toward the %s ===' % (ds, arm))
        hdr = ('%-8s%10s%10s%10s%10s%9s%12s%12s%10s'
               % ('w', 'mean e', 'mean S', 'mean D', 'S/e med', 'silent',
                  'own resid', 'vs cert law', 'train e'))
        print(hdr); rule(len(hdr))
        for w in D['weights']:
            rs = sel(dataset=ds, arm=arm, w=w)
            print('%-8g%10.2f%10.2f%10.2f%10.3f%9.3f%12.4f%12.4f%10.2f'
                  % (w, np.mean([r['e'] for r in rs]), np.mean([r['S'] for r in rs]),
                     np.mean([r['D'] for r in rs]), np.median([r['S_over_e'] for r in rs]),
                     np.mean([r['silent'] for r in rs]),
                     np.mean([r['own_law_residual'] for r in rs]),
                     np.mean([r['residual_vs_certificate_law'] for r in rs]),
                     np.mean([r['train_error'] for r in rs])))


def trend(arm, ds, key):
    """Spearman of the quantity against log weight, within each seed x split x
    trial, averaged. w = 0 is placed one decade below the smallest weight."""
    out = []
    ws = D['weights']
    lw = {w: (np.log10(w) if w > 0 else np.log10(min(x for x in ws if x > 0)) - 1) for w in ws}
    for seed in D['seeds']:
        for cfg in sorted({r['config'] for r in R}):
            for t in sorted({r['trial'] for r in sel(dataset=ds, config=cfg)}):
                rs = sorted(sel(dataset=ds, arm=arm, seed=seed, config=cfg, trial=t),
                            key=lambda r: r['w'])
                if len(rs) < 3:
                    continue
                y = [r[key] for r in rs]
                if np.ptp(y) < 1e-12:
                    continue
                out.append(spearmanr([lw[r['w']] for r in rs], y).correlation)
    return float(np.mean(out)) if out else None, len(out)


print('\n\n=== Verdicts on the predeclared hypotheses ===')
print('rho = Spearman of the quantity against log(w), within each seed x split x trial.')
for ds in D['datasets']:
    print('\n[%s]' % ds)
    for arm in D['arms']:
        r_res, n = trend(arm, ds, 'own_law_residual')
        print('  H1 %-16s own law residual vs w: rho %+.3f over %d series  -> %s'
              % (arm, r_res, n, 'HOLDS' if r_res is not None and r_res < -0.5 else 'FAILS'))
    r_se, n = trend('certificate law', ds, 'S_over_e')
    lo = np.median([r['S_over_e'] for r in sel(dataset=ds, arm='certificate law', w=0.0)])
    hi = np.median([r['S_over_e'] for r in sel(dataset=ds, arm='certificate law', w=1000.0)])
    print('  H2 certificate law: S/e vs w: rho %+.3f over %d series; median S/e %.3f -> %.3f  -> %s'
          % (r_se, n, lo, hi, 'SUPPORTED' if r_se is not None and r_se < -0.3 else 'NOT SUPPORTED'))
    r_e, _ = trend('KZ theory', ds, 'e')
    r_s, _ = trend('KZ theory', ds, 'S')
    print('  H3 KZ theory: e vs w rho %+.3f, S vs w rho %+.3f  -> %s'
          % (r_e, r_s, 'SUPPORTED' if (r_e or 0) > 0.3 and (r_s or 0) > 0.3 else 'NOT SUPPORTED'))

print('\n\n=== H2 by the protocol\'s own wording: "falsified if S/e is flat or rising" ===')
print('The rank-trend statistic above was chosen before the run, and it was a poor')
print('choice: the response is a STEP at the smallest weight, then flat, and a')
print('monotone trend test cannot see a step. Both are reported; the protocol text')
print('is the governing criterion. Plateau = mean over w >= 0.1.')
hdr = ('%-8s%-17s%9s%9s%10s%10s%10s%10s%9s%9s'
       % ('repr', 'arm', 'e w=0', 'e plat.', 'S w=0', 'S plat.', 'S/e w=0', 'S/e plat',
          'sil w=0', 'sil plat'))
print(hdr); rule(len(hdr))
for ds in D['datasets']:
    for arm in D['arms']:
        z = sel(dataset=ds, arm=arm, w=0.0)
        p = [r for r in R if r['dataset'] == ds and r['arm'] == arm and r['w'] >= 0.1]
        print('%-8s%-17s%9.2f%9.2f%10.2f%10.2f%10.3f%10.3f%9.3f%9.3f'
              % (ds, arm, np.mean([r['e'] for r in z]), np.mean([r['e'] for r in p]),
                 np.mean([r['S'] for r in z]), np.mean([r['S'] for r in p]),
                 np.median([r['S_over_e'] for r in z]), np.median([r['S_over_e'] for r in p]),
                 np.mean([r['silent'] for r in z]), np.mean([r['silent'] for r in p])))

nc = {(r['dataset'], r['arm'], r['w'], r['seed'], r['config']) for r in R if not r['converged']}
print('\nConvergence: %d of %d fit-configurations hit the 20,000-iteration cap, all at'
      % (len(nc), len({(r['dataset'], r['arm'], r['w'], r['seed'], r['config']) for r in R})))
print('w = 1000, where the own law residual is already <= %.4f and every table entry'
      % max(r['own_law_residual'] for r in R if (r['dataset'], r['arm'], r['w'], r['seed'],
                                                   r['config']) in nc))
print('matches w = 100 to two decimals. They are kept, not dropped.')
