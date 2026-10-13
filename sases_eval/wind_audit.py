"""Independent replication on wind-turbine power. Protocol: WIND_PROTOCOL.md.

Run build_wind.py first. The certificate (ceiling_audit.certificate) and the
consensus combination (consensus_audit.combine) are imported unchanged. The
only generalisation is the theory exponent: the capillary code centres the
growth radius on the KZ value 0.5, here it is the vector q_th = (3, 1).
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
from sklearn.linear_model import LinearRegression
from threadpoolctl import threadpool_limits

from ceiling_audit import certificate
from consensus_audit import combine
from multimodel_audit import fit_model

HERE = Path(__file__).resolve().parent
OUT = HERE / 'wind'
EDGES = np.round(np.arange(4.5, 14.5 + 1e-9, 0.5), 2)
BANDS = {'TRAIN': (4.5, 6.5), 'LAWCAL': (6.5, 8.5), 'A': (8.5, 10.5), 'B': (11.5, 14.5)}
MIN_RECORDS = 6
Q_TH = np.array([3.0, 1.0])
MODELS = [('linear', 0), ('poly3', 0), ('knn5', 0), ('krr_rbf', 0), ('rf200', 0),
          ('gbrt', 0), ('mlp8', 0), ('mlp16x16', 0), ('mlp32x32', 0)]


class Unit:
    """One turbine-month, shaped like the capillary Corpus: bins are trials."""

    def __init__(self, U, P, W):
        self.u = np.log(U)
        self.y = np.stack([np.log(P), np.log(W)], 1)
        b = np.digitize(U, EDGES) - 1
        self.names, self.TP, self.TM, self.lp, self.members = [], {}, {}, {}, {}
        for k in range(len(EDGES) - 1):
            m = b == k
            if m.sum() >= MIN_RECORDS:
                n = float(EDGES[k] + 0.25)              # bin centre labels the bin
                self.names.append(n)
                self.members[n] = m
                self.lp[n] = float(self.u[m].mean())
                self.TP[n] = float(np.exp(self.lp[n]))
                self.TM[n] = self.y[m].mean(0)

    def band(self, key):
        lo, hi = BANDS[key]
        return [n for n in self.names if lo <= n - 0.25 < hi]

    def windows(self, bins):
        m = np.zeros(len(self.u), bool)
        for n in bins:
            m |= self.members[n]
        return self.u[m], self.y[m]

    def slopes(self, bins):
        x = np.array([self.lp[n] for n in bins]); Y = np.array([self.TM[n] for n in bins])
        return np.array([np.polyfit(x, Y[:, j], 1)[0] for j in range(Y.shape[1])])


def balls(c, lawcal, t):
    """Consensus regions; consensus_audit's construction with q_th in place of 0.5."""
    centres, radii = [], []
    for size in range(3, len(lawcal) + 1):
        for sub in combinations(lawcal, size):
            top = max(sub, key=lambda n: c.TP[n])
            q = c.slopes(list(sub)); d = c.lp[t] - c.lp[top]
            centres.append(c.TM[top] + q * d); radii.append(float(np.linalg.norm(q - Q_TH) * d))
    return np.array(centres), np.array(radii)


def run():
    OUT.mkdir(exist_ok=True)
    R = np.load(OUT / 'records.npz')
    rows, units = [], []
    t0 = time.time()
    with threadpool_limits(limits=1):
        for turbine in sorted(set(R['turbine'].tolist())):
            for month in sorted(set(R['month'].tolist())):
                m = (R['turbine'] == turbine) & (R['month'] == month)
                c = Unit(R['U'][m], R['P'][m], R['omega'][m])
                train, lawcal = c.band('TRAIN'), c.band('LAWCAL')
                tests = {s: c.band(s) for s in ('A', 'B')}
                ok = len(train) == 4 and len(lawcal) == 4
                units.append(dict(turbine=turbine, month=month, records=int(m.sum()),
                                  train_bins=len(train), lawcal_bins=len(lawcal),
                                  A_bins=len(tests['A']), B_bins=len(tests['B']),
                                  enters_A=bool(ok and len(tests['A']) >= 2),
                                  enters_B=bool(ok and len(tests['B']) >= 2)))
                if not ok or not any(len(v) >= 2 for v in tests.values()):
                    continue
                q = c.slopes(lawcal)
                top = max(lawcal, key=lambda n: c.TP[n])
                kappa = float(np.linalg.norm(q - Q_TH))
                Utr, Ytr = c.windows(train)
                xcal = np.array([c.lp[n] for n in lawcal])
                for kind, seed in MODELS:
                    g = fit_model(kind, seed, Utr, Ytr)
                    # Competitors, built from calibration labels only.
                    cal_err = np.linalg.norm(g(xcal[:, None]) - np.array([c.TM[n] for n in lawcal]),
                                             axis=1)
                    ols = LinearRegression().fit(xcal[:, None], cal_err)
                    for scen, bins in tests.items():
                        if len(bins) < 2:
                            continue
                        for t in bins:
                            u = c.lp[t]
                            pred = g(np.array([[u]]))[0]
                            centre, radius, S = certificate(pred, c.TM[top], q, u - c.lp[top], kappa)
                            e = float(np.linalg.norm(pred - c.TM[t]))
                            covered = bool(np.linalg.norm(c.TM[t] - centre) <= radius + 1e-10)
                            if covered:
                                assert S <= e + 1e-8, 'triangle inequality violated'
                            cs, rs = balls(c, lawcal, t)
                            S_con, _, _ = combine(pred, cs, rs)
                            con_cov = bool(np.all(np.linalg.norm(cs - c.TM[t], axis=1) <= rs + 1e-9))
                            if con_cov:
                                assert S_con <= e + 1e-8
                            rows.append(dict(
                                turbine=turbine, month=month, unit='T%d-%02d' % (turbine, month),
                                scenario=scen, model=kind, bin=t, U=c.TP[t],
                                delta=float(u - c.lp[top]), kappa=kappa, radius=radius,
                                margin=float(radius - np.linalg.norm(c.TM[t] - centre)),
                                e=e, sases=float(S_con), sases_ceiling=float(S),
                                covered=bool(con_cov), covered_ceiling=covered,
                                raw_defect=float(np.linalg.norm(pred - centre)),
                                sample_max_heuristic=float(cal_err.max()),
                                ols_error_heuristic=float(max(0.0, ols.predict([[u]])[0])),
                                q_P=float(q[0]), q_omega=float(q[1])))
                print('T%d month %2d  %4d records  A:%d B:%d bins  (%.0fs)'
                      % (turbine, month, m.sum(), len(tests['A']), len(tests['B']),
                         time.time() - t0), flush=True)

    data = dict(rows=rows, units=units, models=MODELS, bands=BANDS, q_theory=Q_TH.tolist(),
                min_records=MIN_RECORDS,
                citation='Kelmarsh wind farm dataset, Cubico Sustainable Investments Ltd, '
                         'Zenodo 16807551, CC-BY-4.0',
                protocol_sha256=hashlib.sha256((HERE / 'WIND_PROTOCOL.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                records_sha256=hashlib.sha256((OUT / 'records.npz').read_bytes()).hexdigest())
    tmp = OUT / 'results.tmp'
    tmp.write_text(json.dumps(data, indent=1, allow_nan=False))
    tmp.replace(OUT / 'results.json')
    with (OUT / 'rows.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print('rows %d from %d units -> wind/results.json'
          % (len(rows), len({r['unit'] for r in rows})))


if __name__ == '__main__':
    run()
