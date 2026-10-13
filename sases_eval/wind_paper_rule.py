"""Post hoc, see WIND_ADDENDUM.md: the paper's own Eq. 5 allowance on wind data.

beta = 2 * kappa'_fit * delta, kappa'_fit = max leave-the-top-out ratio on
LAWCAL. Label-only for the premise; uses the stored raw defect for S.
"""
import json
from pathlib import Path

import numpy as np

import wind_audit as W

HERE = Path(__file__).resolve().parent


def kappa_fit(c, lawcal):
    b = sorted(lawcal, key=lambda n: c.TP[n])
    ratios = []
    for fit, held in ((b[:3], b[3:]), (b[:2], b[2:])):
        q = c.slopes(fit); top = fit[-1]
        for n in held:
            d = c.lp[n] - c.lp[top]
            z = np.linalg.norm(c.TM[n] - (c.TM[top] + q * d))
            ratios.append(z / d)
    return float(max(ratios))


def run():
    rec = np.load(HERE / 'wind/records.npz')
    res = json.loads((HERE / 'wind/results.json').read_text())
    rows = res['rows']
    beta_rate, zeta = {}, {}
    for t in range(1, 7):
        for m in range(5, 13):
            s = (rec['turbine'] == t) & (rec['month'] == m)
            c = W.Unit(rec['U'][s], rec['P'][s], rec['omega'][s])
            lc = c.band('LAWCAL')
            if len(c.band('TRAIN')) != 4 or len(lc) != 4:
                continue
            unit = 'T%d-%02d' % (t, m)
            beta_rate[unit] = 2 * kappa_fit(c, lc)
            q = c.slopes(lc); top = max(lc, key=lambda n: c.TP[n])
            for n in c.names:
                d = c.lp[n] - c.lp[top]
                if d > 0:
                    zeta[(unit, n)] = float(np.linalg.norm(c.TM[n] - (c.TM[top] + q * d)))
    out = {}
    print('PAPER RULE (Eq. 5), POST HOC: beta = 2 x max leave-the-top-out ratio x delta')
    for scen in ('A', 'B'):
        rs = [r for r in rows if r['scenario'] == scen]
        beta = np.array([beta_rate[r['unit']] * r['delta'] for r in rs])
        z = np.array([zeta[(r['unit'], r['bin'])] for r in rs])
        D = np.array([r['raw_defect'] for r in rs]); e = np.array([r['e'] for r in rs])
        S = np.maximum(D - beta, 0)
        cov, val = z <= beta + 1e-10, S <= e + 1e-9
        assert np.all(val[cov]), 'bound failed where its premise held'
        units = sorted({r['unit'] for r in rs})
        unit_cov = [np.all(cov[[r['unit'] == u for r in rs]]) for u in units]
        out[scen] = dict(rows=len(rs), premise=float(cov.mean()), validity=float(val.mean()),
                         validity_given_premise=float(val[cov].mean()) if cov.any() else None,
                         units_all_covered=int(sum(unit_cov)), units=len(units),
                         median_S_over_e=float(np.median(S / e)),
                         silent=float(np.mean(S <= 0.01)),
                         median_rate=float(np.median(list(beta_rate[u] for u in units))),
                         median_beta_over_zeta=float(np.median(beta / z)))
        o = out[scen]
        print('\nscenario %s: %d rows, %d units' % (scen, o['rows'], o['units']))
        print('  declared rate 2*kappa\' median %.3f   beta / ||zeta|| median %.2f'
              % (o['median_rate'], o['median_beta_over_zeta']))
        print('  premise held %.3f of rows, on every row of %d/%d units'
              % (o['premise'], o['units_all_covered'], o['units']))
        print('  validity %.3f; where the premise held %s'
              % (o['validity'], '--' if o['validity_given_premise'] is None
                 else '%.3f' % o['validity_given_premise']))
        print('  premise held & bound failed: %d   premise failed & bound failed: %d'
              % ((cov & ~val).sum(), (~cov & ~val).sum()))
        print('  median S/e %.3f   silent %.3f' % (o['median_S_over_e'], o['silent']))
    (HERE / 'wind/paper_rule.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    run()
