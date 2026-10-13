"""Does training a surrogate on the law blind the certificate that checks it?

Protocol: PHYSICS_INFORMED_PROTOCOL.md. Run test_pinn.py first.
The certificate is imported (ceiling_audit.certificate, consensus_audit.combine),
not reimplemented; only the surrogate is new.
"""
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from ceiling_audit import certificate
from consensus_audit import combine
from multimodel_audit import Corpus, subset_balls, CONFIGS, LAWCAL_LO
from pinn import PINN

HERE = Path(__file__).resolve().parent
OUT = HERE / 'physics_informed'
DATASETS = ['ctr12', 'pist12']
ARMS = ['certificate law', 'training law', 'KZ theory']
WEIGHTS = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
SEEDS = [0, 1, 2]
U_HI = np.log(400.0)


def arm_slope(c, arm, lawcal):
    if arm == 'certificate law':
        return c.slopes(lawcal)
    if arm == 'training law':
        return c.slopes(c.train)
    return np.full(c.B, 0.5)


def run():
    OUT.mkdir(exist_ok=True)
    rows, cache = [], {}
    t0 = time.time()
    with threadpool_limits(limits=1):
        for ds in DATASETS:
            c = Corpus(ds)
            U, Y = c.windows(c.train)
            u_tr = max(c.lp[n] for n in c.train)
            for tag, hi in CONFIGS:
                lawcal = [n for n in c.names if LAWCAL_LO <= c.TP[n] <= hi]
                test = [n for n in c.names if c.TP[n] > hi]
                q_cert = c.slopes(lawcal)
                top = max(lawcal, key=lambda n: c.TP[n])
                kappa = float(np.linalg.norm(q_cert - .5))
                for arm in ARMS:
                    q = arm_slope(c, arm, lawcal)
                    for w in WEIGHTS:
                        for seed in SEEDS:
                            # w = 0 ignores q; other arms ignore the split.
                            key = (ds, seed, w, None if w == 0 else tuple(np.round(q, 12)))
                            if key not in cache:
                                cache[key] = PINN(seed).fit(U, Y, q, w, u_tr, U_HI)
                            m = cache[key]
                            train_err = float(np.mean([np.linalg.norm(
                                m.predict([c.lp[n]])[0] - c.TM[n]) for n in c.train]))
                            # Own law residual against the CERTIFICATE's law, in the
                            # extrapolation region: how law-consistent the surrogate
                            # is in the very sense the certificate measures.
                            uc = np.linspace(u_tr, U_HI - .1, 40)
                            r_cert = m.predict(uc + .1) - m.predict(uc) - q_cert * .1
                            for t in test:
                                u = c.lp[t]
                                pred = m.predict([u])[0]
                                centre, radius, S = certificate(pred, c.TM[top], q_cert,
                                                                u - c.lp[top], kappa)
                                e = float(np.linalg.norm(pred - c.TM[t]))
                                covered = bool(np.linalg.norm(c.TM[t] - centre) <= radius + 1e-10)
                                if covered:
                                    assert S <= e + 1e-8, 'triangle inequality violated'
                                cs, rs, _ = subset_balls(c, lawcal, t)
                                S_con, _, _ = combine(pred, cs, rs)
                                con_cov = bool(np.all(np.linalg.norm(cs - c.TM[t], axis=1)
                                                      <= rs + 1e-9))
                                if con_cov:
                                    assert S_con <= e + 1e-8
                                rows.append(dict(
                                    dataset=ds, config=tag, arm=arm, w=w, seed=seed, trial=t,
                                    P=c.TP[t], e=e, S=S, S_consensus=S_con,
                                    D=float(np.linalg.norm(pred - centre)), radius=radius,
                                    S_over_e=S / e, silent=bool(S <= 1), covered=covered,
                                    valid=bool(S <= e + 1e-10),
                                    own_law_residual=m.law_residual(),
                                    residual_vs_certificate_law=float(
                                        np.linalg.norm(r_cert, axis=1).mean()),
                                    train_error=train_err, converged=m.converged))
                print('%-7s %-14s %-16s done  (%d fits, %.0fs)'
                      % (ds, tag, arm, len(cache), time.time() - t0), flush=True)

    data = dict(rows=rows, fits=len(cache), arms=ARMS, weights=WEIGHTS, seeds=SEEDS,
                datasets=DATASETS,
                caveat='Four distinct test trials; seeds and weights are not independent trials.',
                protocol_sha256=hashlib.sha256((HERE / 'PHYSICS_INFORMED_PROTOCOL.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                pinn_sha256=hashlib.sha256((HERE / 'pinn.py').read_bytes()).hexdigest())
    tmp = OUT / 'results.tmp'
    tmp.write_text(json.dumps(data, indent=1, allow_nan=False))
    tmp.replace(OUT / 'results.json')
    with (OUT / 'rows.csv').open('w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0]))
        wr.writeheader(); wr.writerows(rows)
    print('rows %d, fits %d -> physics_informed/results.json' % (len(rows), len(cache)))


if __name__ == '__main__':
    run()
