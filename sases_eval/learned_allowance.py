"""Learned law allowances: NN and KAN against the formula rules.
Protocol: LEARNED_ALLOWANCE_PROTOCOL.md.

  python learned_allowance.py dev        wind 2016->2017, solar 2017->2018, 2017-18->2019
  python learned_allowance.py confirm    wind 2016-17->2018, solar 2017-19->2022-23

Reference rules (C, P, E1, E3) are rebuilt with the audits' own functions and gated
against wind/allowance.json and pv/premise.json before any learned rule is scored.
beta never reads the scored unit's own test-bin labels: fleet rules train on other
years, calibration-only rules on the unit's own TRAIN and LAWCAL bins.
"""
import hashlib
import json
import math
import pickle
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_dist
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

import allowance_audit as AA
import pv_audit as PA
from kan import KAN
from wind_paper_rule import kappa_fit as paper_kappa

warnings.filterwarnings('ignore')
HERE = Path(__file__).resolve().parent
OUT = HERE / 'learned'
ALPHA, FOLDS = 0.10, 5
AA.YEARS[2018] = HERE / 'wind' / '2018'
BANDS = {'wind': {'A': (8.5, 10.5), 'gap': (10.5, 11.5), 'B': (11.5, 14.5)},
         'pv': {'A': (550, 800), 'gap': (800, 900), 'B': (900, 1100)}}
Q_TH = {'wind': np.array([3.0, 1.0]), 'pv': np.array([1.0])}
FLEET = ['F0', 'F-lin', 'F-GBT', 'F-NN', 'F-KAN']
SEEDS = {'F-NN': (0, 1, 2), 'F-KAN': (0, 1, 2)}


def band_of(system, n):
    half = 0.25 if system == 'wind' else 25.0
    for k, (lo, hi) in BANDS[system].items():
        if lo <= n - half < hi:
            return k
    return None


# ------------------------------------------------------------------- tables
def unit_rows(system, name, year, c):
    """One row per bin above the ceiling: zeta, delta, features, formula betas."""
    q, top = AA.ceiling_line(c)
    lab = sorted(c.band('TRAIN') + c.band('LAWCAL'), key=lambda n: c.TP[n])
    x = np.array([c.lp[n] for n in lab]); Y = np.array([c.TM[n] for n in lab])
    curv = [np.polyfit(x, Y[:, j], 2)[0] for j in range(Y.shape[1])]
    lc = c.band('LAWCAL')
    rms = float(np.sqrt(np.mean([np.sum((c.TM[n] - (c.TM[top] + q * (c.lp[n] - c.lp[top]))) ** 2)
                                 for n in lc])))
    k1 = AA.e1_kappa(c)[0]
    kp = 2 * paper_kappa(c, lc)
    kc = float(np.linalg.norm(q - Q_TH[system]))
    unit = dict(name=name, year=year, lab_x=x, lab_Y=Y, q=q, top_y=c.TM[top], top_u=c.lp[top], k1=k1)
    rows = []
    for n in c.names:
        d = c.lp[n] - c.lp[top]
        if d <= 0:
            continue
        if system == 'wind':
            f = [d, c.lp[n], q[0], q[1], c.TM[top][0], c.TM[top][1], curv[0], curv[1], k1, rms]
        else:
            mo = int(name[5:7])
            f = [d, c.lp[n], q[0], c.TM[top][0], curv[0], k1, rms,
                 math.sin(2 * math.pi * mo / 12), math.cos(2 * math.pi * mo / 12)]
        r = dict(unit=name, year=year, bin=float(n), band=band_of(system, n), delta=float(d),
                 u=float(c.lp[n]), zeta=AA.zeta(c, n), x=np.array(f, float),
                 C=kc * d, P=kp * d, E1=2 * k1 * d)
        if system == 'pv':
            r['S'] = 2 * k1 * d + 2 * max(0.0, math.log(c.TP[n] / PA.G_CLIP))
        rows.append(r)
    return unit, rows


def table(system, year):
    """Cached unit-bin table for one system-year."""
    OUT.mkdir(exist_ok=True)
    f = OUT / ('table_%s_%d.pkl' % (system, year))
    if f.exists():
        return pickle.loads(f.read_bytes())
    units, rows = {}, []
    if system == 'wind':
        for name, (t, m, c) in AA.units_of(year).items():
            units[name], rs = unit_rows('wind', name, year, c)
            rows += rs
    else:
        # One pass over every PV year; cache them all.
        per = {}
        for name, y, comb, c in PA.units():
            u, rs = unit_rows('pv', name, y, c)
            pu, pr = per.setdefault(y, ({}, []))
            pu[name] = u; pr += rs
        for y, v in per.items():
            (OUT / ('table_pv_%d.pkl' % y)).write_bytes(pickle.dumps(v))
        return per.get(year, ({}, []))
    f.write_bytes(pickle.dumps((units, rows)))
    return units, rows


# ----------------------------------------------------------- scale models
def make_model(kind, seed):
    if kind == 'F-lin':
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    if kind == 'F-GBT':
        return GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05,
                                         subsample=0.8, random_state=seed)
    if kind == 'F-NN':
        return make_pipeline(StandardScaler(), MLPRegressor((16, 16), alpha=1e-2, solver='lbfgs',
                                                           max_iter=5000, random_state=seed))
    if kind == 'F-KAN':
        return KAN((None, 4, 1), steps=3000, seed=seed)
    raise ValueError(kind)


def fit_scale(kind, seed, X, z):
    """Return sigma(.) fitted to ln ||zeta||. F0 is sigma = delta, no fit."""
    if kind == 'F0':
        return lambda X: X[:, 0]
    m = make_model(kind, seed)
    if kind == 'F-KAN':
        m.widths[0] = X.shape[1]
    m.fit(X, np.log(np.maximum(z, 1e-4)))
    lo, hi = max(float(z.min()), 1e-4), float(z.max())
    return lambda X, m=m: np.clip(np.exp(m.predict(X)), lo, hi)


def cv_plus(train, test, kind, seeds=(0,)):
    """Mondrian-by-band CV+ with normalised scores; folds grouped by unit.
    Returns {tag: beta} for each seed and, with several seeds, their ensemble
    (geometric mean of the fold's scales)."""
    X = np.stack([r['x'] for r in train]); z = np.array([r['zeta'] for r in train])
    band = np.array([r['band'] for r in train]); unit = np.array([r['unit'] for r in train])
    units = np.array(sorted(set(unit)))
    np.random.default_rng(0).shuffle(units)
    folds = np.array_split(units, FOLDS)
    Xt = np.stack([r['x'] for r in test]); bt = np.array([r['band'] for r in test])
    tags = [kind if sd == 0 else '%s#%d' % (kind, sd) for sd in seeds]
    if len(seeds) > 1:
        tags.append(kind + '-ens')
    V = {t: [[] for _ in test] for t in tags}
    for fu in folds:
        hold = np.isin(unit, fu)
        sigs = [fit_scale(kind, sd, X[~hold], z[~hold]) for sd in seeds]
        sh = [f(X[hold]) for f in sigs]; st = [f(Xt) for f in sigs]
        if len(seeds) > 1:
            sh.append(np.exp(np.mean(np.log(sh), 0))); st.append(np.exp(np.mean(np.log(st), 0)))
        sb = band[hold]
        for t, h, tt in zip(tags, sh, st):
            s = z[hold] / h
            for b in set(bt):
                sc = s[sb == b]
                for i in np.where(bt == b)[0]:
                    V[t][i].append(tt[i] * sc)
    out = {}
    for t in tags:
        beta = np.empty(len(test))
        for i, v in enumerate(V[t]):
            v = np.concatenate(v); n = len(v); k = math.ceil((1 - ALPHA) * (n + 1))
            beta[i] = np.partition(v, k - 1)[k - 1] if k <= n else math.inf
        out[t] = beta
    return out


def e3(train, test):
    pool = {}
    for r in train:
        pool.setdefault(r['bin'], []).append(r['zeta'])
    return np.array([AA.conformal_upper(np.array(pool.get(r['bin'], []))) for r in test])


# ------------------------------------------------- calibration-only learned
def calib_only(units, test, kind):
    """beta = max(E1, 2 ||g(u_t) - c(u_t)||), g an NN or KAN fit to the unit's 8 labelled bins."""
    cache = {}
    out = np.empty(len(test))
    for i, r in enumerate(test):
        U = units[r['unit']]
        if r['unit'] not in cache:
            xs = (U['lab_x'] - U['lab_x'].mean()) / U['lab_x'].std()
            gs = []
            for j in range(U['lab_Y'].shape[1]):
                if kind == 'A-NN':
                    m = MLPRegressor((16,), activation='tanh', alpha=1e-2, solver='lbfgs',
                                     max_iter=5000, random_state=0).fit(xs[:, None], U['lab_Y'][:, j])
                    gs.append(lambda u, m=m: m.predict(u[:, None]))
                else:
                    m = KAN((1, 3, 1), steps=1500, seed=0).fit(xs[:, None], U['lab_Y'][:, j])
                    gs.append(lambda u, m=m: m.predict(u[:, None]))
            cache[r['unit']] = (gs, U['lab_x'].mean(), U['lab_x'].std())
        gs, mu, sd = cache[r['unit']]
        us = np.array([(r['u'] - mu) / sd])
        g = np.array([gj(us)[0] for gj in gs])
        centre = U['top_y'] + U['q'] * r['delta']
        out[i] = max(r['E1'], 2 * float(np.linalg.norm(g - centre)))
    return out


# -------------------------------------------------------------- evaluation
def cp(k, n):
    lo = 0.0 if k <= 0 else float(beta_dist.ppf(.025, k, n - k + 1))
    hi = 1.0 if k >= n else float(beta_dist.ppf(.975, k + 1, n - k))
    return [lo, hi]


def cert_rows(system, year):
    if system == 'wind':
        rows = json.loads((AA.YEARS[year] / 'results.json').read_text())['rows']
        return [(r['unit'], float(r['bin']), r['raw_defect'], r['e']) for r in rows]
    f = HERE / 'pv' / ('cert_%d.json' % year)
    if not f.exists():
        return None
    return [(r['unit'], float(r['bin']), r['D'], r['e']) for r in json.loads(f.read_text())['rows']]


def score(test, betas, certs):
    out = {}
    z = np.array([r['zeta'] for r in test]); sc = np.array([r['band'] for r in test])
    key = {(r['unit'], r['bin']): i for i, r in enumerate(test)}
    for s in ('A', 'B'):
        m = sc == s
        if not m.any():
            continue
        out[s] = {}
        for rule, b in betas.items():
            b = np.asarray(b)[m]; zz = z[m]; fin = np.isfinite(b)
            cov = zz <= b + 1e-10
            o = dict(unit_bins=int(m.sum()), premise=float(cov.mean()), premise_ci=cp(int(cov.sum()), len(cov)),
                     committed=float(cov[fin].mean()) if fin.any() else None,
                     committed_ci=cp(int(cov[fin].sum()), int(fin.sum())) if fin.any() else None,
                     abstain=float(1 - fin.mean()),
                     tightness=float(np.median(b[fin] / np.maximum(zz[fin], 1e-12))) if fin.any() else None)
            if certs:
                bfull = np.asarray(betas[rule])
                rs = [(bfull[key[(u, n)]], z[key[(u, n)]], D, e) for u, n, D, e in certs
                      if (u, n) in key and sc[key[(u, n)]] == s]
                if rs:
                    bb, zz2, D, e = map(np.array, zip(*rs))
                    S = np.maximum(D - bb, 0.0); val = S <= e + 1e-9; prem = zz2 <= bb + 1e-10
                    assert not np.any(prem & ~val), 'Proposition 1 violated'
                    o.update(rows=len(rs), validity=float(val.mean()), validity_ci=cp(int(val.sum()), len(val)),
                             median_S_over_e=float(np.median(S / e)), silent=float(np.mean(S <= 0.01)),
                             fails_with_premise=int(np.sum(prem & ~val)))
            out[s][rule] = o
    return out


# ------------------------------------------------------------------ gates
def gate_wind_2017(test, betas):
    stored = json.loads((HERE / 'wind/allowance.json').read_text())['confirmation_2017']
    sc = np.array([r['band'] for r in test]); z = np.array([r['zeta'] for r in test])
    for s in ('A', 'B'):
        m = sc == s
        for rule in ('C', 'P', 'E1', 'E3'):
            got = float(np.mean(z[m] <= np.asarray(betas[rule])[m] + 1e-10))
            assert abs(got - stored[s][rule]['premise']) < 1e-12, (s, rule, got, stored[s][rule]['premise'])
    print('gate: wind 2017 C/P/E1/E3 reproduce wind/allowance.json', flush=True)


def gate_pv(test, betas, year):
    prem = {(r['unit'], r['bin']): r for r in json.loads((HERE / 'pv/premise.json').read_text())['rows']
            if r['year'] == year}
    n = 0
    for i, r in enumerate(test):
        p = prem.get((r['unit'], r['bin']))
        if p is None:
            continue
        n += 1
        for rule, key in (('C', 'beta_C'), ('P', 'beta_P'), ('E1', 'beta_E1'), ('S', 'beta_S')):
            assert abs(betas[rule][i] - p[key]) < 1e-9, (rule, r['unit'], r['bin'])
        assert abs(r['zeta'] - p['zeta']) < 1e-12
    assert n == sum(1 for r in test if r['band'] in ('A', 'B'))
    print('gate: solar %d C/P/E1/S and zeta reproduce pv/premise.json on %d unit-bins' % (year, n), flush=True)


# ------------------------------------------------------------------- runs
def run_pool(system, train_years, test_year, with_calib_only=True):
    """test_year may be a list: years sharing one training pool are scored in one pass
    (each test bin's beta depends on the training pool only) and reported per year."""
    if isinstance(test_year, (list, tuple)):
        t0 = time.time()
        units, allrows = {}, []
        for y in test_year:
            u, r = table(system, y); units.update(u); allrows += r
        o = run_pool.__wrapped__(system, train_years, test_year, units, allrows, with_calib_only, t0)
        return o
    units, allrows = table(system, test_year)
    return run_pool.__wrapped__(system, train_years, [test_year], units, allrows, with_calib_only, time.time())[0]


def _run_pool(system, train_years, test_years, units, allrows, with_calib_only, t0):
    test_year = test_years[0] if len(test_years) == 1 else test_years
    train = [r for y in train_years for r in table(system, y)[1]]
    # A unit enters a scenario only with at least two test bins there (wind_audit, pv_audit).
    count = {}
    for r in allrows:
        count[(r['unit'], r['band'])] = count.get((r['unit'], r['band']), 0) + 1
    test = [r for r in allrows if r['band'] in ('A', 'B') and count[(r['unit'], r['band'])] >= 2]
    betas = {k: np.array([r[k] for r in test]) for k in (('C', 'P', 'E1') + (('S',) if system == 'pv' else ()))}
    betas['E3'] = e3(train, test)
    betas['Z'] = np.array([np.linalg.norm(units[r['unit']]['q']) * r['delta'] for r in test])
    if system == 'wind' and test_year == 2017 and train_years == [2016]:
        gate_wind_2017(test, betas)
    if system == 'pv':
        for y in test_years:
            m = [i for i, r in enumerate(test) if r['year'] == y]
            gate_pv([test[i] for i in m], {k: np.asarray(v)[m] for k, v in betas.items()}, y)
    with threadpool_limits(limits=1):
        for kind in FLEET:
            betas.update(cv_plus(train, test, kind, SEEDS.get(kind, (0,))))
            print('  %s %s->%s %-9s %.0fs' % (system, train_years, test_year, kind, time.time() - t0), flush=True)
        if with_calib_only:
            for kind in ('A-NN', 'A-KAN'):
                betas[kind] = calib_only(units, test, kind)
                print('  %s %s->%s %-9s %.0fs' % (system, train_years, test_year, kind, time.time() - t0), flush=True)
    out = []
    for y in test_years:
        m = np.array([r['year'] == y for r in test])
        ty = [r for r in test if r['year'] == y]
        by = {k: np.asarray(v)[m] for k, v in betas.items()}
        out.append(dict(system=system, train=train_years, test=y, n_train=len(train),
                        n_train_units=len({r['unit'] for r in train}), results=score(ty, by, cert_rows(system, y)),
                        betas={k: v.tolist() for k, v in by.items()},
                        test_keys=[(r['unit'], r['bin'], r['band'], r['zeta'], r['delta']) for r in ty]))
    return out


run_pool.__wrapped__ = _run_pool


def show(o):
    print('\n%s  train %s -> test %d   (%d training unit-bins from %d units)'
          % (o['system'].upper(), o['train'], o['test'], o['n_train'], o['n_train_units']))
    for s, res in o['results'].items():
        print(' scenario %s' % s)
        hdr = '  %-10s %8s %15s %9s %7s %8s %8s %8s %7s' % ('rule', 'premise', '95% CI', 'commit', 'abst',
                                                            'beta/z', 'valid', 'S/e', 'silent')
        print(hdr)
        for rule, v in res.items():
            print('  %-10s %8.3f %15s %9s %6.0f%% %8s %8s %8s %7s'
                  % (rule, v['premise'], '[%.3f,%.3f]' % tuple(v['premise_ci']),
                     '--' if v['committed'] is None else '%.3f' % v['committed'], 100 * v['abstain'],
                     '--' if v['tightness'] is None else '%.2f' % v['tightness'],
                     '%.3f' % v['validity'] if 'validity' in v else '--',
                     '%.3f' % v['median_S_over_e'] if 'validity' in v else '--',
                     '%.3f' % v['silent'] if 'validity' in v else '--'))


def main(mode):
    pools = {'dev': [('wind', [2016], 2017), ('pv', [2017], 2018), ('pv', [2017, 2018], 2019)],
             'confirm': [('wind', [2016, 2017], 2018), ('pv', [2017, 2018, 2019], [2022, 2023])]}[mode]
    out = []
    for system, tr, te in pools:
        o = run_pool(system, tr, te)
        for x in (o if isinstance(o, list) else [o]):
            show(x)
            out.append(x)
    data = dict(mode=mode, pools=out, alpha=ALPHA, folds=FOLDS,
                protocol_sha256=hashlib.sha256((HERE / 'LEARNED_ALLOWANCE_PROTOCOL.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                kan_sha256=hashlib.sha256((HERE / 'kan.py').read_bytes()).hexdigest())
    (OUT / ('%s.json' % mode)).write_text(json.dumps(data, indent=1, allow_nan=True))
    print('\n-> learned/%s.json' % mode)


if __name__ == '__main__':
    main(sys.argv[1])
