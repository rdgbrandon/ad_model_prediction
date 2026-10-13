"""Row-level data behind the wind / PV results report (wind_pv_pdf.py).

The audits store aggregates; the figures need rows. This module rebuilds the
row-level allowances with the audits' own functions (allowance_audit,
wind_paper_rule, pv_audit), then GATES on the stored aggregates: every premise
share, validity and failure count must match wind/allowance.json and the PV
report to 1e-12, or nothing is drawn. Writes wind_pv_report/data.npz and
wind_pv_report/summary.json.
"""
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import allowance_audit as AA
import pv_audit as PA
from wind_paper_rule import kappa_fit as paper_kappa

HERE = Path(__file__).resolve().parent
OUT = HERE / 'wind_pv_report'
WIND_RULES = AA.RULES                                   # C P E1 E2 E3
PV_RULES = PA.RULES                                     # C P E1 S E3_prev E3_loyo


# ------------------------------------------------------------------ wind rows
def wind_rows(year, fleet, units):
    """allowance_audit.evaluate, row by row. Same beta per rule, same S."""
    rows = json.loads((AA.YEARS[year] / 'results.json').read_text())['rows']
    k1 = {u: AA.e1_kappa(v[2]) for u, v in units.items()}
    kp = {u: 2 * paper_kappa(v[2], v[2].band('LAWCAL')) for u, v in units.items()}
    zc, out = {}, []
    for r in rows:
        t, m, c = units[r['unit']]
        key = (r['unit'], r['bin'])
        if key not in zc:
            zc[key] = AA.zeta(c, r['bin'])
        z, d = zc[key], r['delta']
        for rule in WIND_RULES:
            if rule == 'C':
                b = r['radius']
            elif rule == 'P':
                b = kp[r['unit']] * d
            elif rule == 'E1':
                b = 2 * k1[r['unit']][0] * d
            elif rule == 'E2':
                b = max(2 * k1[r['unit']][0] * d, 2 * AA.e2_curvature(c, r['bin']))
            else:
                pool = [zz[r['bin']] for uu, zz in fleet(r['unit'], t, m).items()
                        if r['bin'] in zz]
                b = AA.conformal_upper(np.array(pool))
            S = max(r['raw_defect'] - b, 0.0)
            out.append(dict(year=year, scen=r['scenario'], rule=rule, unit=r['unit'],
                            bin=r['bin'], model=r['model'], delta=d, zeta=z, beta=b,
                            D=r['raw_defect'], e=r['e'], S=S))
    return out


def wind_growth(units):
    """(delta, zeta, U) for every bin above the LAWCAL ceiling, every unit."""
    out = []
    for u, (t, m, c) in units.items():
        q, top = AA.ceiling_line(c)
        for n in c.names:
            d = c.lp[n] - c.lp[top]
            if d > 0:
                out.append((d, AA.zeta(c, n), n))
    return np.array(out)


def wind_shape(units):
    """Bin means relative to the LAWCAL ceiling: (bin, d ln P, d ln omega)."""
    out = []
    for u, (t, m, c) in units.items():
        q, top = AA.ceiling_line(c)
        for n in c.names:
            dy = c.TM[n] - c.TM[top]
            out.append((n, dy[0], dy[1]))
    return np.array(out)


def gate_wind(rows, stored, year):
    for scen in ('A', 'B'):
        for rule in WIND_RULES:
            rs = [r for r in rows if r['scen'] == scen and r['rule'] == rule]
            prem = {(r['unit'], r['bin']): r['zeta'] <= r['beta'] + 1e-10 for r in rs}
            val = np.array([r['S'] <= r['e'] + 1e-9 for r in rs])
            cov = np.array([prem[(r['unit'], r['bin'])] for r in rs])
            s = stored[scen][rule]
            assert len(rs) == s['rows'], (year, scen, rule)
            assert abs(sum(prem.values()) / len(prem) - s['premise']) < 1e-12, (year, scen, rule)
            assert abs(val.mean() - s['validity']) < 1e-12, (year, scen, rule)
            assert int((cov & ~val).sum()) == s['fails_with_premise'] == 0
            assert abs(np.median([r['S'] / r['e'] for r in rs]) - s['median_S_over_e']) < 1e-12


def gate_paper_rule(rows):
    """The 2016 P rows must also reproduce the post hoc wind/paper_rule.json."""
    pr = json.loads((HERE / 'wind/paper_rule.json').read_text())
    for scen in ('A', 'B'):
        rs = [r for r in rows if r['scen'] == scen and r['rule'] == 'P']
        cov = np.array([r['zeta'] <= r['beta'] + 1e-10 for r in rs])
        val = np.array([r['S'] <= r['e'] + 1e-9 for r in rs])
        assert abs(cov.mean() - pr[scen]['premise']) < 1e-12
        assert abs(val.mean() - pr[scen]['validity']) < 1e-12


# -------------------------------------------------------------------- PV rows
def pv_rows():
    prem = json.loads((HERE / 'pv/premise.json').read_text())['rows']
    P = {(r['unit'], r['bin']): r for r in prem}
    out = []
    for year in (2018, 2019):
        for r in json.loads((HERE / 'pv' / ('cert_%d.json' % year)).read_text())['rows']:
            p = P[(r['unit'], r['bin'])]
            for rule in PV_RULES:
                out.append(dict(year=year, scen=r['scenario'], rule=rule, unit=r['unit'],
                                bin=r['bin'], model=r['model'], delta=p['delta'],
                                zeta=p['zeta'], beta=p['beta_' + rule], D=r['D'], e=r['e'],
                                S=r['S_' + rule], covered=p['covered_' + rule]))
    return prem, out


def gate_pv(prem, rows):
    # Label-only coverage, scenario A, against the figures quoted in pv/report.txt.
    for rule, want in (('C', 0.247), ('P', 0.899), ('E1', 0.955)):
        got = np.mean([r['covered_' + rule] for r in prem if r['scenario'] == 'A'])
        assert abs(got - want) < 5e-4, (rule, got)
    # S must be max(D - beta, 0) with the stored beta, and the premise flag must agree.
    for r in rows:
        assert abs(r['S'] - max(r['D'] - r['beta'], 0.0)) < 1e-9
        assert r['covered'] == (r['zeta'] <= r['beta'] + 1e-10)
        if r['covered']:
            assert r['S'] <= r['e'] + 1e-8


def pv_shape():
    """Bin means relative to the LAWCAL ceiling, every eligible combiner-month, and
    the SIGNED law residual (bin mean minus the LAWCAL line) above the ceiling."""
    out, signed = [], []
    for name, year, comb, c in PA.units():
        q, top = PA.law(c)
        for n in c.names:
            out.append((n, float(c.TM[n][0] - c.TM[top][0])))
            d = c.lp[n] - c.lp[top]
            if d > 0 and n >= 575:
                signed.append((n, d, float(c.TM[n][0] - (c.TM[top][0] + q[0] * d))))
    return np.array(out), np.array(signed)


def pv_signed_table(signed):
    rows = []
    for n in np.unique(signed[:, 0]):
        m = signed[:, 0] == n
        r, d = signed[m, 2], signed[m, 1]
        rows.append(dict(bin=float(n), n=int(m.sum()), delta=float(np.median(d)),
                         signed=float(np.median(r)), q25=float(np.percentile(r, 25)),
                         q75=float(np.percentile(r, 75)), above=float(np.mean(r > 0)),
                         abs_median=float(np.median(np.abs(r)))))
    return rows


# ---------------------------------------------------------------- summaries
def cp(k, n):
    lo, hi = AA.cp(k, n)
    return [lo, hi]


def summarise(rows, rules, key):
    """premise share (unit-bins), validity, fails|premise, median S/e, silent, abstain."""
    res = {}
    for g in sorted({key(r) for r in rows}):
        res[g] = {}
        for rule in rules:
            rs = [r for r in rows if key(r) == g and r['rule'] == rule]
            prem = {(r['unit'], r['bin']): r['zeta'] <= r['beta'] + 1e-10 for r in rs}
            cov = np.array([prem[(r['unit'], r['bin'])] for r in rs])
            val = np.array([r['S'] <= r['e'] + 1e-9 for r in rs])
            k, n = sum(prem.values()), len(prem)
            fin = {kk: v for kk, v in prem.items()
                   if not math.isinf(next(r['beta'] for r in rs if (r['unit'], r['bin']) == kk))}
            kf, nf = sum(fin.values()), len(fin)
            res[g][rule] = dict(
                unit_bins=n, premise=k / n, premise_ci=cp(k, n), rows=len(rs),
                committed_bins=nf, premise_committed=kf / nf if nf else None,
                premise_committed_ci=cp(kf, nf) if nf else None,
                validity=float(val.mean()), validity_ci=cp(int(val.sum()), len(val)),
                premise_rows=int(cov.sum()), fails_with_premise=int((cov & ~val).sum()),
                fails_without_premise=int((~cov & ~val).sum()),
                median_S_over_e=float(np.median([r['S'] / r['e'] for r in rs])),
                silent=float(np.mean([r['S'] <= 0.01 for r in rs])),
                abstain=float(np.mean([math.isinf(r['beta']) for r in rs])),
                median_e=float(np.median([r['e'] for r in rs])))
    return res


def competitors():
    """2016 wind, every method on the lower-bound reading; report_wind.py's definitions."""
    from scipy.stats import spearmanr
    R = json.loads((HERE / 'wind/results.json').read_text())['rows']
    out = {}
    for scen in ('A', 'B'):
        rs = [r for r in R if r['scenario'] == scen]
        e = np.array([r['e'] for r in rs])
        out[scen] = {}
        for key in ('sases', 'sample_max_heuristic', 'raw_defect', 'ols_error_heuristic'):
            v = np.array([r[key] for r in rs])
            rho, groups = [], {}
            for r in rs:
                groups.setdefault((r['unit'], r['bin']), []).append(r)
            for g in groups.values():
                x = np.array([r[key] for r in g]); y = np.array([r['e'] for r in g])
                if len(g) > 2 and np.ptp(x) > 1e-12 and np.ptp(y) > 1e-12:
                    rho.append(spearmanr(x, y).correlation)
            out[scen][key] = dict(below_e=float(np.mean(v <= e + 1e-9)),
                                  median_score_over_e=float(np.median(v / e)),
                                  rank_rho=float(np.mean(rho)))
    # Gate on the figures printed in wind/report.txt.
    for scen, key, below, rho in (('A', 'sases', .178, .985), ('A', 'sample_max_heuristic', .995, .955),
                                  ('A', 'raw_defect', .165, .986), ('B', 'sases', .171, .826)):
        assert abs(out[scen][key]['below_e'] - below) < 5e-4, (scen, key)
        assert abs(out[scen][key]['rank_rho'] - rho) < 5e-4, (scen, key)
    return out


def run():
    OUT.mkdir(exist_ok=True)
    # Wind: the two fleets exactly as allowance_audit.run builds them.
    u16, u17 = AA.units_of(2016), AA.units_of(2017)
    z16 = AA.zetas(2016)
    tm16 = {u: (int(u[1]), int(u[3:])) for u in z16}
    w16 = wind_rows(2016, lambda u, t, m: {v: zz for v, zz in z16.items()
                                           if tm16[v][0] != t and tm16[v][1] != m}, u16)
    w17 = wind_rows(2017, lambda u, t, m: z16, u17)
    stored = json.loads((HERE / 'wind/allowance.json').read_text())
    gate_wind(w16, stored['development_2016'], 2016)
    gate_wind(w17, stored['confirmation_2017'], 2017)
    gate_paper_rule(w16)
    print('wind gate passed: %d + %d row-rule pairs' % (len(w16), len(w17)), flush=True)

    prem, pv = pv_rows()
    gate_pv(prem, pv)
    print('PV gate passed: %d row-rule pairs' % len(pv), flush=True)

    wind = w16 + w17
    summary = dict(
        wind=summarise(wind, WIND_RULES, lambda r: '%d%s' % (r['year'], r['scen'])),
        pv=summarise(pv, PV_RULES, lambda r: '%d%s' % (r['year'], r['scen'])),
        pv_pooled=summarise(pv, PV_RULES, lambda r: r['scen']))
    # Label-only PV premise coverage over all years (the 813-unit analysis).
    lab = {}
    for scen in ('A', 'B'):
        rs = [r for r in prem if r['scenario'] == scen]
        z = np.array([r['zeta'] for r in rs])
        lab[scen] = dict(unit_bins=len(rs), units=len({r['unit'] for r in rs}),
                         zeta_median=float(np.median(z)), zeta_p90=float(np.percentile(z, 90)))
        for rule in PV_RULES:
            cov = np.array([r['covered_' + rule] for r in rs])
            b = np.array([r['beta_' + rule] for r in rs])
            fin = np.isfinite(b)
            combs = sorted({r['combiner'] for r in rs})
            per = [np.mean([r['covered_' + rule] for r in rs if r['combiner'] == c]) for c in combs]
            lab[scen][rule] = dict(premise=float(cov.mean()), premise_ci=cp(int(cov.sum()), len(cov)),
                                   premise_committed=float(cov[fin].mean()),
                                   premise_committed_ci=cp(int(cov[fin].sum()), int(fin.sum())),
                                   abstain=float(1 - fin.mean()),
                                   beta_over_zeta=float(np.median(b[fin] / np.maximum(z[fin], 1e-12))),
                                   combiners_ge_90=int(sum(v >= .9 for v in per)),
                                   combiners=len(per), combiner_min=float(min(per)))
    summary['pv_label'] = lab
    summary['wind_competitors_2016'] = competitors()
    summary['pv_q'] = dict(zip(('median', 'q25', 'q75'), np.percentile(
        [r['q'] for r in prem if r['scenario'] == 'A'], [50, 25, 75]).tolist()))
    summary['pv_units'] = len({r['unit'] for r in prem})
    summary['pv_years'] = sorted({r['year'] for r in prem})
    summary['wind_units'] = {'2016': len(u16), '2017': len(u17)}
    # Proposition 1 tallies: every row-rule pair whose premise held.
    for name, rows in (('wind', wind), ('pv', pv)):
        cov = np.array([r['zeta'] <= r['beta'] + 1e-10 for r in rows])
        val = np.array([r['S'] <= r['e'] + 1e-9 for r in rows])
        summary[name + '_theorem'] = dict(pairs=len(rows), premise_held=int(cov.sum()),
                                          fails_with_premise=int((cov & ~val).sum()),
                                          premise_failed=int((~cov).sum()),
                                          fails_without_premise=int((~cov & ~val).sum()))
    # Median fitted exponents per wind year (LAWCAL), from the stored rows.
    for y in (2016, 2017):
        rs = json.loads((AA.YEARS[y] / 'results.json').read_text())['rows']
        per_unit = {r['unit']: (r['q_P'], r['q_omega']) for r in rs}
        summary['wind_q_%d' % y] = np.median(np.array(list(per_unit.values())), 0).tolist()

    def arr(rows, keys):
        return {k: np.array([r[k] for r in rows]) for k in keys}
    keys = ('year', 'scen', 'rule', 'delta', 'zeta', 'beta', 'D', 'e', 'S')
    W, P = arr(wind, keys), arr(pv, keys)
    g16, g17 = wind_growth(u16), wind_growth(u17)
    pshape, psigned = pv_shape()
    summary['pv_signed'] = pv_signed_table(psigned)
    # Label-only shortfall of the predeclared wind rule (2016, consensus run's ceiling radius).
    for scen in ('A', 'B'):
        m = (W['year'] == 2016) & (W['scen'] == scen) & (W['rule'] == 'C')
        summary.setdefault('wind_shortfall_2016', {})[scen] = dict(
            radius_median=float(np.median(W['beta'][m])), zeta_median=float(np.median(W['zeta'][m])))
    # The predeclared 2016 primary result: consensus certificate, wind/results.json.
    R16 = json.loads((HERE / 'wind/results.json').read_text())['rows']
    for scen in ('A', 'B'):
        rs = [r for r in R16 if r['scenario'] == scen]
        cov = np.array([r['covered'] for r in rs]); val = np.array([r['sases'] <= r['e'] + 1e-9 for r in rs])
        units = sorted({r['unit'] for r in rs})
        ok = [all(r['sases'] <= r['e'] + 1e-9 for r in rs if r['unit'] == u) for u in units]
        summary.setdefault('wind_primary_2016', {})[scen] = dict(
            rows=len(rs), units=len(units), premise=float(cov.mean()), validity=float(val.mean()),
            units_all_valid=int(sum(ok)), units_ci=cp(int(sum(ok)), len(units)),
            median_S_over_e=float(np.median([r['sases'] / r['e'] for r in rs])),
            median_e=float(np.median([r['e'] for r in rs])))
    np.savez_compressed(
        OUT / 'data.npz',
        **{'wind_' + k: v for k, v in W.items()}, **{'pv_' + k: v for k, v in P.items()},
        wind_growth=np.vstack([g16, g17]),
        pv_growth=np.array([(r['delta'], r['zeta'], r['bin']) for r in prem]),
        wind_shape=np.vstack([wind_shape(u16), wind_shape(u17)]),
        pv_shape=pshape, pv_signed=psigned)
    summary['inputs_sha256'] = {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest() for f in (
        'wind/results.json', 'wind/2017/results.json', 'wind/allowance.json',
        'wind/paper_rule.json', 'pv/premise.json', 'pv/cert_2018.json', 'pv/cert_2019.json')}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=1, allow_nan=True))
    print('-> wind_pv_report/data.npz, summary.json')


if __name__ == '__main__':
    run()
