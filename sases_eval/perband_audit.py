"""Per-output law allowance vs the sphere allowance. Protocol: PERBAND_PROTOCOL.md.

Same certificate, a sum of three things per output:
    S_j = max(D_j - b_j - beta_j, 0),  S = ||S_vec||,   premise |zeta_j| <= beta_j for all j
against the sphere S = max(D - b - beta, 0), premise ||zeta|| <= beta. b = 0 in the
ceiling form (centre built from measured LAWCAL labels).

  python perband_audit.py capillary
  python perband_audit.py wind 2016 2017 2018      (development)
  python perband_audit.py wind 2019                (confirmation; builds records first)
  python perband_audit.py report
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

HERE = Path(__file__).resolve().parent
OUT = HERE / 'perband'
ALPHA = 0.10


# ------------------------------------------------------------------ rule pieces
def hop_kappas(c, hops):
    """(sphere kappa', per-output kappa' vector) from hops [(fit_bins, held_bins)]."""
    sph, vec = [], []
    for fit, held in hops:
        if len(fit) < 2:
            continue
        q = c.slopes(fit); top = fit[-1]
        for n in held:
            d = c.lp[n] - c.lp[top]
            z = c.TM[n] - (c.TM[top] + q * d)
            sph.append(np.linalg.norm(z) / d); vec.append(np.abs(z) / d)
    return float(max(sph)), np.max(np.array(vec), 0)


def p_hops(c, lawcal):
    b = sorted(lawcal, key=lambda n: c.TP[n])
    return [(b[:3], b[3:]), (b[:2], b[2:])]


def e1_hops(c):
    lab = sorted(c.band('TRAIN') + c.band('LAWCAL'), key=lambda n: c.TP[n])
    return [(lab[i:i + 4], lab[i + 4:]) for i in range(len(lab) - 3)]


def conformal_upper(scores):
    n = len(scores)
    k = math.ceil((n + 1) * (1 - ALPHA))
    return float(np.sort(scores)[k - 1]) if k <= n else math.inf


def certs(pred, centre, label, beta, bvec):
    """Sphere and per-output certificates, premises and error for one row."""
    D = pred - centre; z = label - centre
    S_s = max(float(np.linalg.norm(D)) - beta, 0.0)
    S_p = float(np.linalg.norm(np.maximum(np.abs(D) - bvec, 0.0)))
    e = float(np.linalg.norm(pred - label))
    prem_s = bool(np.linalg.norm(z) <= beta + 1e-10)
    prem_p = bool(np.all(np.abs(z) <= bvec + 1e-10))
    if prem_s:
        assert S_s <= e + 1e-8, 'sphere bound failed where its premise held'
    if prem_p:
        assert S_p <= e + 1e-8, 'per-output bound failed where its premise held'
    return dict(S_sph=S_s, S_pb=S_p, e=e, prem_sph=prem_s, prem_pb=prem_p,
                abst_sph=math.isinf(beta), abst_pb=bool(np.isinf(bvec).any()))


# ======================================================================= capillary
def _cap_job(args):
    ds, kind, seed = args
    from threadpoolctl import threadpool_limits
    import multimodel_audit as M
    from wind_paper_rule import kappa_fit
    c = M.Corpus(ds)
    rows = []
    with threadpool_limits(limits=1):
        U, Yt = c.windows(c.train)
        g = M.fit_model(kind, seed, U, Yt)
        for tag, hi in M.CONFIGS:
            lawcal = [n for n in c.names if M.LAWCAL_LO <= c.TP[n] <= hi]
            test = [n for n in c.names if c.TP[n] > hi]
            q = c.slopes(lawcal); top = max(lawcal, key=lambda n: c.TP[n])
            kP, kPv = hop_kappas(c, p_hops(c, lawcal))
            assert abs(kP - kappa_fit(c, lawcal)) < 1e-12
            for t in test:
                d = float(c.lp[t] - c.lp[top])
                pred = g(np.array([[c.lp[t]]]))[0]
                centre = c.TM[top] + q * d
                base = dict(dataset=ds, config=tag, model=kind, seed=seed, trial=t, P=c.TP[t], delta=d)
                for rule, beta, bvec in (('C', float(np.linalg.norm(q - .5)) * d, np.abs(q - .5) * d),
                                         ('P', 2 * kP * d, 2 * kPv * d)):
                    r = dict(base, rule=rule, **certs(pred, centre, c.TM[t], beta, bvec))
                    rows.append(r)
    return rows


def capillary():
    import multimodel_audit as M
    jobs = [(ds, k, s) for ds in M.DATASETS for k, s in M.MODELS]
    rows = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for rr in ex.map(_cap_job, jobs):
            rows += rr
    # Gate: sphere rule C must reproduce the stored multimodel ceiling S and e.
    import csv
    ref = {(r['dataset'], r['config'], r['model'], r['seed'], r['trial']): r
           for r in csv.DictReader(open(HERE / 'multimodel' / 'rows.csv'))}
    n = 0
    for r in rows:
        if r['rule'] != 'C':
            continue
        s = ref[(r['dataset'], r['config'], r['model'], str(r['seed']), r['trial'])]
        assert abs(r['S_sph'] - float(s['S'])) < 1e-8 and abs(r['e'] - float(s['e'])) < 1e-8, s
        n += 1
    print('capillary gate passed on %d rows' % n)
    OUT.mkdir(exist_ok=True)
    pickle.dump(rows, open(OUT / 'capillary_rows.pkl', 'wb'))
    return rows


# ============================================================================ wind
def build_2019():
    import build_wind
    out = HERE / 'wind' / '2019'
    if (out / 'records.npz').exists():
        return
    build_wind.ARCHIVE = HERE.parent / 'external_data' / 'kelmarsh' / 'Kelmarsh_SCADA_2019_3085.zip'
    build_wind.MONTHS = range(1, 13)
    build_wind.OUT = out
    build_wind.run()


def _wind_job(args):
    name, U, P, Wm = args
    from threadpoolctl import threadpool_limits
    import wind_audit as W
    from multimodel_audit import fit_model
    c = W.Unit(U, P, Wm)
    train, lawcal = c.band('TRAIN'), c.band('LAWCAL')
    tests = {s: c.band(s) for s in ('A', 'B')}
    if not (len(train) == 4 and len(lawcal) == 4) or not any(len(v) >= 2 for v in tests.values()):
        return name, []
    q = c.slopes(lawcal); top = max(lawcal, key=lambda n: c.TP[n])
    Utr, Ytr = c.windows(train)
    rows = []
    with threadpool_limits(limits=1):
        for kind, seed in W.MODELS:
            g = fit_model(kind, seed, Utr, Ytr)
            for scen, bins in tests.items():
                if len(bins) < 2:
                    continue
                for t in bins:
                    pred = g(np.array([[c.lp[t]]]))[0]
                    rows.append(dict(unit=name, scen=scen, bin=t, model=kind, pred=pred,
                                     delta=float(c.lp[t] - c.lp[top])))
    return name, rows


def wind_preds(year):
    import allowance_audit as AA
    cache = OUT / ('wind_preds_%d.pkl' % year)
    if cache.exists():
        return pickle.load(open(cache, 'rb'))
    rec = np.load(AA.YEARS[year] / 'records.npz')
    jobs = []
    for t in sorted(set(rec['turbine'].tolist())):
        for m in sorted(set(rec['month'].tolist())):
            s = (rec['turbine'] == t) & (rec['month'] == m)
            jobs.append(('T%d-%02d' % (t, m), rec['U'][s], rec['P'][s], rec['omega'][s]))
    rows = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for name, rr in ex.map(_wind_job, jobs):
            rows += rr
    OUT.mkdir(exist_ok=True)
    pickle.dump(rows, open(cache, 'wb'))
    return rows


def fleet_vectors(year):
    """(year, unit) -> {bin: zeta vector} over every bin above the ceiling."""
    import allowance_audit as AA
    out = {}
    for u, (t, m, c) in AA.units_of(year).items():
        q, top = AA.ceiling_line(c)
        out[(year, u)] = {n: c.TM[n] - (c.TM[top] + q * (c.lp[n] - c.lp[top]))
                          for n in c.names if c.lp[n] > c.lp[top]}
    return out


def e3_betas(pool, n):
    """Sphere and joint per-output E3 allowances at bin n from a fleet pool."""
    keys = sorted(k for k in pool if n in pool[k])
    Z = np.array([pool[k][n] for k in keys]) if keys else np.zeros((0, 2))
    beta = conformal_upper(np.linalg.norm(Z, axis=1)) if len(Z) else math.inf
    half_s, half_q = Z[0::2], Z[1::2]
    if len(half_s) == 0 or len(half_q) == 0:
        return beta, np.full(2, math.inf)
    sig = np.median(np.abs(half_s), 0) + 1e-9
    qh = conformal_upper(np.max(np.abs(half_q) / sig, 1))
    return beta, qh * sig


def wind(year):
    import allowance_audit as AA
    import wind_audit as W
    from wind_paper_rule import kappa_fit
    for y in (2018, 2019):
        AA.YEARS[y] = HERE / 'wind' / str(y)
    if year == 2019:
        build_2019()
    preds = wind_preds(year)
    units = AA.units_of(year)
    # Gate: raw defect against the stored audit rows where they exist.
    f = AA.YEARS[year] / 'results.json'
    if f.exists():
        ref = {(r['unit'], r['scenario'], r['bin'], r['model']): r['raw_defect']
               for r in json.loads(f.read_text())['rows']}
        for r in preds:
            c = units[r['unit']][2]; q, top = AA.ceiling_line(c)
            D = np.linalg.norm(r['pred'] - (c.TM[top] + q * r['delta']))
            assert abs(D - ref[(r['unit'], r['scen'], r['bin'], r['model'])]) < 1e-8
        print('wind %d gate passed on %d rows' % (year, len(preds)))
    # Fleets, as in allowance_audit / learned_allowance.
    if year == 2016:
        z16 = fleet_vectors(2016)
        fleet = lambda u: {k: v for k, v in z16.items()
                           if k[1][1] != u[1] and k[1][3:] != u[3:]}
    else:
        pool = {}
        for y in range(2016, year):
            pool.update(fleet_vectors(y))
        fleet = lambda u: pool
    kc, e3c = {}, {}
    rows = []
    for r in preds:
        u = r['unit']; t, m, c = units[u]
        if u not in kc:
            lawcal = c.band('LAWCAL'); q, top = AA.ceiling_line(c)
            kP, kPv = hop_kappas(c, p_hops(c, lawcal))
            kE, kEv = hop_kappas(c, e1_hops(c))
            assert abs(kP - kappa_fit(c, lawcal)) < 1e-12 and abs(kE - AA.e1_kappa(c)[0]) < 1e-12
            kc[u] = (q, top, kP, kPv, kE, kEv)
        q, top, kP, kPv, kE, kEv = kc[u]
        d = r['delta']; centre = c.TM[top] + q * d; label = c.TM[r['bin']]
        if (u, r['bin']) not in e3c:
            e3c[(u, r['bin'])] = e3_betas(fleet(u), r['bin'])
        b3, b3v = e3c[(u, r['bin'])]
        base = dict(year=year, unit=u, scen=r['scen'], bin=r['bin'], model=r['model'], delta=d)
        for rule, beta, bvec in (('C', float(np.linalg.norm(q - W.Q_TH)) * d, np.abs(q - W.Q_TH) * d),
                                 ('P', 2 * kP * d, 2 * kPv * d), ('E1', 2 * kE * d, 2 * kEv * d),
                                 ('E3', b3, b3v)):
            rows.append(dict(base, rule=rule, **certs(r['pred'], centre, label, beta, bvec)))
    pickle.dump(rows, open(OUT / ('wind_rows_%d.pkl' % year), 'wb'))
    print('wind %d: %d row-rule pairs' % (year, len(rows)))
    return rows


# ========================================================================== report
def summarise(rows):
    S_s = np.array([r['S_sph'] for r in rows]); S_p = np.array([r['S_pb'] for r in rows])
    e = np.array([r['e'] for r in rows])
    ps = np.array([r['prem_sph'] for r in rows]); pp = np.array([r['prem_pb'] for r in rows])
    vs, vp = S_s <= e + 1e-9, S_p <= e + 1e-9
    both = S_s > 1e-12
    return dict(
        rows=len(rows),
        premise_sph=float(ps.mean()), premise_pb=float(pp.mean()),
        valid_sph=float(vs.mean()), valid_pb=float(vp.mean()),
        fail_prem_sph=int((ps & ~vs).sum()), fail_prem_pb=int((pp & ~vp).sum()),
        Se_sph=float(np.median(S_s / e)), Se_pb=float(np.median(S_p / e)),
        silent_sph=float(np.mean(S_s <= 0.01)), silent_pb=float(np.mean(S_p <= 0.01)),
        pb_larger=float(np.mean(S_p > S_s + 1e-12)),
        ratio_med=float(np.median(S_p[both] / S_s[both])) if both.any() else None,
        abstain_sph=float(np.mean([r['abst_sph'] for r in rows])),
        abstain_pb=float(np.mean([r['abst_pb'] for r in rows])))


def report():
    out, lines = {}, []
    fmt = '%-34s %6s  %5.3f %5.3f   %5.3f %5.3f   %3d %3d   %5.2f %5.2f   %5.3f %5.3f   %5.2f  %s'
    hdr = ('%-34s %6s  %-11s   %-11s   %-7s   %-11s   %-11s   %-5s  %s'
           % ('group / rule', 'rows', 'premise s/p', 'valid s/p', 'fail|pr', 'S/e s/p', 'silent s/p',
              'pb>s', 'S_pb/S_s'))
    def block(title, rows, key):
        lines.append('\n' + title); lines.append(hdr); lines.append('-' * len(hdr))
        for g in sorted({key(r) for r in rows}):
            for rule in sorted({r['rule'] for r in rows if key(r) == g}, key=['C', 'P', 'E1', 'E3'].index):
                s = summarise([r for r in rows if key(r) == g and r['rule'] == rule])
                out['%s|%s|%s' % (title, g, rule)] = s
                lines.append(fmt % ('%s  %s' % (g, rule), s['rows'], s['premise_sph'], s['premise_pb'],
                                    s['valid_sph'], s['valid_pb'], s['fail_prem_sph'], s['fail_prem_pb'],
                                    s['Se_sph'], s['Se_pb'], s['silent_sph'], s['silent_pb'], s['pb_larger'],
                                    '%.2f' % s['ratio_med'] if s['ratio_med'] else '--'))
    cap = OUT / 'capillary_rows.pkl'
    if cap.exists():
        R = pickle.load(open(cap, 'rb'))
        block('CAPILLARY, all 7 representations', R, lambda r: r['config'])
        block('CAPILLARY, ctr12 (the paper representation)', [r for r in R if r['dataset'] == 'ctr12'],
              lambda r: r['config'])
    for y in (2016, 2017, 2018, 2019):
        f = OUT / ('wind_rows_%d.pkl' % y)
        if f.exists():
            tag = 'CONFIRMATION' if y == 2019 else 'development'
            block('WIND %d (%s)' % (y, tag), pickle.load(open(f, 'rb')),
                  lambda r: {'A': 'A below rated', 'B': 'B rated'}[r['scen']])
    lines.append('\ns = sphere (current), p = per-output. fail|pr = bound failures where that premise held '
                 '(must be 0).\npb>s = share of rows where the per-output S is larger; S_pb/S_s = median ratio '
                 'where the sphere S > 0.')
    txt = '\n'.join(lines)
    (OUT / 'report.txt').write_text(txt)
    (OUT / 'results.json').write_text(json.dumps(out, indent=1))
    print(txt)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    if sys.argv[1] == 'capillary':
        capillary()
    elif sys.argv[1] == 'wind':
        for y in sys.argv[2:]:
            wind(int(y))
    else:
        report()
    print('(%.0fs)' % (time.time() - t0))
