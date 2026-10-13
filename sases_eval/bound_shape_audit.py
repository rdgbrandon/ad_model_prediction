"""Offset + slope allowance and a spec-sheet break law. Protocol: BOUND_SHAPE_PROTOCOL.md.

  python bound_shape_audit.py      runs capillary, wind 2016-19, solar; writes bound_shape/
"""
import json
import math
import pickle
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings('ignore')

HERE = Path(__file__).resolve().parent
OUT = HERE / 'bound_shape'
WIND_CAP = np.log([2050.0, 15.0])                 # rated power (kW), max rotor speed (rpm)
G_CLIP = 823.0


# ------------------------------------------------------------------ allowances
def hops(c, hop_list):
    """(d_h, ||zeta_h||) for every calibration hop."""
    out = []
    for fit, held in hop_list:
        if len(fit) < 2:
            continue
        q = c.slopes(fit); top = fit[-1]
        for n in held:
            d = c.lp[n] - c.lp[top]
            out.append((d, float(np.linalg.norm(c.TM[n] - (c.TM[top] + q * d)))))
    return np.array(out)


def boundary_residual(c, lawcal, q, top):
    return max(float(np.linalg.norm(c.TM[n] - (c.TM[top] + q * (c.lp[n] - c.lp[top])))) for n in lawcal)


def rates(c, lawcal, q, top, hop_list):
    H = hops(c, hop_list)
    r0 = boundary_residual(c, lawcal, q, top)
    k = float(np.max(H[:, 1] / H[:, 0]))
    kA = float(np.max(np.maximum(H[:, 1] - r0, 0) / H[:, 0]))
    return dict(k=k, r0=r0, kA=kA)


def score(pred, centre, label, beta):
    S = max(float(np.linalg.norm(pred - centre)) - beta, 0.0)
    e = float(np.linalg.norm(pred - label))
    z = float(np.linalg.norm(label - centre))
    prem = z <= beta + 1e-10
    if prem:
        assert S <= e + 1e-8, 'bound failed where its premise held'
    return dict(S=S, e=e, zeta=z, beta=beta, prem=prem)


def rule_rows(base, pred, label, line_c, break_c, R, d, extra=()):
    out = []
    bL, bA = 2 * R['k'] * d, R['r0'] + 2 * R['kA'] * d
    todo = [('L', line_c, bL), ('A', line_c, bA)] + list(extra)
    if break_c is not None:
        todo += [('K-L', break_c, bL), ('K-A', break_c, bA)]
    for rule, cen, b in todo:
        out.append(dict(base, rule=rule, **score(pred, cen, label, b)))
    return out


# ======================================================================= capillary
def _cap_job(args):
    ds, kind, seed = args
    from threadpoolctl import threadpool_limits
    import multimodel_audit as M
    from perband_audit import p_hops
    c = M.Corpus(ds)
    rows = []
    with threadpool_limits(limits=1):
        U, Yt = c.windows(c.train)
        g = M.fit_model(kind, seed, U, Yt)
        for tag, hi in M.CONFIGS:
            lawcal = [n for n in c.names if M.LAWCAL_LO <= c.TP[n] <= hi]
            q = c.slopes(lawcal); top = max(lawcal, key=lambda n: c.TP[n])
            R = rates(c, lawcal, q, top, p_hops(c, lawcal))
            kC = float(np.linalg.norm(q - .5))
            for t in [n for n in c.names if c.TP[n] > hi]:
                d = float(c.lp[t] - c.lp[top])
                pred = g(np.array([[c.lp[t]]]))[0]
                base = dict(system='capillary', group=tag, dataset=ds, model=kind, seed=seed,
                            unit=ds, bin=t, delta=d)
                rows += rule_rows(base, pred, c.TM[t], c.TM[top] + q * d, None, R, d,
                                  extra=[('C', c.TM[top] + q * d, kC * d)])
    return rows


def capillary():
    import multimodel_audit as M
    rows = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for rr in ex.map(_cap_job, [(ds, k, s) for ds in M.DATASETS for k, s in M.MODELS]):
            rows += rr
    import csv
    ref = {(r['dataset'], r['config'], r['model'], r['seed'], r['trial']): r
           for r in csv.DictReader(open(HERE / 'multimodel' / 'rows.csv'))}
    for r in rows:
        if r['rule'] == 'C':
            s = ref[(r['dataset'], r['group'], r['model'], str(r['seed']), r['bin'])]
            assert abs(r['S'] - float(s['S'])) < 1e-8 and abs(r['e'] - float(s['e'])) < 1e-8
    print('capillary: %d row-rule pairs, gate passed' % len(rows), flush=True)
    return rows


# ============================================================================ wind
def wind(year):
    import allowance_audit as AA
    from perband_audit import e1_hops
    for y in (2018, 2019):
        AA.YEARS[y] = HERE / 'wind' / str(y)
    units = AA.units_of(year)
    preds = pickle.load(open(HERE / 'perband' / ('wind_preds_%d.pkl' % year), 'rb'))
    cache, rows = {}, []
    for r in preds:
        u = r['unit']; c = units[u][2]
        if u not in cache:
            q, top = AA.ceiling_line(c)
            R = rates(c, c.band('LAWCAL'), q, top, e1_hops(c))
            assert abs(R['k'] - AA.e1_kappa(c)[0]) < 1e-12
            cache[u] = (q, top, R)
        q, top, R = cache[u]
        d = r['delta']; line = c.TM[top] + q * d
        base = dict(system='wind', group='%d%s' % (year, r['scen']), year=year, scen=r['scen'],
                    model=r['model'], unit=u, bin=r['bin'], delta=d)
        rows += rule_rows(base, r['pred'], c.TM[r['bin']], line, np.minimum(line, WIND_CAP), R, d)
    print('wind %d: %d row-rule pairs' % (year, len(rows)), flush=True)
    return rows


# =========================================================================== solar
def solar():
    import pv_audit as PA
    from perband_audit import e1_hops
    units = {name: (year, c) for name, year, comb, c in PA.units()}
    prem = json.loads((HERE / 'pv' / 'premise.json').read_text())['rows']
    lab_rows, cache = [], {}

    def prep(name):
        if name not in cache:
            y, c = units[name]
            q, top = PA.law(c)
            cache[name] = (c, q, top, rates(c, c.band('LAWCAL'), q, top, e1_hops(c)))
        return cache[name]

    def centres(c, q, top, n):
        d = c.lp[n] - c.lp[top]
        line = c.TM[top] + q * d
        brk = c.TM[top] + q * (min(c.lp[n], math.log(G_CLIP)) - c.lp[top])
        return d, line, brk

    # Label-only premise coverage, every unit (no surrogate needed).
    for p in prem:
        c, q, top, R = prep(p['unit'])
        d, line, brk = centres(c, q, top, p['bin'])
        assert abs(R['k'] * 2 * d - p['beta_E1']) < 1e-9
        for rule, cen, b in (('L', line, 2 * R['k'] * d), ('A', line, R['r0'] + 2 * R['kA'] * d),
                             ('K-L', brk, 2 * R['k'] * d), ('K-A', brk, R['r0'] + 2 * R['kA'] * d)):
            lab_rows.append(dict(system='solar', group=p['scenario'], year=p['year'], rule=rule,
                                 prem=bool(np.linalg.norm(c.TM[p['bin']] - cen) <= b + 1e-10)))
    # Certificate rows 2018-19: recover the scalar prediction from stored D and e.
    rows = []
    for year in (2018, 2019):
        for r in json.loads((HERE / 'pv' / ('cert_%d.json' % year)).read_text())['rows']:
            c, q, top, R = prep(r['unit'])
            d, line, brk = centres(c, q, top, r['bin'])
            y = float(c.TM[r['bin']][0])
            cand = [line[0] + s * r['D'] for s in (1, -1)]
            ok = [p for p in cand if abs(abs(p - y) - r['e']) < 1e-9]
            assert ok, 'prediction not recoverable'
            pred = np.array([ok[0]])
            base = dict(system='solar', group='%d%s' % (year, r['scenario']), year=year, scen=r['scenario'],
                        model=r['model'], unit=r['unit'], bin=r['bin'], delta=d)
            rows += rule_rows(base, pred, c.TM[r['bin']], line, brk, R, d)
    print('solar: %d label rows, %d certificate row-rule pairs' % (len(lab_rows), len(rows)), flush=True)
    return lab_rows, rows


# ========================================================================== report
ORDER = ['C', 'L', 'A', 'K-L', 'K-A']


def summarise(rows):
    S = np.array([r['S'] for r in rows]); e = np.array([r['e'] for r in rows])
    p = np.array([r['prem'] for r in rows]); v = S <= e + 1e-9
    b = np.array([r['beta'] for r in rows]); z = np.array([r['zeta'] for r in rows])
    return dict(rows=len(rows), premise=float(p.mean()), valid=float(v.mean()),
                fail_prem=int((p & ~v).sum()), Se=float(np.median(S / e)),
                silent=float(np.mean(S <= 0.01)), beta_over_zeta=float(np.median(b / np.maximum(z, 1e-12))))


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rows = capillary()
    for y in (2016, 2017, 2018, 2019):
        rows += wind(y)
    lab, srows = solar()
    rows += srows
    pickle.dump(dict(rows=rows, label=lab), open(OUT / 'rows.pkl', 'wb'))
    res, lines = {}, []
    hdr = '%-26s %-5s %6s %8s %7s %6s %7s %7s %9s' % ('group', 'rule', 'rows', 'premise', 'valid',
                                                       'fail|p', 'S/e', 'silent', 'beta/zeta')
    titles = [('capillary', 'CAPILLARY (7 representations, exploratory)'),
              ('wind', 'WIND (2016-18 development, 2019 confirmation)'),
              ('solar', 'SOLAR certificate 2018-19 (exploratory)')]
    for sysn, title in titles:
        lines += ['', title, hdr, '-' * len(hdr)]
        rs = [r for r in rows if r['system'] == sysn]
        for g in sorted({r['group'] for r in rs}):
            for rule in [x for x in ORDER if any(r['rule'] == x and r['group'] == g for r in rs)]:
                s = summarise([r for r in rs if r['group'] == g and r['rule'] == rule])
                res['%s|%s|%s' % (sysn, g, rule)] = s
                lines.append('%-26s %-5s %6d %8.3f %7.3f %6d %7.2f %7.3f %9.2f' % (
                    g, rule, s['rows'], s['premise'], s['valid'], s['fail_prem'], s['Se'], s['silent'],
                    s['beta_over_zeta']))
    lines += ['', 'SOLAR label-only premise coverage, all 813 units (exploratory)']
    for g in ('A', 'B'):
        for rule in ('L', 'A', 'K-L', 'K-A'):
            v = [r['prem'] for r in lab if r['group'] == g and r['rule'] == rule]
            res['solar_label|%s|%s' % (g, rule)] = float(np.mean(v))
            lines.append('  %s  %-4s %.3f  (n=%d)' % (g, rule, np.mean(v), len(v)))
    lines.append('\nfail|p = bound failures where the premise held (Proposition 1: must be 0). '
                 'beta/zeta = median allowance over law residual (> 1 covers).')
    txt = '\n'.join(lines)
    (OUT / 'report.txt').write_text(txt); (OUT / 'results.json').write_text(json.dumps(res, indent=1))
    print(txt); print('(%.0fs)' % (time.time() - t0))


if __name__ == '__main__':
    main()
