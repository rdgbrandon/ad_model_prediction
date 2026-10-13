"""Cluster-bootstrap 95% intervals for the headline results (MULTI_DATASET_PROTOCOL.md rows).
Clusters are machines (turbine, inverter or combiner): rows from one machine are not independent,
so whole machines are resampled with replacement (2,000 draws). Writes multi/bootstrap.json.
"""
import json
import pickle
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NAMES = ['kelmarsh', 'penmanshiel', 'lahauteborne', 'hilloftowie', 'pv9068', 'pv2107']
B = 2000


def machine(name, unit):
    if name == 'pv9068':
        return unit.split('-')[-1]                 # '2018-01-1.01' -> combiner '1.01'
    return unit.split('-')[1]                      # '<name>-<machine>-<month>'


def stats(rows):
    bins = {}
    for r in rows:
        bins[(r['unit'], r['bin'])] = r['prem']
    S = np.array([r['ST'] for r in rows]); e = np.array([r['e'] for r in rows])
    return np.mean(list(bins.values())), np.mean(S <= e + 1e-9), np.median(S / e)


def main():
    out = {}
    rng = np.random.default_rng(0)
    for name in NAMES:
        R = pickle.load(open(HERE / 'multi' / ('%s_rows.pkl' % name), 'rb'))
        for band in ('A', 'B'):
            for rule in ('L', 'K-S1'):
                rs = [r for r in R if r['scen'] == band and r['rule'] == rule]
                if not rs:
                    continue
                groups = {}
                for r in rs:
                    groups.setdefault(machine(name, r['unit']), []).append(r)
                keys = sorted(groups)
                point = stats(rs)
                draws = []
                for _ in range(B):
                    pick = rng.choice(len(keys), len(keys), replace=True)
                    draws.append(stats([r for i in pick for r in groups[keys[i]]]))
                draws = np.array(draws)
                lo, hi = np.percentile(draws, [2.5, 97.5], 0)
                out['%s|%s|%s' % (name, band, rule)] = dict(
                    machines=len(keys), premise=[point[0], lo[0], hi[0]], valid=[point[1], lo[1], hi[1]],
                    Se=[point[2], lo[2], hi[2]])
                print('%-13s %s %-5s machines %3d  premise %.3f [%.3f, %.3f]  valid %.3f [%.3f, %.3f]  S/e %.2f [%.2f, %.2f]'
                      % (name, band, rule, len(keys), point[0], lo[0], hi[0], point[1], lo[1], hi[1], point[2], lo[2], hi[2]),
                      flush=True)
    (HERE / 'multi' / 'bootstrap.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
