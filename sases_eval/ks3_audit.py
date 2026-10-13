"""K-S3: plateau allowance from earlier years' fleet. Protocol: KS3_PROTOCOL.md.

  python ks3_audit.py run 2017 2018 2019 2020     development
  python ks3_audit.py run 2021                    confirmation (builds records first)
  python ks3_audit.py report
"""
import json
import math
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings('ignore')

import allowance_audit as AA
import multi_audit as MA

HERE = Path(__file__).resolve().parent
OUT = HERE / 'ks3'
ARCHIVES = {2019: 'Kelmarsh_SCADA_2019_3085.zip', 2020: 'Kelmarsh_SCADA_2020_3086.zip',
            2021: 'Kelmarsh_SCADA_2021_4456.zip'}
for _y in (2018, 2019, 2020, 2021):
    AA.YEARS[_y] = HERE / 'wind' / str(_y)


def build(year):
    out = AA.YEARS[year]
    if (out / 'records.npz').exists():
        return
    import build_wind
    build_wind.ARCHIVE = HERE.parent / 'external_data' / 'kelmarsh' / ARCHIVES[year]
    build_wind.MONTHS = range(1, 13)
    build_wind.OUT = out
    build_wind.run()


def conformal90(z):
    n = len(z); k = math.ceil((n + 1) * 0.9)
    return float(np.sort(z)[k - 1]) if n >= 9 and k <= n else math.inf


def fleet_pool(years):
    """bin -> law errors against each unit's own capped law, over the given years."""
    pool = {}
    for y in years:
        for u, (t, m, c) in AA.units_of(y).items():
            q, top, kappa, line, capped, ds = MA.law_parts('kelmarsh', c)
            for n in c.names:
                d = c.lp[n] - c.lp[top]
                if d > 0:
                    pool.setdefault(n, []).append(float(np.linalg.norm(c.TM[n] - capped(d))))
    return {n: conformal90(np.array(v)) for n, v in pool.items()}


def _job(args):
    uname, c, q90 = args
    from threadpoolctl import threadpool_limits
    from multimodel_audit import fit_model
    q, top, kappa, line, capped, ds = MA.law_parts('kelmarsh', c)
    tests = {s: c.band(s) for s in ('A', 'B') if len(c.band(s)) >= 2}
    if not tests:
        return []
    U, Y = c.windows(c.band('TRAIN'))
    aT = max(c.band('TRAIN'), key=lambda n: c.TP[n]); dT = c.lp[aT] - c.lp[top]
    rows = []
    with threadpool_limits(limits=1):
        for kind, seed in MA.MODELS:
            g = fit_model(kind, seed, U, Y)
            pr = lambda u: np.asarray(g(np.array([[u]]))).reshape(-1)[:2]
            fT = pr(c.lp[aT])
            for scen, bins in tests.items():
                for t in bins:
                    d = c.lp[t] - c.lp[top]; fx = pr(c.lp[t])
                    b1 = 2 * kappa * min(d, ds)
                    b3 = b1 if d <= ds else min(2 * kappa * ds, q90.get(t, math.inf))
                    for rule, beta in (('K-L', 2 * kappa * d), ('K-S1', b1), ('K-S3', b3)):
                        r = _cert(fx, c.TM[top], c.TM[t], capped(d), capped(0), beta, fT, c.TM[aT], capped(dT))
                        rows.append(dict(unit=uname, scen=scen, bin=t, model=kind, rule=rule, delta=d,
                                         beyond=bool(d > ds), **r))
    return rows


def _cert(fx, ya, yx, cx, ca, beta, fT, yT, cT):
    z = float(np.linalg.norm(yx - cx)); e = float(np.linalg.norm(fx - yx))
    Sc = max(float(np.linalg.norm(fx - ya - (cx - ca))) - beta, 0.0)
    rT = float(np.linalg.norm(yT - cT))
    DT = float(np.linalg.norm(fx - fT - (cx - cT))); bT = float(np.linalg.norm(fT - yT))
    ST = max(DT - bT - beta - rT, 0.0)
    prem = z <= beta + 1e-10
    if prem:
        assert Sc <= e + 1e-8 and ST <= e + 1e-8, 'bound failed where its premise held'
    return dict(zeta=z, beta=beta, e=e, Sc=Sc, ST=ST, prem=prem)


def run(year):
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    build(year)
    q90 = fleet_pool(range(2016, year))
    units = AA.units_of(year)
    rows = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for rr in ex.map(_job, [(u, v[2], q90) for u, v in units.items()], chunksize=2):
            rows += rr
    pickle.dump(rows, open(OUT / ('rows_%d.pkl' % year), 'wb'))
    print('ks3 %d: %d units, %d rows (%.0fs)' % (year, len(units), len(rows), time.time() - t0), flush=True)


def report():
    from scipy.stats import beta as Bd
    res, lines = {}, []
    hdr = '%-6s %-7s %-5s %6s %8s %16s %7s %6s %6s %6s %9s' % ('year', 'band', 'rule', 'rows', 'premise', '95% CI (bins)',
                                                           'valid', 'fail', 'S/e', 'Sc/e', 'beta/zeta')
    lines += [hdr, '-' * len(hdr)]
    for y in range(2017, 2022):
        f = OUT / ('rows_%d.pkl' % y)
        if not f.exists():
            continue
        R = pickle.load(open(f, 'rb'))
        for scen in ('A', 'B'):
            for rule in ('K-L', 'K-S1', 'K-S3'):
                rs = [r for r in R if r['scen'] == scen and r['rule'] == rule]
                if not rs:
                    continue
                bins = {(r['unit'], r['bin']): r['prem'] for r in rs}
                k, n = sum(bins.values()), len(bins)
                lo = 0.0 if k == 0 else Bd.ppf(.025, k, n - k + 1); hi = 1.0 if k == n else Bd.ppf(.975, k + 1, n - k)
                S = np.array([r['ST'] for r in rs]); Sc = np.array([r['Sc'] for r in rs]); e = np.array([r['e'] for r in rs])
                p = np.array([r['prem'] for r in rs])
                ratio = np.median([r['beta'] / max(r['zeta'], 1e-9) for r in rs if np.isfinite(r['beta'])])
                s = dict(rows=len(rs), premise=k / n, ci=[float(lo), float(hi)], valid=float(np.mean(S <= e + 1e-9)),
                         fail=int((p & (S > e + 1e-9)).sum()), Se=float(np.median(S / e)), Sce=float(np.median(Sc / e)),
                         beta_over_zeta=float(ratio))
                res['%d|%s|%s' % (y, scen, rule)] = s
                lines.append('%-6d %-7s %-5s %6d %8.3f %16s %7.3f %6d %6.2f %6.2f %9.1f' % (
                    y, scen, rule, s['rows'], s['premise'], '[%.3f, %.3f]' % tuple(s['ci']), s['valid'], s['fail'],
                    s['Se'], s['Sce'], s['beta_over_zeta']))
        lines.append('')
    txt = '\n'.join(lines)
    (OUT / 'report.txt').write_text(txt); (OUT / 'results.json').write_text(json.dumps(res, indent=1))
    print(txt)


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        for yy in sys.argv[2:]:
            run(int(yy))
    else:
        report()
