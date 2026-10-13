"""Reproduction gate for MULTIMODEL_PROTOCOL.md.

On ctr12 with linear/mlp8/mlp16x16 the new harness must reproduce the stored
ceiling and consensus numbers to 1e-8. Run this before trusting anything the
multi-representation sweep prints.
"""
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from ceiling_audit import certificate
from consensus_audit import combine
from multimodel_audit import Corpus, fit_model, subset_balls, CONFIGS, LAWCAL_LO

HERE = Path(__file__).resolve().parent
TOL = 1e-8


def test_ctr12_matches_spec():
    old = np.load(HERE / 'spec.npz', allow_pickle=False)
    new = np.load(HERE / 'datasets/ctr12.npz', allow_pickle=False)
    for k in ('Y', 'P', 'trial', 'wi'):
        assert np.array_equal(old[k], new[k]), k


def test_reproduces_ceiling_and_consensus():
    ceiling = {(r['config'], r['model'], r['seed'], r['trial']): r
               for r in json.loads((HERE / 'ceiling/results.json').read_text())['rows']}
    consensus = {(r['config'], r['model'], r['seed'], r['trial']): r
                 for r in json.loads((HERE / 'consensus/results.json').read_text())['rows']}
    c = Corpus('ctr12')
    checked = 0
    with threadpool_limits(limits=1):
        for kind, seed in [('linear', 0)] + [('mlp8', s) for s in range(3)] \
                + [('mlp16x16', s) for s in range(3)]:
            U, Yt = c.windows(c.train)
            g = fit_model(kind, seed, U, Yt)
            for tag, hi in CONFIGS:
                lawcal = [n for n in c.names if LAWCAL_LO <= c.TP[n] <= hi]
                q = c.slopes(lawcal)
                top = max(lawcal, key=lambda n: c.TP[n])
                kappa = float(np.linalg.norm(q - .5))
                for t in [n for n in c.names if c.TP[n] > hi]:
                    key = (tag, kind, seed, t)
                    pred = g(np.array([[c.lp[t]]]))[0]
                    _, radius, S = certificate(pred, c.TM[top], q, c.lp[t] - c.lp[top], kappa)
                    ref = ceiling[key]
                    assert abs(kappa - ref['kappa']) < TOL, (key, kappa, ref['kappa'])
                    assert abs(radius - ref['radius']) < TOL, key
                    assert abs(S - ref['S']) < TOL, (key, S, ref['S'])
                    e = float(np.linalg.norm(pred - c.TM[t]))
                    assert abs(e - ref['e']) < TOL, (key, e, ref['e'])
                    centres, radii, _ = subset_balls(c, lawcal, t)
                    S_con, _, best_single = combine(pred, centres, radii)
                    cref = consensus[key]
                    assert abs(S_con - cref['S']) < TOL, (key, S_con, cref['S'])
                    assert abs(best_single - cref['best_single_S']) < TOL, key
                    assert abs(ref['S'] - cref['baseline_S']) < TOL, key
                    checked += 1
    assert checked == 7 * 7, checked
    print('reproduction gate passed on', checked, 'rows')


if __name__ == '__main__':
    test_ctr12_matches_spec()
    test_reproduces_ceiling_and_consensus()
