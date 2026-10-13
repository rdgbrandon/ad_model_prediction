"""Allowance that stops growing at the spec-sheet cap. Protocol: SATURATING_PROTOCOL.md.

  python saturating_audit.py 2016 2017 2018 2019      development
  python saturating_audit.py 2020                     confirmation (builds records first)
  python saturating_audit.py report
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

import allowance_audit as AA
import perband_audit as PB
from bound_shape_audit import WIND_CAP, rates, score
from perband_audit import e1_hops

HERE = Path(__file__).resolve().parent
OUT = HERE / 'saturating'
ARCHIVES = {2019: 'Kelmarsh_SCADA_2019_3085.zip', 2020: 'Kelmarsh_SCADA_2020_3086.zip'}
for _y in (2018, 2019, 2020):
    AA.YEARS[_y] = HERE / 'wind' / str(_y)
RULES = ['L', 'K-L', 'K-S1', 'K-S2']


def build(year):
    out = AA.YEARS[year]
    if (out / 'records.npz').exists():
        return
    import build_wind
    build_wind.ARCHIVE = HERE.parent / 'external_data' / 'kelmarsh' / ARCHIVES[year]
    build_wind.MONTHS = range(1, 13)
    build_wind.OUT = out
    build_wind.run()


def delta_star(c, q, top):
    """Distance at which each output's fitted line reaches its cap."""
    return np.array([(WIND_CAP[j] - c.TM[top][j]) / q[j] if q[j] > 0 else np.inf for j in range(2)])


def run(year):
    build(year)
    units = AA.units_of(year)
    preds = PB.wind_preds(year)                      # nine surrogates per unit, cached
    cache, rows = {}, []
    for r in preds:
        u = r['unit']; c = units[u][2]
        if u not in cache:
            q, top = AA.ceiling_line(c)
            R = rates(c, c.band('LAWCAL'), q, top, e1_hops(c))
            assert abs(R['k'] - AA.e1_kappa(c)[0]) < 1e-12
            ds = np.maximum(delta_star(c, q, top), 0.0)
            cache[u] = (q, top, R['k'], float(np.max(ds)), float(np.min(ds)))
        q, top, k, ds1, ds2 = cache[u]
        d = r['delta']; line = c.TM[top] + q * d; brk = np.minimum(line, WIND_CAP)
        base = dict(year=year, scen=r['scen'], unit=u, bin=r['bin'], model=r['model'], delta=d,
                    dstar1=ds1, dstar2=ds2)
        for rule, cen, b in (('L', line, 2 * k * d), ('K-L', brk, 2 * k * d),
                             ('K-S1', brk, 2 * k * min(d, ds1)), ('K-S2', brk, 2 * k * min(d, ds2))):
            rows.append(dict(base, rule=rule, **score(r['pred'], cen, c.TM[r['bin']], b)))
    OUT.mkdir(exist_ok=True)
    pickle.dump(rows, open(OUT / ('rows_%d.pkl' % year), 'wb'))
    print('wind %d: %d units, %d row-rule pairs' % (year, len(cache), len(rows)), flush=True)


def report():
    from scipy.stats import beta as Bd
    res, lines = {}, []
    hdr = '%-22s %-5s %6s %8s %17s %7s %6s %7s %7s %9s' % (
        'year / scenario', 'rule', 'rows', 'premise', '95% CI (bins)', 'valid', 'fail|p', 'S/e', 'silent', 'beta/zeta')
    for y in (2016, 2017, 2018, 2019, 2020):
        f = OUT / ('rows_%d.pkl' % y)
        if not f.exists():
            continue
        R = pickle.load(open(f, 'rb'))
        lines += ['', 'WIND %d (%s)' % (y, 'CONFIRMATION' if y == 2020 else 'development'), hdr, '-' * len(hdr)]
        for scen, sl in (('A', 'A below rated'), ('B', 'B rated')):
            for rule in RULES:
                rs = [r for r in R if r['scen'] == scen and r['rule'] == rule]
                S = np.array([r['S'] for r in rs]); e = np.array([r['e'] for r in rs])
                p = np.array([r['prem'] for r in rs]); v = S <= e + 1e-9
                bins = {(r['unit'], r['bin']): r['prem'] for r in rs}
                k, n = sum(bins.values()), len(bins)
                lo = 0.0 if k == 0 else Bd.ppf(.025, k, n - k + 1)
                hi = 1.0 if k == n else Bd.ppf(.975, k + 1, n - k)
                s = dict(rows=len(rs), premise=float(p.mean()), ci=[float(lo), float(hi)], valid=float(v.mean()),
                         fail_prem=int((p & ~v).sum()), Se=float(np.median(S / e)), silent=float(np.mean(S <= 0.01)),
                         beta_over_zeta=float(np.median([r['beta'] / max(r['zeta'], 1e-12) for r in rs])))
                res['%d|%s|%s' % (y, scen, rule)] = s
                lines.append('%-22s %-5s %6d %8.3f %17s %7.3f %6d %7.2f %7.3f %9.2f' % (
                    '%d %s' % (y, sl), rule, s['rows'], s['premise'], '[%.3f, %.3f]' % tuple(s['ci']), s['valid'],
                    s['fail_prem'], s['Se'], s['silent'], s['beta_over_zeta']))
    lines.append('\nfail|p = bound failures where the premise held (must be 0). CI: Clopper-Pearson over unit-bins.')
    txt = '\n'.join(lines)
    (OUT / 'report.txt').write_text(txt); (OUT / 'results.json').write_text(json.dumps(res, indent=1))
    print(txt)


if __name__ == '__main__':
    if sys.argv[1] == 'report':
        report()
    else:
        for y in sys.argv[1:]:
            run(int(y))
