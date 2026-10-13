"""Does the certificate rank many surrogates correctly? n = 25, 50, 100 fits per unit.

A fixed pool of 100 surrogate configurations; n = 25 and 50 are nested random subsets.
Per dataset at most 60 units (seeded sample) and at most 400 TRAIN records per unit, so
the run fits in about half an hour. Rule K-S1, the law of MULTI_DATASET_PROTOCOL.md.

Scores ranked against the true error e, within each test bin:
  S    three-term total bound (anchor at the top training bin)
  Sc   measured-anchor form (b = 0)
  D    raw defect, no allowances
  cal  calibration maximum: the surrogate's largest error on the LAWCAL bins (trivial baseline)

  python ranking_audit.py run [names...]      -> ranking/<name>_rows.pkl
  python ranking_audit.py report              -> ranking/report.txt, results.json
"""
import json
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings('ignore')

import multi_audit as MA

HERE = Path(__file__).resolve().parent
OUT = HERE / 'ranking'
NAMES = ['capillary', 'kelmarsh', 'penmanshiel', 'lahauteborne', 'hilloftowie', 'pv9068', 'pv2107']
MAX_UNITS, MAX_TRAIN = 60, 400
SIZES = (9, 25, 50, 100)


def pool():
    """100 configurations: 16 classical, 84 MLPs."""
    cfg = [('poly', d) for d in (1, 2, 3)] + [('knn', k) for k in (3, 10, 30)]
    cfg += [('krr', g, a) for g in (0.3, 3.0) for a in (1e-3, 1e-1)]
    cfg += [('rf', d) for d in (3, 6, None)] + [('gbrt', d, lr) for d, lr in ((2, 0.1), (3, 0.1), (3, 0.05))]
    for h in ((8,), (16,), (32,), (16, 16), (32, 32), (64, 64), (8, 8, 8)):
        for act in ('tanh', 'relu'):
            for alpha in (1e-4, 1e-2):
                for seed in (0, 1, 2):
                    cfg.append(('mlp', h, act, alpha, seed))
    assert len(cfg) == 100
    return cfg


CFG = pool()
ORDER = list(np.random.default_rng(0).permutation(len(CFG)))      # nested subsets
NINE = None                                                         # n = 9: the first 9 of ORDER


def label(c):
    return '-'.join(str(x) for x in c)


def fit(c, U, Y):
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.kernel_ridge import KernelRidge
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.multioutput import MultiOutputRegressor
    from sklearn.neural_network import MLPRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler, PolynomialFeatures
    X = U[:, None]
    k = c[0]
    if k == 'poly':
        m = make_pipeline(StandardScaler(), PolynomialFeatures(c[1]), Ridge(alpha=1e-6))
    elif k == 'knn':
        m = KNeighborsRegressor(n_neighbors=min(c[1], len(X)))
    elif k == 'krr':
        m = make_pipeline(StandardScaler(), KernelRidge(kernel='rbf', gamma=c[1], alpha=c[2]))
    elif k == 'rf':
        m = RandomForestRegressor(n_estimators=100, max_depth=c[1], random_state=0)
    elif k == 'gbrt':
        m = MultiOutputRegressor(GradientBoostingRegressor(max_depth=c[1], learning_rate=c[2], random_state=0))
    else:
        m = make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=c[1], activation=c[2], alpha=c[3],
                                                         random_state=c[4], max_iter=2000, learning_rate_init=5e-3,
                                                         tol=1e-7, n_iter_no_change=100))
    m.fit(X, Y if Y.shape[1] > 1 else Y.ravel())
    out = Y.shape[1]
    return lambda V: np.asarray(m.predict(np.asarray(V, float)[:, None])).reshape(len(V), out)


def _job(args):
    name, uname, c = args
    from threadpoolctl import threadpool_limits
    q, top, kappa, line, capped, dstar = MA.law_parts(name, c)
    tests = {s: c.band(s) for s in ('A', 'B') if len(c.band(s)) >= 2}
    if not tests:
        return []
    U, Y = c.windows(c.band('TRAIN'))
    if len(U) > MAX_TRAIN:
        idx = np.random.default_rng(abs(hash(uname)) % 2 ** 32).choice(len(U), MAX_TRAIN, replace=False)
        U, Y = U[idx], Y[idx]
    aT = max(c.band('TRAIN'), key=lambda n: c.TP[n]); dT = c.lp[aT] - c.lp[top]
    lawcal = c.band('LAWCAL')
    bins = [t for v in tests.values() for t in v]
    scen = {t: s for s, v in tests.items() for t in v}
    rows = []
    with threadpool_limits(limits=1):
        for i, cf in enumerate(CFG):
            try:
                g = fit(cf, U, Y)
            except Exception:
                continue
            P = g(np.array([c.lp[t] for t in bins] + [c.lp[aT]] + [c.lp[n] for n in lawcal]))
            fT = P[len(bins)]
            cal = float(max(np.linalg.norm(P[len(bins) + 1 + j] - c.TM[n]) for j, n in enumerate(lawcal)))
            for k, t in enumerate(bins):
                d = c.lp[t] - c.lp[top]
                r = MA.cert(P[k], None if False else fT, c.TM[aT], c.TM[t], capped(d), capped(dT), 2 * kappa * min(d, dstar)) \
                    if False else None
                cx, cT = capped(d), capped(dT); beta = 2 * kappa * min(d, dstar)
                fx = P[k]; yx = c.TM[t]
                rT = float(np.linalg.norm(c.TM[aT] - cT))
                DT = float(np.linalg.norm(fx - fT - (cx - cT))); bT = float(np.linalg.norm(fT - c.TM[aT]))
                ST = max(DT - bT - beta - rT, 0.0)
                Sc = max(float(np.linalg.norm(fx - cx)) - beta, 0.0)
                e = float(np.linalg.norm(fx - yx))
                prem = float(np.linalg.norm(yx - cx)) <= beta + 1e-10
                if prem:
                    assert ST <= e + 1e-8 and Sc <= e + 1e-8
                rows.append((uname, scen[t], t, i, ST, Sc, DT, cal, e, prem))
    return rows


def _cap_job(i):
    import multimodel_audit as M
    from perband_audit import hop_kappas, p_hops
    from threadpoolctl import threadpool_limits
    c = M.Corpus('ctr12')
    U, Y = c.windows(c.train)
    rows = []
    with threadpool_limits(limits=1):
        g = fit(CFG[i], U, Y)
        for tag, hi in M.CONFIGS:
            lawcal = [n for n in c.names if M.LAWCAL_LO <= c.TP[n] <= hi]
            q = c.slopes(lawcal); top = max(lawcal, key=lambda n: c.TP[n])
            kappa = hop_kappas(c, p_hops(c, lawcal))[0]
            aT = max(c.train, key=lambda n: c.TP[n]); dT = c.lp[aT] - c.lp[top]
            fT = g(np.array([c.lp[aT]]))[0]; cT = c.TM[top] + q * dT
            cal = float(max(np.linalg.norm(g(np.array([c.lp[n]]))[0] - c.TM[n]) for n in lawcal))
            for t in [n for n in c.names if c.TP[n] > hi]:
                d = c.lp[t] - c.lp[top]; cx = c.TM[top] + q * d; beta = 2 * kappa * d
                fx = g(np.array([c.lp[t]]))[0]
                rT = float(np.linalg.norm(c.TM[aT] - cT))
                DT = float(np.linalg.norm(fx - fT - (cx - cT))); bT = float(np.linalg.norm(fT - c.TM[aT]))
                ST = max(DT - bT - beta - rT, 0.0); Sc = max(float(np.linalg.norm(fx - cx)) - beta, 0.0)
                e = float(np.linalg.norm(fx - c.TM[t]))
                rows.append(('ctr12|' + tag, tag, t, i, ST, Sc, DT, cal, e, bool(np.linalg.norm(c.TM[t] - cx) <= beta)))
    return rows


def run(name):
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        if name == 'capillary':
            for rr in ex.map(_cap_job, range(len(CFG))):
                rows += rr
        else:
            units = MA.load_units(name)
            keys = sorted(units)
            if len(keys) > MAX_UNITS:
                keys = sorted(np.random.default_rng(0).choice(keys, MAX_UNITS, replace=False))
            for rr in ex.map(_job, [(name, k, units[k]) for k in keys], chunksize=1):
                rows += rr
    pickle.dump(rows, open(OUT / ('%s_rows.pkl' % name), 'wb'))
    print('%s: %d rows, %.0fs' % (name, len(rows), time.time() - t0), flush=True)


# ------------------------------------------------------------------ ranking metrics
def spearman(x, y):
    from scipy.stats import spearmanr
    return spearmanr(x, y).correlation if np.ptp(x) > 1e-12 and np.ptp(y) > 1e-12 else np.nan


def pairwise(x, e):
    """Share of model pairs ordered as their errors are; a tie in the score counts 1/2."""
    ok = tie = n = 0
    for i, j in combinations(range(len(x)), 2):
        if abs(e[i] - e[j]) < 1e-12:
            continue
        n += 1
        if abs(x[i] - x[j]) < 1e-12:
            tie += 1
        elif (x[i] - x[j]) * (e[i] - e[j]) > 0:
            ok += 1
    return (ok + 0.5 * tie) / n if n else np.nan, tie / n if n else np.nan


def report():
    res, lines = {}, []
    cols = ['S', 'Sc', 'D', 'cal']
    hdr = '%-13s %-6s %4s %6s | %s | %s | %s | %s' % ('dataset', 'band', 'n', 'bins', 'rho S   Sc    D   cal',
                                                    'pairs S   Sc    D   cal', 'S ties', 'worst S / cal  best-not-flagged S / cal')
    lines += [hdr, '-' * len(hdr)]
    for name in NAMES:
        f = OUT / ('%s_rows.pkl' % name)
        if not f.exists():
            continue
        R = pickle.load(open(f, 'rb'))
        G = {}
        for r in R:
            G.setdefault((r[0], r[2]), []).append(r)
        for band in sorted({r[1] for r in R}):
            for n in SIZES:
                keep = set(ORDER[:n])
                acc = {k: [] for k in ('rho', 'pair', 'tie', 'worst', 'best')}
                for key, g in G.items():
                    g = [r for r in g if r[1] == band and r[3] in keep]
                    if len(g) < 3:
                        continue
                    M = np.array([r[4:9] for r in g], float)       # S, Sc, D, cal, e
                    e = M[:, 4]
                    acc['rho'].append([spearman(M[:, j], e) for j in range(4)])
                    pw = [pairwise(M[:, j], e) for j in range(4)]
                    acc['pair'].append([p[0] for p in pw]); acc['tie'].append(pw[0][1])
                    acc['worst'].append([float(np.argmax(M[:, j]) == np.argmax(e)) for j in (0, 3)])
                    acc['best'].append([float(M[np.argmin(e), j] <= M[:, j].min() + 1e-12) for j in (0, 3)])
                if not acc['rho']:
                    continue
                m = {k: np.nanmean(np.array(v, float), 0).tolist() for k, v in acc.items()}
                res['%s|%s|%d' % (name, band, n)] = dict(bins=len(acc['rho']), **m)
                lines.append('%-13s %-6s %4d %6d | %s | %s | %6.2f | %4.2f / %4.2f   %4.2f / %4.2f' % (
                    name, band.replace('canonical_', ''), n, len(acc['rho']),
                    ' '.join('%5.2f' % v for v in m['rho']), ' '.join('%5.2f' % v for v in m['pair']),
                    m['tie'], m['worst'][0], m['worst'][1], m['best'][0], m['best'][1]))
        lines.append('')
    lines.append('rho = mean within-bin Spearman with the true error; pairs = share of model pairs ordered '
                 'correctly (score ties count 1/2); S ties = share of pairs tied in S (mostly both silent); '
                 'worst = picks the worst model; best-not-flagged = the truly best model has the lowest score.')
    txt = '\n'.join(lines)
    (OUT / 'report.txt').write_text(txt); (OUT / 'results.json').write_text(json.dumps(res, indent=1))
    print(txt)


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        for nm in (sys.argv[2:] or NAMES):
            run(nm)
    else:
        report()
