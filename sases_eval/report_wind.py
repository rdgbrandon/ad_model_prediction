"""Tables, intervals, paired tests and hypothesis verdicts for wind/results.json."""
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta, binom, spearmanr

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / 'wind/results.json').read_text())
R = D['rows']
METHODS = [('sases', 'SASES consensus', 'lower'),
           ('sample_max_heuristic', 'Calibration maximum', 'lower'),
           ('raw_defect', 'Raw defect', 'upper'),
           ('ols_error_heuristic', 'OLS error predictor', 'upper')]
LEVELS = [('unit', 'unit (turbine-month)'), ('turbine', 'turbine'), ('month', 'month')]


def cp(k, n, a=.05):
    lo = 0.0 if k <= 0 else float(beta.ppf(a / 2, k, n - k + 1))
    hi = 1.0 if k >= n else float(beta.ppf(1 - a / 2, k + 1, n - k))
    return '[%.3f, %.3f]' % (lo, hi)


def holds(r, key, side):
    return r[key] <= r['e'] + 1e-9 if side == 'lower' else r[key] >= r['e'] - 1e-9


def by(rows, level):
    out = {}
    for r in rows:
        out.setdefault(r[level], []).append(r)
    return out


def sign_p(a, b):
    """One-sided exact sign test that a beats b, over units where they differ."""
    s = sum(x and not y for x, y in zip(a, b)); c = sum(y and not x for x, y in zip(a, b))
    return (float(binom.sf(s - 1, s + c, .5)) if s + c else None), s, c


def rule(n):
    print('-' * n)


print('INDEPENDENT REPLICATION: KELMARSH WIND TURBINES (2016)')
print(D['citation'])
U = D['units']
print('units examined %d; entering scenario A: %d, scenario B: %d'
      % (len(U), sum(u['enters_A'] for u in U), sum(u['enters_B'] for u in U)))
print('rows: %d   surrogates per unit: %d   law exponents q_th = %s'
      % (len(R), len(D['models']), D['q_theory']))

for scen, label in (('A', 'A: 8.5-10.5 m/s, below rated, the law roughly holds'),
                    ('B', 'B: 11.5-14.5 m/s, rated region, the law fails')):
    rs = [r for r in R if r['scenario'] == scen]
    print('\n\n' + '=' * 100 + '\nSCENARIO ' + label + '\n' + '=' * 100)
    q = np.array([[r['q_P'], r['q_omega']] for r in rs])
    print('fitted law exponents on LAWCAL (median over units): q_P %.2f, q_omega %.2f '
          '(theory 3, 1)' % tuple(np.median(q, 0)))

    cov = np.array([r['covered'] for r in rs]); val = np.array([holds(r, 'sases', 'lower') for r in rs])
    print('\n-- premise against bound, row level (the H2 cross-tab) --')
    print('                       bound held   bound failed')
    print('  premise held      %10d   %12d' % ((cov & val).sum(), (cov & ~val).sum()))
    print('  premise failed    %10d   %12d' % ((~cov & val).sum(), (~cov & ~val).sum()))
    print('  premise coverage %.3f, validity %.3f, validity where premise held %s'
          % (cov.mean(), val.mean(), '%.3f' % val[cov].mean() if cov.any() else '--'))
    se = np.array([r['sases'] / r['e'] for r in rs])
    print('  median S/e %.3f   silent (S <= 0.01) %.3f   median e %.3f'
          % (np.median(se), np.mean([r['sases'] <= 0.01 for r in rs]),
             np.median([r['e'] for r in rs])))
    print('  (outputs are natural logs, so S = 0.01 is a 1% bound on power or speed)')

    print('\n-- every method, both readings --')
    hdr = '%-21s%-7s%9s%9s%10s%12s' % ('method', 'slide', 'below e', 'above e', 'score/e', 'rank rho')
    print(hdr); rule(len(hdr))
    for key, lab, side in METHODS:
        v = np.array([r[key] for r in rs]); e = np.array([r['e'] for r in rs])
        rho = []
        for grp in by(rs, 'unit').values():
            for b in set(r['bin'] for r in grp):
                g = [r for r in grp if r['bin'] == b]
                x = np.array([r[key] for r in g]); y = np.array([r['e'] for r in g])
                if len(g) > 2 and np.ptp(x) > 1e-12 and np.ptp(y) > 1e-12:
                    rho.append(spearmanr(x, y).correlation)
        print('%-21s%-7s%9.3f%9.3f%10.2f%12s'
              % (lab, side, np.mean(v <= e + 1e-9), np.mean(v >= e - 1e-9),
                 np.median(v / e), '%.3f' % np.mean(rho) if rho else 'cannot rank'))

    print('\n-- held on every row of a cluster, with 95% Clopper-Pearson --')
    hdr = '%-21s%-7s' % ('method', 'side') + ''.join('%24s' % lev for _, lev in LEVELS)
    print(hdr); rule(len(hdr))
    allheld = {}
    for key, lab, side in METHODS:
        cells = []
        for lev, _ in LEVELS:
            groups = by(rs, lev)
            h = {g: all(holds(r, key, side) for r in v) for g, v in groups.items()}
            allheld[(key, lev)] = h
            k = sum(h.values()); n = len(h)
            cells.append('%5s %s' % ('%d/%d' % (k, n), cp(k, n)))
        print('%-21s%-7s' % (lab, side) + ''.join('%24s' % c for c in cells))

    print('\n-- below-error rate per cluster (lower-bound reading for every method) --')
    for lev, levname in LEVELS[1:]:
        groups = by(rs, lev)
        print('  by %s:' % levname)
        for key, lab, _ in METHODS:
            rates = ['%.2f' % np.mean([r[key] <= r['e'] + 1e-9 for r in groups[g]])
                     for g in sorted(groups)]
            print('    %-21s %s' % (lab, '  '.join(rates)))

    print('\n-- paired sign tests, SASES against each competitor --')
    print('Two indicators: "held on every row of the cluster" (this project\'s convention,')
    print('each method on its slide side) and "higher below-error rate in the cluster".')
    hdr = '%-21s%-22s%-18s%14s%14s' % ('competitor', 'indicator', 'level', 'SASES/comp.', 'p one-sided')
    print(hdr); rule(len(hdr))
    for key, lab, side in METHODS[1:]:
        for lev, levname in LEVELS:
            a = allheld[('sases', lev)]; b = allheld[(key, lev)]
            p, s, c = sign_p([a[g] for g in a], [b[g] for g in a])
            print('%-21s%-22s%-18s%14s%14s' % (lab, 'held on every row', levname,
                                                '%d/%d' % (s, c), '--' if p is None else '%.2g' % p))
        for lev, levname in LEVELS:
            groups = by(rs, lev)
            ra = [np.mean([r['sases'] <= r['e'] + 1e-9 for r in groups[g]]) for g in sorted(groups)]
            rb = [np.mean([r[key] <= r['e'] + 1e-9 for r in groups[g]]) for g in sorted(groups)]
            p, s, c = sign_p([x > y for x, y in zip(ra, rb)], [y > x for x, y in zip(ra, rb)])
            print('%-21s%-22s%-18s%14s%14s' % ('', 'higher below rate', levname,
                                                '%d/%d' % (s, c), '--' if p is None else '%.2g' % p))
