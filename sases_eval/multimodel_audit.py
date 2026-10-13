"""Ceiling and consensus certificates across many surrogates and many target
representations. Protocol: MULTIMODEL_PROTOCOL.md, hashed into the results.

The certificate itself is imported, not reimplemented: `certificate` from
ceiling_audit, `combine` from consensus_audit, `summarize` from theory_audit.
Only the surrogate family and the target representation vary here.
"""
import csv
import hashlib
import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings('ignore')
from threadpoolctl import threadpool_limits
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.kernel_ridge import KernelRidge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, PolynomialFeatures

from ceiling_audit import certificate
from consensus_audit import combine
from theory_audit import summarize

HERE = Path(__file__).resolve().parent
OUT = HERE / 'multimodel'
DATASETS = ['ctr12', 'ctr24w', 'ctrlin8', 'ctrshort', 'ctrmed', 'ctrshape', 'pist12']
MODELS = ([('linear', 0), ('poly3', 0), ('knn5', 0), ('krr_rbf', 0)]
          + [('rf200', s) for s in range(3)] + [('gbrt', s) for s in range(3)]
          + [('mlp8', s) for s in range(3)] + [('mlp16x16', s) for s in range(3)]
          + [('mlp32x32', s) for s in range(3)])
CONFIGS = [('canonical_146', 146.0), ('canonical_192', 192.0)]
TRAIN_LO, TRAIN_HI, LAWCAL_LO = 12.0, 54.0, 106.0


class Corpus:
    """Trial means and window arrays for one target representation."""

    def __init__(self, name):
        d = np.load(HERE / 'datasets' / (name + '.npz'), allow_pickle=False)
        self.name = name
        self.Y, self.P, self.trial = d['Y'], d['P'], d['trial']
        self.names = list(dict.fromkeys(self.trial))
        self.TP = {n: float(self.P[self.trial == n][0]) for n in self.names}
        self.TM = {n: self.Y[self.trial == n].mean(0) for n in self.names}
        self.lp = {n: np.log(self.TP[n]) for n in self.names}
        self.B = self.Y.shape[1]
        self.train = [n for n in self.names if TRAIN_LO <= self.TP[n] <= TRAIN_HI]

    def windows(self, trials):
        m = np.isin(self.trial, list(trials))
        return np.log(self.P[m]), self.Y[m]

    def slopes(self, ts):
        x = np.array([self.lp[n] for n in ts])
        Y = np.array([self.TM[n] for n in ts])
        return np.array([np.polyfit(x, Y[:, b], 1)[0] for b in range(self.B)])


def fit_model(kind, seed, U, Yt):
    """Surrogate on ln(power) -> target vector. linear/mlp8/mlp16x16 keep the
    definitions used by capillary2.build; the rest are the new families."""
    X = U[:, None]
    if kind == 'linear':
        m = LinearRegression().fit(X, Yt)
        return lambda V: m.predict(np.asarray(V, float))
    if kind == 'poly3':
        m = make_pipeline(StandardScaler(), PolynomialFeatures(3), Ridge(alpha=1e-6)).fit(X, Yt)
        return lambda V: m.predict(np.asarray(V, float))
    if kind == 'knn5':
        m = KNeighborsRegressor(n_neighbors=5).fit(X, Yt)
        return lambda V: m.predict(np.asarray(V, float))
    if kind == 'krr_rbf':
        sc = StandardScaler().fit(X)
        m = KernelRidge(kernel='rbf', alpha=1e-3, gamma=1.0).fit(sc.transform(X), Yt)
        return lambda V: m.predict(sc.transform(np.asarray(V, float)))
    if kind == 'rf200':
        m = RandomForestRegressor(n_estimators=200, random_state=seed).fit(X, Yt)
        return lambda V: m.predict(np.asarray(V, float))
    if kind == 'gbrt':
        m = MultiOutputRegressor(GradientBoostingRegressor(random_state=seed)).fit(X, Yt)
        return lambda V: m.predict(np.asarray(V, float))
    hid = {'mlp8': (8,), 'mlp16x16': (16, 16), 'mlp32x32': (32, 32)}[kind]
    sc = StandardScaler().fit(X)
    g = MLPRegressor(hidden_layer_sizes=hid, activation='tanh', alpha=1e-3,
                     max_iter=8000, random_state=seed, learning_rate_init=5e-3,
                     tol=1e-8, n_iter_no_change=400).fit(sc.transform(X), Yt)
    return lambda V: g.predict(sc.transform(np.asarray(V, float)))


def subset_balls(c, lawcal, trial):
    """One target ball per LAWCAL subset of size >= 3; calibration labels only."""
    centres, radii, subsets = [], [], []
    for size in range(3, len(lawcal) + 1):
        for sub in combinations(lawcal, size):
            top = max(sub, key=lambda t: c.TP[t])
            q = c.slopes(list(sub))
            d = c.lp[trial] - c.lp[top]
            centres.append(c.TM[top] + q * d)
            radii.append(float(np.linalg.norm(q - .5) * d))
            subsets.append(list(sub))
    return np.array(centres), np.array(radii), subsets


def run():
    OUT.mkdir(exist_ok=True)
    rows = []
    with threadpool_limits(limits=1):
        for ds in DATASETS:
            c = Corpus(ds)
            for kind, seed in MODELS:
                t0 = time.time()
                U, Yt = c.windows(c.train)
                g = fit_model(kind, seed, U, Yt)
                for tag, hi in CONFIGS:
                    lawcal = [n for n in c.names if LAWCAL_LO <= c.TP[n] <= hi]
                    test = [n for n in c.names if c.TP[n] > hi]
                    assert not (set(lawcal) & set(test) or set(c.train) & set(test)
                                or set(c.train) & set(lawcal))
                    q = c.slopes(lawcal)
                    top = max(lawcal, key=lambda n: c.TP[n])
                    kappa = float(np.linalg.norm(q - .5))
                    for t in test:
                        delta = float(c.lp[t] - c.lp[top])
                        pred = g(np.array([[c.lp[t]]]))[0]
                        centre, radius, S = certificate(pred, c.TM[top], q, delta, kappa)
                        e = float(np.linalg.norm(pred - c.TM[t]))
                        residual = float(np.linalg.norm(c.TM[t] - centre))
                        covered = bool(residual <= radius + 1e-10)
                        if covered:
                            assert S <= e + 1e-8, 'triangle inequality violated'
                        centres, radii, subsets = subset_balls(c, lawcal, t)
                        S_con, w, best_single = combine(pred, centres, radii)
                        res_all = np.linalg.norm(centres - c.TM[t], axis=1)
                        con_covered = bool(np.all(res_all <= radii + 1e-9))
                        if con_covered:
                            assert S_con <= e + 1e-8, 'consensus premise held but bound exceeded error'
                        assert S_con + 1e-8 >= S, 'consensus cannot fall below the single-region bound'
                        rows.append(dict(
                            dataset=ds, dim=c.B, config=tag, model=kind, seed=seed, trial=t,
                            P=c.TP[t], ceiling=c.TP[top], delta=delta, kappa=kappa,
                            radius=radius, tube_residual=residual, margin=radius - residual,
                            S=S, e=e, S_over_e=S / e if e > 0 else None, covered=covered,
                            valid=bool(S <= e + 1e-10), anchor_covered=True,
                            S_consensus=S_con, S_best_single=best_single,
                            consensus_gain=S_con - S, ball_count=len(radii),
                            consensus_covered=con_covered,
                            consensus_min_margin=float(np.min(radii - res_all)),
                            blend_gain=S_con - best_single,
                            n_windows_train=int(len(U))))
                print('%-9s %-9s seed %d  %5.1fs' % (ds, kind, seed, time.time() - t0), flush=True)

    summary = {}
    for ds in DATASETS:
        for tag, _ in CONFIGS:
            for kind, seed in MODELS:
                rs = [r for r in rows if r['dataset'] == ds and r['config'] == tag
                      and r['model'] == kind and r['seed'] == seed]
                if not rs:
                    continue
                summary['%s|%s|%s|%d' % (ds, tag, kind, seed)] = dict(
                    summarize(rs),
                    mean_S_over_e_consensus=float(np.mean([r['S_consensus'] / r['e'] for r in rs])),
                    mean_consensus_gain=float(np.mean([r['consensus_gain'] for r in rs])),
                    max_blend_gain=float(np.max([r['blend_gain'] for r in rs])),
                    consensus_covered_rows=int(sum(r['consensus_covered'] for r in rs)),
                    consensus_min_margin=float(np.min([r['consensus_min_margin'] for r in rs])),
                    mean_e=float(np.mean([r['e'] for r in rs])))
    data = dict(rows=rows, summary=summary, datasets=DATASETS, models=MODELS,
                assumption='True target remains inside the calibration-centred growth ball',
                caveat='Representations share the same 21 trials and one apparatus; '
                       'they are robustness checks, not independent replications.',
                protocol_sha256=hashlib.sha256((HERE / 'MULTIMODEL_PROTOCOL.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                builder_sha256=hashlib.sha256((HERE / 'build_datasets.py').read_bytes()).hexdigest())
    tmp = OUT / 'results.tmp'
    tmp.write_text(json.dumps(data, indent=1, allow_nan=False))
    tmp.replace(OUT / 'results.json')
    with (OUT / 'rows.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print('rows', len(rows), '-> multimodel/results.json', flush=True)


if __name__ == '__main__':
    run()
