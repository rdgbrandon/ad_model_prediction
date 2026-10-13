"""Data-driven expansions of the law allowance. Protocol: ALLOWANCE_PROTOCOL.md.

2016 is the development year (exploratory); 2017 is the confirmation year.
beta never reads the scored unit's own test-bin labels. S = max(D - beta, 0)
on the stored raw defect D, centred on the LAWCAL ceiling exactly as before.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist

import wind_audit as W
from wind_paper_rule import kappa_fit as paper_kappa

HERE = Path(__file__).resolve().parent
ALPHA = 0.10
YEARS = {2016: HERE / 'wind', 2017: HERE / 'wind' / '2017'}
RULES = ['C', 'P', 'E1', 'E2', 'E3']
NAMES = {'C': 'C  ceiling theory-distance (primary run)',
         'P': "P  paper Eq.5, 2 x short-hop kappa'",
         'E1': "E1 long-hop kappa' (calibration labels)",
         'E2': 'E2 E1 + extrapolated curvature',
         'E3': 'E3 fleet-calibrated, conformal 90%'}


def units_of(year):
    rec = np.load(YEARS[year] / 'records.npz')
    out = {}
    for t in sorted(set(rec['turbine'].tolist())):
        for m in sorted(set(rec['month'].tolist())):
            s = (rec['turbine'] == t) & (rec['month'] == m)
            c = W.Unit(rec['U'][s], rec['P'][s], rec['omega'][s])
            if len(c.band('TRAIN')) == 4 and len(c.band('LAWCAL')) == 4:
                out['T%d-%02d' % (t, m)] = (t, m, c)
    return out


def ceiling_line(c):
    lc = c.band('LAWCAL')
    return c.slopes(lc), max(lc, key=lambda n: c.TP[n])


def zeta(c, n):
    q, top = ceiling_line(c)
    return float(np.linalg.norm(c.TM[n] - (c.TM[top] + q * (c.lp[n] - c.lp[top]))))


def e1_kappa(c):
    lab = sorted(c.band('TRAIN') + c.band('LAWCAL'), key=lambda n: c.TP[n])
    ratios = []
    for i in range(len(lab) - 3):
        fit = lab[i:i + 4]
        q = c.slopes(fit); top = fit[-1]
        for n in lab[i + 4:]:
            d = c.lp[n] - c.lp[top]
            ratios.append(np.linalg.norm(c.TM[n] - (c.TM[top] + q * d)) / d)
    return float(max(ratios)), len(ratios)


def e2_curvature(c, n):
    lab = sorted(c.band('TRAIN') + c.band('LAWCAL'), key=lambda n: c.TP[n])
    x = np.array([c.lp[k] for k in lab]); Y = np.array([c.TM[k] for k in lab])
    quad = np.array([np.polyval(np.polyfit(x, Y[:, j], 2), c.lp[n]) for j in range(Y.shape[1])])
    q, top = ceiling_line(c)
    return float(np.linalg.norm(quad - (c.TM[top] + q * (c.lp[n] - c.lp[top]))))


def conformal_upper(scores):
    n = len(scores)
    k = math.ceil((n + 1) * (1 - ALPHA))
    return float(np.sort(scores)[k - 1]) if k <= n else float('inf')


def cp(k, n):
    lo = 0.0 if k <= 0 else float(beta_dist.ppf(.025, k, n - k + 1))
    hi = 1.0 if k >= n else float(beta_dist.ppf(.975, k + 1, n - k))
    return lo, hi


def evaluate(year, fleet):
    """fleet: unit -> {bin: zeta} for the units E3 may calibrate on."""
    units = units_of(year)
    rows = json.loads((YEARS[year] / 'results.json').read_text())['rows']
    k1 = {u: e1_kappa(v[2]) for u, v in units.items()}
    kp = {u: 2 * paper_kappa(v[2], v[2].band('LAWCAL')) for u, v in units.items()}
    cache, out = {}, {}
    for scen in ('A', 'B'):
        rs = [r for r in rows if r['scenario'] == scen]
        res = {}
        for rule in RULES:
            prem_ub, rec = {}, []
            for r in rs:
                t, m, c = units[r['unit']]
                key = (r['unit'], r['bin'])
                if key not in cache:
                    cache[key] = zeta(c, r['bin'])
                z, d = cache[key], r['delta']
                if rule == 'C':
                    b = r['radius']
                elif rule == 'P':
                    b = kp[r['unit']] * d
                elif rule == 'E1':
                    b = 2 * k1[r['unit']][0] * d
                elif rule == 'E2':
                    b = max(2 * k1[r['unit']][0] * d, 2 * e2_curvature(c, r['bin']))
                else:
                    pool = [zz[r['bin']] for uu, zz in fleet(r['unit'], t, m).items()
                            if r['bin'] in zz]
                    b = conformal_upper(np.array(pool))
                S = max(r['raw_defect'] - b, 0.0)
                prem_ub[key] = z <= b + 1e-10
                rec.append((prem_ub[key], S <= r['e'] + 1e-9, S / r['e'], S <= 0.01,
                            math.isinf(b), r['unit']))
            p = np.array([x[0] for x in rec]); v = np.array([x[1] for x in rec])
            kcov, ncov = sum(prem_ub.values()), len(prem_ub)
            unit_ok = {}
            for x in rec:
                unit_ok[x[5]] = unit_ok.get(x[5], True) and x[1]
            res[rule] = dict(
                unit_bins=ncov, premise=kcov / ncov, premise_ci=cp(kcov, ncov),
                rows=len(rec), validity=float(v.mean()),
                fails_with_premise=int((p & ~v).sum()),
                validity_given_premise=float(v[p].mean()) if p.any() else None,
                units_valid_every_row=int(sum(unit_ok.values())), units=len(unit_ok),
                median_S_over_e=float(np.median([x[2] for x in rec])),
                silent=float(np.mean([x[3] for x in rec])),
                infinite_beta=float(np.mean([x[4] for x in rec])))
        out[scen] = res
    return out, {u: v[0] for u, v in k1.items()}


def zetas(year):
    """unit -> {bin: zeta} over every bin above the ceiling."""
    z = {}
    for u, (t, m, c) in units_of(year).items():
        q, top = ceiling_line(c)
        z[u] = {n: zeta(c, n) for n in c.names if c.lp[n] > c.lp[top]}
    return z


def run():
    z16 = zetas(2016)
    tm16 = {u: (int(u[1]), int(u[3:])) for u in z16}
    # 2016, development: calibrate on units sharing neither turbine nor month.
    dev, k16 = evaluate(2016, lambda u, t, m: {v: zz for v, zz in z16.items()
                                               if tm16[v][0] != t and tm16[v][1] != m})
    # 2017, confirmation: calibrate on every 2016 unit.
    conf, k17 = evaluate(2017, lambda u, t, m: z16)
    data = dict(development_2016=dev, confirmation_2017=conf, alpha=ALPHA,
                e1_kappa_2016=k16, e1_kappa_2017=k17,
                protocol_sha256=hashlib.sha256((HERE / 'ALLOWANCE_PROTOCOL.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (HERE / 'wind' / 'allowance.json').write_text(json.dumps(data, indent=1, allow_nan=True))
    for label, res in (('2016 - DEVELOPMENT (exploratory: residuals already seen)', dev),
                       ('2017 - CONFIRMATION (untouched year)', conf)):
        print('\n' + '=' * 104 + '\n' + label + '\n' + '=' * 104)
        for scen, name in (('A', 'A: 8.5-10.5 m/s, below rated'), ('B', 'B: 11.5-14.5 m/s, rated')):
            print('\nscenario %s' % name)
            hdr = ('%-42s%9s%17s%9s%9s%10s%9s%8s%7s'
                   % ('rule', 'premise', '95% CI', 'valid', 'units', 'fail|prem', 'S/e med',
                      'silent', 'inf'))
            print(hdr); print('-' * len(hdr))
            for rule in RULES:
                o = res[scen][rule]
                print('%-42s%9.3f%17s%9.3f%9s%10d%9.3f%8.3f%7.3f'
                      % (NAMES[rule], o['premise'], '[%.3f, %.3f]' % tuple(o['premise_ci']),
                         o['validity'], '%d/%d' % (o['units_valid_every_row'], o['units']),
                         o['fails_with_premise'], o['median_S_over_e'], o['silent'],
                         o['infinite_beta']))
    print('\npremise: share of unit-bins whose law residual beta covered (model-independent).')
    print('valid: share of rows with S <= e. units: units valid on every row. fail|prem: bound')
    print('failures on rows where the premise held - Proposition 1 says this must be 0.')
    print('inf: share of rows where E3 had fewer than 9 calibration units and abstained.')


if __name__ == '__main__':
    run()
