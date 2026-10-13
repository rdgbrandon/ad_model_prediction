"""Clean-law test on PV current vs irradiance. PV_PROTOCOL.md, PV_DEVIATIONS.md.

  python pv_audit.py premise        label-only premise coverage, every year
  python pv_audit.py cert 2019      full certificate with nine surrogates

Rules P and E1 are the wind functions (wind_paper_rule.kappa_fit,
allowance_audit.e1_kappa), imported, not rewritten. The certificate centre is
the LAWCAL ceiling, as in every ceiling-form audit; S = max(D - beta, 0).
"""
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings('ignore')
from threadpoolctl import threadpool_limits

from allowance_audit import e1_kappa, conformal_upper
from multimodel_audit import fit_model
from wind_paper_rule import kappa_fit

HERE = Path(__file__).resolve().parent
OUT = HERE / 'pv'
EDGES = np.arange(150.0, 1100.0 + 1e-9, 50.0)
BANDS = {'TRAIN': (150, 350), 'LAWCAL': (350, 550), 'A': (550, 800), 'B': (900, 1100)}
MIN_RECORDS = 6
Q_TH = np.array([1.0])
G_CLIP = 823.0
RULES = ['C', 'P', 'E1', 'S', 'E3_prev', 'E3_loyo']
MODELS = [('linear', 0), ('poly3', 0), ('knn5', 0), ('krr_rbf', 0), ('rf200', 0),
          ('gbrt', 0), ('mlp8', 0), ('mlp16x16', 0), ('mlp32x32', 0)]


class Unit:
    """One combiner-month; bins of irradiance play the role of trials."""

    def __init__(self, G, I):
        self.u = np.log(G.astype(float))
        self.y = np.log(I.astype(float))[:, None]
        b = np.digitize(G, EDGES) - 1
        self.names, self.TP, self.TM, self.lp, self.members, self.left = [], {}, {}, {}, {}, {}
        for k in range(len(EDGES) - 1):
            m = b == k
            if m.sum() >= MIN_RECORDS:
                n = float(EDGES[k] + 25.0)
                self.names.append(n); self.members[n] = m; self.left[n] = float(EDGES[k])
                self.lp[n] = float(self.u[m].mean()); self.TP[n] = float(np.exp(self.lp[n]))
                self.TM[n] = self.y[m].mean(0)

    def band(self, key):
        lo, hi = BANDS[key]
        return [n for n in self.names if lo <= self.left[n] < hi]

    def windows(self, bins):
        m = np.zeros(len(self.u), bool)
        for n in bins:
            m |= self.members[n]
        return self.u[m], self.y[m]

    def slopes(self, bins):
        x = np.array([self.lp[n] for n in bins]); Y = np.array([self.TM[n] for n in bins])
        return np.array([np.polyfit(x, Y[:, j], 1)[0] for j in range(Y.shape[1])])


def units():
    R = np.load(OUT / 'records.npz')
    for year in sorted(set(R['year'].tolist())):
        for c in range(len(R['labels'])):
            for month in range(1, 13):
                m = (R['year'] == year) & (R['combiner'] == c) & (R['month'] == month)
                if m.sum() < 8 * MIN_RECORDS:
                    continue
                unit = Unit(R['G'][m], R['I'][m])
                if len(unit.band('TRAIN')) == 4 and len(unit.band('LAWCAL')) == 4:
                    yield '%d-%02d-%s' % (year, month, R['labels'][c]), year, str(R['labels'][c]), unit


def law(unit):
    lc = unit.band('LAWCAL')
    q = unit.slopes(lc); top = max(lc, key=lambda n: unit.TP[n])
    return q, top


def premise():
    OUT.mkdir(exist_ok=True)
    rows, pool = [], {}
    for name, year, comb, c in units():
        q, top = law(c)
        kC = float(np.linalg.norm(q - Q_TH))
        kP = 2 * kappa_fit(c, c.band('LAWCAL'))
        kE1 = 2 * e1_kappa(c)[0]
        for scen in ('A', 'B'):
            bins = c.band(scen)
            if len(bins) < 2:
                continue
            for t in bins:
                d = c.lp[t] - c.lp[top]
                z = float(np.linalg.norm(c.TM[t] - (c.TM[top] + q * d)))
                pool.setdefault((year, t), []).append(z)
                rows.append(dict(unit=name, year=year, combiner=comb, scenario=scen, bin=t,
                                 G=c.TP[t], delta=float(d), zeta=z, q=float(q[0]),
                                 beta_C=kC * d, beta_P=kP * d, beta_E1=kE1 * d,
                                 beta_S=kE1 * d + 2 * max(0.0, math.log(c.TP[t] / G_CLIP))))
    years = sorted({r['year'] for r in rows})
    for r in rows:
        prev = pool.get((r['year'] - 1, r['bin']), [])
        loyo = [z for y in years if y != r['year'] for z in pool.get((y, r['bin']), [])]
        r['beta_E3_prev'] = conformal_upper(np.array(prev))
        r['beta_E3_loyo'] = conformal_upper(np.array(loyo))
        r['n_E3_prev'], r['n_E3_loyo'] = len(prev), len(loyo)
        for rule in RULES:
            r['covered_' + rule] = bool(r['zeta'] <= r['beta_' + rule] + 1e-10)
    data = dict(rows=rows, g_clip=G_CLIP,
                protocol_sha256=hashlib.sha256((HERE / 'PV_PROTOCOL.md').read_bytes()).hexdigest(),
                deviations_sha256=hashlib.sha256((HERE / 'PV_DEVIATIONS.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                records_sha256=hashlib.sha256((OUT / 'records.npz').read_bytes()).hexdigest())
    (OUT / 'premise.json').write_text(json.dumps(data, indent=1, allow_nan=True))
    print('premise rows %d from %d units -> pv/premise.json'
          % (len(rows), len({r['unit'] for r in rows})))


def cert(year):
    prem = {(r['unit'], r['bin']): r for r in
            json.loads((OUT / 'premise.json').read_text())['rows'] if r['year'] == year}
    rows, t0 = [], time.time()
    with threadpool_limits(limits=1):
        for name, y, comb, c in units():
            if y != year or not any(k[0] == name for k in prem):
                continue
            q, top = law(c)
            U, Ytr = c.windows(c.band('TRAIN'))
            for kind, seed in MODELS:
                g = fit_model(kind, seed, U, Ytr)
                for (un, t), p in prem.items():
                    if un != name:
                        continue
                    pred = np.asarray(g(np.array([[c.lp[t]]]))).ravel()[:1]
                    centre = c.TM[top] + q * (c.lp[t] - c.lp[top])
                    D = float(np.linalg.norm(pred - centre))
                    e = float(np.linalg.norm(pred - c.TM[t]))
                    row = dict(unit=name, combiner=comb, scenario=p['scenario'], bin=t,
                               model=kind, D=D, e=e)
                    for rule in RULES:
                        S = max(D - p['beta_' + rule], 0.0)
                        if p['covered_' + rule]:
                            assert S <= e + 1e-8, 'bound failed where its premise held'
                        row['S_' + rule] = S
                    rows.append(row)
            print('%s  (%.0fs)' % (name, time.time() - t0), flush=True)
    (OUT / ('cert_%d.json' % year)).write_text(json.dumps(dict(
        rows=rows, year=year, models=MODELS,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=1))
    print('cert rows %d -> pv/cert_%d.json' % (len(rows), year))


if __name__ == '__main__':
    if sys.argv[1] == 'premise':
        premise()
    else:
        cert(int(sys.argv[2]))
