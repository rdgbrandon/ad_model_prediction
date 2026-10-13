"""Worked derivation of every law allowance, on one real unit per system.

Each rule is recomputed step by step with its intermediate quantities exposed (the
hops, their ratios, the fleet pool and its order statistic), and every final value
is asserted equal to what the audit functions return. Writes
learned/derivation.json and prints the derivation.
"""
import json
import math
from pathlib import Path

import numpy as np

import allowance_audit as AA
import pv_audit as PA
from wind_paper_rule import kappa_fit as paper_kappa

HERE = Path(__file__).resolve().parent
ALPHA = 0.10


def line(c, bins):
    """Slope fitted on bins, anchored at the top bin: the certificate's law line."""
    q = c.slopes(bins); top = max(bins, key=lambda n: c.TP[n])
    return q, top


def resid(c, q, top, n):
    d = c.lp[n] - c.lp[top]
    centre = c.TM[top] + q * d
    return d, centre, c.TM[n] - centre


def derive(c, unit, tests, q_th, fleet, band_pool, spec_clip=None):
    lab = sorted(c.band('TRAIN') + c.band('LAWCAL'), key=lambda n: c.TP[n])
    lc = sorted(c.band('LAWCAL'), key=lambda n: c.TP[n])
    q, top = line(c, lc)
    out = dict(unit=unit,
               labelled=[dict(bin=n, x=c.TP[n], y=c.TM[n].tolist(), role='LAWCAL' if n in lc else 'TRAIN')
                         for n in lab],
               q=q.tolist(), top=top, y_top=c.TM[top].tolist(), q_th=q_th.tolist())
    # C
    kC = float(np.linalg.norm(q - q_th))
    # P: leave-the-top-out on LAWCAL (fit on 3 -> hold 1; fit on 2 -> hold 2)
    hopsP = []
    for fit, held in ((lc[:3], lc[3:]), (lc[:2], lc[2:])):
        qq, tt = line(c, fit)
        for n in held:
            d, _, z = resid(c, qq, tt, n)
            hopsP.append(dict(fit=fit, held=n, delta=d, zeta=float(np.linalg.norm(z)),
                              ratio=float(np.linalg.norm(z) / d)))
    kP = max(h['ratio'] for h in hopsP)
    assert abs(kP - paper_kappa(c, c.band('LAWCAL'))) < 1e-12
    # E1: every window of 4 consecutive labelled bins predicts every higher labelled bin
    hopsE = []
    for i in range(len(lab) - 3):
        fit = lab[i:i + 4]
        qq, tt = line(c, fit)
        for n in lab[i + 4:]:
            d, _, z = resid(c, qq, tt, n)
            hopsE.append(dict(fit=fit, held=n, delta=d, zeta=float(np.linalg.norm(z)),
                              ratio=float(np.linalg.norm(z) / d)))
    kE = max(h['ratio'] for h in hopsE)
    assert abs(kE - AA.e1_kappa(c)[0]) < 1e-12
    x = np.array([c.lp[n] for n in lab]); Y = np.array([c.TM[n] for n in lab])
    out.update(kappa_C=kC, hops_P=hopsP, kappa_P=kP, hops_E1=hopsE, kappa_E1=kE)
    out['tests'] = []
    for n in tests:
        d, centre, z = resid(c, q, top, n)
        zn = float(np.linalg.norm(z))
        assert abs(zn - AA.zeta(c, n)) < 1e-12
        quad = np.array([np.polyval(np.polyfit(x, Y[:, j], 2), c.lp[n]) for j in range(Y.shape[1])])
        dq = float(np.linalg.norm(quad - centre))
        pool = np.sort(np.array(fleet.get(n, [])))
        k = math.ceil((len(pool) + 1) * (1 - ALPHA))
        bE3 = float(pool[k - 1]) if k <= len(pool) else math.inf
        assert bE3 == AA.conformal_upper(pool)
        band, ratios = band_pool(n)
        kf = math.ceil((len(ratios) + 1) * (1 - ALPHA))
        rateF0 = float(np.sort(ratios)[kf - 1])
        t = dict(bin=n, x=c.TP[n], delta=d, y=c.TM[n].tolist(), centre=centre.tolist(), zeta=z.tolist(),
                 zeta_norm=zn, quad=quad.tolist(), quad_departure=dq,
                 beta=dict(C=kC * d, P=2 * kP * d, E1=2 * kE * d, E2=max(2 * kE * d, 2 * dq), E3=bE3,
                           F0=rateF0 * d, Z=float(np.linalg.norm(q)) * d),
                 e3_pool_n=len(pool), e3_k=k, e3_pool_quantiles=np.percentile(pool, [50, 90]).tolist() if len(pool) else None,
                 f0_band=band, f0_n=len(ratios), f0_k=kf, f0_rate=rateF0)
        if spec_clip:
            t['beta']['S'] = 2 * kE * d + 2 * max(0.0, math.log(c.TP[n] / spec_clip))
            t['spec_term'] = 2 * max(0.0, math.log(c.TP[n] / spec_clip))
        t['covered'] = {r: bool(zn <= b + 1e-10) for r, b in t['beta'].items()}
        out['tests'].append(t)
    return out


def pick(units, need, kappa):
    """The eligible unit whose E1 kappa' is closest to the median: a typical unit."""
    ok = {u: c for u, c in units.items() if all(n in c.names for n in need)}
    ks = {u: kappa(c) for u, c in ok.items()}
    med = np.median(list(ks.values()))
    return min(ks, key=lambda u: abs(ks[u] - med))


def fleet_zetas(units):
    pool = {}
    for c in units.values():
        q, top = AA.ceiling_line(c)
        for n in c.names:
            if c.lp[n] > c.lp[top]:
                pool.setdefault(n, []).append(AA.zeta(c, n))
    return pool


def band_ratios(units, lo, hi, half):
    r = []
    for c in units.values():
        q, top = AA.ceiling_line(c)
        for n in c.names:
            d = c.lp[n] - c.lp[top]
            if d > 0 and lo <= n - half < hi:
                r.append(AA.zeta(c, n) / d)
    return np.array(r)


def capillary():
    fits = {f['config']: f for f in json.loads((HERE / 'rerun/calibration_fits.json').read_text())}
    row = next(r for r in json.loads((HERE / 'ceiling/results.json').read_text())['rows']
               if r['config'] == 'canonical_192' and r['model'] == 'linear' and r['trial'] == '_60_1')
    f = fits['canonical_192']
    q = np.array(f['q_high'])
    kappa = float(np.linalg.norm(q - 0.5))
    assert abs(kappa - row['kappa']) < 1e-9 and abs(kappa * row['delta'] - row['radius']) < 1e-9
    return dict(config='canonical_192', lawcal=f['lawcal'], ceiling=f['ceiling'], ceiling_mW=row['ceiling'],
                trial=row['trial'], P_mW=row['P'], delta=row['delta'], q=q.tolist(), q_min=float(q.min()),
                q_max=float(q.max()), kappa=kappa, beta=row['radius'], zeta=row['tube_residual'],
                covered=row['covered'])


def run():
    wind16 = {k: v[2] for k, v in AA.units_of(2016).items()}
    wind17 = {k: v[2] for k, v in AA.units_of(2017).items()}
    wu = pick(wind17, (9.75, 12.75, 13.25), lambda c: AA.e1_kappa(c)[0])
    wband = lambda n: (('A', band_ratios(wind16, 8.5, 10.5, .25)) if n < 10.5
                       else ('B', band_ratios(wind16, 11.5, 14.5, .25)))
    W = derive(wind17[wu], wu, [9.75, 12.75], np.array([3.0, 1.0]), fleet_zetas(wind16), wband)
    pv = {}
    for name, y, comb, c in PA.units():
        if y in (2017, 2018):
            pv.setdefault(y, {})[name] = c
    pu = pick(pv[2018], (675.0, 975.0, 1025.0), lambda c: AA.e1_kappa(c)[0])
    pband = lambda n: (('A', band_ratios(pv[2017], 550, 800, 25)) if n < 800
                       else ('B', band_ratios(pv[2017], 900, 1100, 25)))
    P = derive(pv[2018][pu], pu, [675.0, 975.0], np.array([1.0]), fleet_zetas(pv[2017]), pband,
               spec_clip=PA.G_CLIP)
    data = dict(wind=W, pv=P, capillary=capillary(), alpha=ALPHA)
    (HERE / 'learned').mkdir(exist_ok=True)
    (HERE / 'learned/derivation.json').write_text(json.dumps(data, indent=1, allow_nan=True))
    for name, D in (('WIND', W), ('SOLAR', P)):
        print('\n==== %s unit %s ====' % (name, D['unit']))
        for r in D['labelled']:
            print('  %-6s bin %7.2f  x %8.2f  y %s' % (r['role'], r['bin'], r['x'], np.round(r['y'], 4)))
        print('  LAWCAL slope q = %s (theory %s), ceiling bin %s' % (np.round(D['q'], 3), D['q_th'], D['top']))
        print('  C: kappa = ||q - q_th|| = %.4f' % D['kappa_C'])
        print("  P: hops %s -> kappa'_short = %.4f" % ([round(h['ratio'], 3) for h in D['hops_P']], D['kappa_P']))
        print("  E1: %d hops, ratios %s -> kappa'_long = %.4f"
              % (len(D['hops_E1']), [round(h['ratio'], 3) for h in D['hops_E1']], D['kappa_E1']))
        for t in D['tests']:
            print('  test bin %.2f: delta %.4f  ||zeta|| %.4f   E3 pool n=%d k=%d   F0 %s-band rate %.3f (n=%d)'
                  % (t['bin'], t['delta'], t['zeta_norm'], t['e3_pool_n'], t['e3_k'], t['f0_band'],
                     t['f0_rate'], t['f0_n']))
            for r, b in t['beta'].items():
                print('     %-3s beta %.4f  %s' % (r, b, 'covers' if t['covered'][r] else 'MISSES'))
    C = data['capillary']
    print('\n==== CAPILLARY %s, trial %s (%.0f mW), ceiling %s (%.0f mW) ====' % (
        C['config'], C['trial'], C['P_mW'], C['ceiling'], C['ceiling_mW']))
    print('  q (12 bands) in [%.2f, %.2f]; kappa = ||q - 0.5|| = %.3f; delta = %.4f; beta = %.3f; ||zeta|| = %.3f'
          % (C['q_min'], C['q_max'], C['kappa'], C['delta'], C['beta'], C['zeta']))


if __name__ == '__main__':
    run()
