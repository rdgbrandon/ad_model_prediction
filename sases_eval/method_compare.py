"""Every law-allowance rule on every dataset, one certificate. Exploratory (no new protocol):
the rules are the ones already defined in ALLOWANCE_PROTOCOL, BOUND_SHAPE_PROTOCOL,
SATURATING_PROTOCOL, KS3_PROTOCOL and LEARNED_ALLOWANCE_PROTOCOL, applied unchanged.

  python method_compare.py run <name> ...     -> compare/<name>_rows.pkl
  python method_compare.py report             -> compare/results.json, report.txt

Same units, same nine surrogates and same three-term certificate as multi_audit.py
(S = max(D_T - b_T - beta - r_T, 0), anchor at the top training bin). Only beta and the
law centre change. Fleet rules (E3, F-GBT, F-NN, K-S3) calibrate on OTHER machines in
OTHER periods (never the scored machine, never the scored month); K-S3y is the original
earlier-years K-S3 (Kelmarsh only). beta never reads the scored unit's test-bin labels.
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

import multi_audit as MA
from perband_audit import hop_kappas, p_hops

HERE = Path(__file__).resolve().parent
OUT = HERE / 'compare'
ALPHA = 0.10
LINE_RULES = ['C', 'P', 'E1', 'E2', 'A', 'Z', 'E3', 'E3/95', 'F-GBT', 'F-NN']
CAP_RULES = ['K-L', 'K-S1', 'K-S3', 'K-S3/95', 'K-S3y']
RULES = LINE_RULES + CAP_RULES
NAMES = {'C': 'theory distance', 'P': 'short hops (paper Eq. 5)', 'E1': 'long hops (= straight law L)',
         'E2': 'long hops + curvature', 'A': 'offset + slope', 'Z': 'monotone saturation',
         'E3': 'fleet conformal 90%', 'E3/95': 'fleet conformal 95%', 'F-GBT': 'learned fleet scale (boosted trees)',
         'F-NN': 'learned fleet scale (neural net)', 'K-L': 'capped law, growing',
         'K-S1': 'capped law, frozen at cap', 'K-S3': 'K-S1, shrunk to fleet past cap (90%)',
         'K-S3/95': 'K-S1, shrunk to fleet past cap (95%)',
         'K-S3y': 'K-S3 from earlier years'}


def q90(z, alpha=ALPHA):
    n = len(z); k = math.ceil((n + 1) * (1 - alpha))
    return float(np.partition(np.asarray(z), k - 1)[k - 1]) if n >= 9 and k <= n else math.inf


# ======================================================================= per-unit law kit
def _kappa(c, hops):
    """hop_kappas, skipping zero-length hops (repeated drive powers in the capillary trials)."""
    out = 0.0
    for fit, held in hops:
        if len(fit) < 2:
            continue
        q = c.slopes(fit); top = fit[-1]
        for n in held:
            d = c.lp[n] - c.lp[top]
            if d > 1e-9:
                out = max(out, float(np.linalg.norm(c.TM[n] - (c.TM[top] + q * d))) / d)
    return out


def kit(c, TR, LC, q_th, line, capped, dstar):
    """Calibration-only quantities: everything from TRAIN and LAWCAL bins."""
    q = c.slopes(LC); top = max(LC, key=lambda n: c.TP[n])
    lab = sorted(set(TR) | set(LC), key=lambda n: c.TP[n])
    hops = [(lab[i:i + 4], lab[i + 4:]) for i in range(len(lab) - 3)]
    k1 = _kappa(c, hops)
    kP = _kappa(c, p_hops(c, LC))
    r0 = max(float(np.linalg.norm(c.TM[n] - line(c.lp[n] - c.lp[top]))) for n in LC)
    kA = 0.0
    for fit, held in hops:
        qq = c.slopes(fit); tt = fit[-1]
        for n in held:
            d = c.lp[n] - c.lp[tt]
            if d <= 1e-9:
                continue
            kA = max(kA, max(float(np.linalg.norm(c.TM[n] - (c.TM[tt] + qq * d))) - r0, 0.0) / d)
    x = np.array([c.lp[n] for n in lab]); Y = np.array([c.TM[n] for n in lab])
    quad = [np.polyfit(x, Y[:, j], 2) for j in range(Y.shape[1])]
    rms = float(np.sqrt(np.mean([np.sum((c.TM[n] - line(c.lp[n] - c.lp[top])) ** 2) for n in LC])))
    kC = float(np.linalg.norm(q - q_th)) if q_th is not None else math.inf
    return dict(q=q, top=top, k1=k1, kP=kP, r0=r0, kA=kA, quad=quad, rms=rms, kC=kC,
                line=line, capped=capped, dstar=dstar)


def formula_betas(c, K, n):
    d = c.lp[n] - c.lp[K['top']]
    quad = np.array([np.polyval(p, c.lp[n]) for p in K['quad']])
    curv = float(np.linalg.norm(quad - K['line'](d)))
    return {'C': K['kC'] * d, 'P': 2 * K['kP'] * d, 'E1': 2 * K['k1'] * d,
            'E2': max(2 * K['k1'] * d, 2 * curv), 'A': K['r0'] + 2 * K['kA'] * d,
            'Z': float(np.linalg.norm(K['q'])) * d,
            'K-L': 2 * K['k1'] * d, 'K-S1': 2 * K['k1'] * min(d, K['dstar'])}


def features(c, K, n):
    d = c.lp[n] - c.lp[K['top']]
    curv = [p[0] for p in K['quad']]
    return np.r_[d, c.lp[n], K['q'], c.TM[K['top']], curv, K['k1'], K['rms']]


def machine_period(name, uname):
    if name == 'pv9068':                                   # 'YYYY-MM-label'
        y, m, lab = uname.split('-', 2)
        return lab, y + m
    a, b = uname.split('-')[-2:]
    return a, b


# ======================================================================= stage 1: betas
def fleet_learned(kind, rows, mach, band_of):
    """beta for every (unit, bin) row, leave-one-machine-out normalised split conformal.
    Scale fitted on half the other machines, scores on the other half, Mondrian by band;
    calibration scores from the scored unit's own period are dropped."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.neural_network import MLPRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    X = np.stack([r['x'] for r in rows]); z = np.array([r['zeta_line'] for r in rows])
    M = np.array([r['machine'] for r in rows]); Pd = np.array([r['period'] for r in rows])
    B = np.array([band_of(r['bin']) for r in rows])
    out = np.full(len(rows), math.inf)
    for m in sorted(set(M)):
        others = sorted(set(M) - {m})
        if len(others) < 2:
            continue
        rng = np.random.default_rng(abs(hash(str(m))) % 2 ** 32)
        rng.shuffle(others)
        fitm = np.isin(M, others[:len(others) // 2]); calm = np.isin(M, others[len(others) // 2:])
        if kind == 'F-GBT':
            mod = GradientBoostingRegressor(n_estimators=200, max_depth=2, learning_rate=0.05, subsample=0.8,
                                            random_state=0)
        else:
            mod = make_pipeline(StandardScaler(), MLPRegressor((16, 16), alpha=1e-2, solver='lbfgs',
                                                               max_iter=3000, random_state=0))
        mod.fit(X[fitm], np.log(np.maximum(z[fitm], 1e-4)))
        lo, hi = max(float(z[fitm].min()), 1e-4), float(z[fitm].max())
        sig = lambda XX: np.clip(np.exp(mod.predict(XX)), lo, hi)
        sc = z[calm] / sig(X[calm]); scB, scP = B[calm], Pd[calm]
        tgt = np.where(M == m)[0]
        st = sig(X[tgt])
        for i, s in zip(tgt, st):
            pool = sc[(scB == B[i]) & (scP != Pd[i])]
            out[i] = s * q90(pool)
    return out


def stage1(name, units):
    meta = MA.DATASETS[name]
    q_th = np.array(meta['q_th'], float)
    lo_B = MA.WIND_BANDS if meta['kind'] == 'wind' else MA.PV_BANDS
    band_of = lambda n: next((k for k, (a, b) in lo_B.items() if a <= n - (0.25 if meta['kind'] == 'wind' else 25.0) < b), 'gap')
    kits, rows = {}, []
    for u, c in units.items():
        q, top, kappa, line, capped, ds = MA.law_parts(name, c)
        K = kit(c, c.band('TRAIN'), c.band('LAWCAL'), q_th, line, capped, ds)
        assert abs(K['k1'] - kappa) < 1e-12 and K['top'] == top
        kits[u] = K
        mach, per = machine_period(name, u)
        for n in c.names:
            d = c.lp[n] - c.lp[top]
            if d > 0:
                rows.append(dict(unit=u, bin=n, machine=mach, period=per, delta=d, x=features(c, K, n),
                                 zeta_line=float(np.linalg.norm(c.TM[n] - line(d))),
                                 zeta_cap=float(np.linalg.norm(c.TM[n] - capped(d)))))
    # fleet conformal by bin: E3 on the straight law, K-S3 on the capped law
    betas = {}
    by_bin = {}
    for i, r in enumerate(rows):
        by_bin.setdefault(r['bin'], []).append(i)
    for i, r in enumerate(rows):
        pool = [rows[j] for j in by_bin[r['bin']] if rows[j]['machine'] != r['machine'] and rows[j]['period'] != r['period']]
        zl, zc = [p['zeta_line'] for p in pool], [p['zeta_cap'] for p in pool]
        betas[(r['unit'], r['bin'])] = {'E3': q90(zl), 'E3/95': q90(zl, 0.05),
                                        'q90cap': q90(zc), 'q95cap': q90(zc, 0.05)}
    t0 = time.time()
    for kind in ('F-GBT', 'F-NN'):
        bb = fleet_learned(kind, rows, None, band_of)
        for r, b in zip(rows, bb):
            betas[(r['unit'], r['bin'])][kind] = float(b)
    print('  %s learned fleet scales (%.0fs)' % (name, time.time() - t0), flush=True)
    yearly = None
    if name == 'kelmarsh':                                 # original K-S3: Kelmarsh 2016-2019
        import ks3_audit as K3
        yearly = K3.fleet_pool(range(2016, 2020))
    for u, c in units.items():
        K = kits[u]
        for n in c.names:
            d = c.lp[n] - c.lp[K['top']]
            if d <= 0:
                continue
            fb = betas[(u, n)]; fb.update(formula_betas(c, K, n))
            b1 = fb['K-S1']
            fb['K-S3'] = b1 if d <= K['dstar'] else min(2 * K['k1'] * K['dstar'], fb['q90cap'])
            fb['K-S3/95'] = b1 if d <= K['dstar'] else min(2 * K['k1'] * K['dstar'], fb['q95cap'])
            fb['K-S3y'] = (b1 if d <= K['dstar'] else min(2 * K['k1'] * K['dstar'], yearly.get(n, math.inf))) \
                if yearly is not None else math.nan
    return kits, betas


# ======================================================================= stage 2: certificates
def _job(args):
    name, uname, c, K, B = args
    from threadpoolctl import threadpool_limits
    from multimodel_audit import fit_model
    K = dict(K); _, _, _, K['line'], K['capped'], _ = MA.law_parts(name, c)     # lambdas do not pickle
    tests = {s: c.band(s) for s in ('A', 'B') if len(c.band(s)) >= 2}
    if not tests:
        return []
    U, Yt = c.windows(c.band('TRAIN')); m = Yt.shape[1]
    top = K['top']; aT = max(c.band('TRAIN'), key=lambda n: c.TP[n]); dT = c.lp[aT] - c.lp[top]
    rows = []
    with threadpool_limits(limits=1):
        for kind, seed in MA.MODELS:
            g = fit_model(kind, seed, U, Yt)
            pr = lambda u: np.asarray(g(np.array([[u]]))).reshape(-1)[:m]
            fa, fT = pr(c.lp[top]), pr(c.lp[aT])
            for scen, bins in tests.items():
                for t in bins:
                    d = c.lp[t] - c.lp[top]; fx = pr(c.lp[t])
                    for rule in RULES:
                        beta = B[(uname, t)][rule]
                        if isinstance(beta, float) and math.isnan(beta):
                            continue
                        cf = K['capped'] if rule.startswith('K-') else K['line']
                        r = MA.cert(fx, fa, c.TM[top], c.TM[t], cf(d), cf(0), beta, fT, c.TM[aT], cf(dT))
                        rows.append(dict(unit=uname, scen=scen, bin=t, model=kind, rule=rule, delta=d,
                                         beyond=bool(d > K['dstar']), ST=r['ST'], Sc=r['Sc'], e=r['e'],
                                         zeta=r['zeta'], beta=beta, prem=r['prem']))
    return rows


def _cap_job(args):
    import multimodel_audit as M
    kind, seed = args
    from threadpoolctl import threadpool_limits
    c = M.Corpus('ctr12')
    rows = []
    with threadpool_limits(limits=1):
        U, Yt = c.windows(c.train)
        g = M.fit_model(kind, seed, U, Yt)
        pr = lambda u: g(np.array([[u]]))[0]
        for tag, hi in M.CONFIGS:
            LC = [n for n in c.names if M.LAWCAL_LO <= c.TP[n] <= hi]
            q = c.slopes(LC); top = max(LC, key=lambda n: c.TP[n])
            line = lambda d, q=q, top=top: c.TM[top] + q * d
            K = kit(c, c.train, LC, np.full(c.B, 0.5), line, line, math.inf)
            aT = max(c.train, key=lambda n: c.TP[n]); dT = c.lp[aT] - c.lp[top]
            fa, fT = pr(c.lp[top]), pr(c.lp[aT])
            for t in [n for n in c.names if c.TP[n] > hi]:
                d = c.lp[t] - c.lp[top]; fx = pr(c.lp[t])
                fb = formula_betas(c, K, t)
                for rule in ('C', 'P', 'E1', 'E2', 'A', 'Z'):
                    r = MA.cert(fx, fa, c.TM[top], c.TM[t], line(d), line(0), fb[rule], fT, c.TM[aT], line(dT))
                    rows.append(dict(unit='ctr12|' + tag, scen=tag, bin=t, model='%s#%d' % (kind, seed), rule=rule,
                                     delta=d, beyond=False, ST=r['ST'], Sc=r['Sc'], e=r['e'], zeta=r['zeta'],
                                     beta=fb[rule], prem=r['prem']))
    return rows


def run(name):
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    if name == 'capillary':
        import multimodel_audit as M
        rows = []
        with ProcessPoolExecutor(max_workers=16) as ex:
            for rr in ex.map(_cap_job, M.MODELS):
                rows += rr
    else:
        units = MA.load_units(name)
        kits, B = stage1(name, units)
        strip = lambda K: {k: v for k, v in K.items() if k not in ('line', 'capped')}
        jobs = [(name, u, c, strip(kits[u]), {k: v for k, v in B.items() if k[0] == u}) for u, c in units.items()]
        print('  stage 1 done (%.0fs), %d jobs' % (time.time() - t0, len(jobs)), flush=True)
        rows = []
        with ProcessPoolExecutor(max_workers=16) as ex:
            for rr in ex.map(_job, jobs, chunksize=2):
                rows += rr
    pickle.dump(rows, open(OUT / ('%s_rows.pkl' % name), 'wb'))
    print('%s: %d units, %d rows (%.0fs)' % (name, len({r['unit'] for r in rows}), len(rows), time.time() - t0),
          flush=True)


# ======================================================================= report
def summarise(rs):
    S = np.array([r['ST'] for r in rs]); e = np.array([r['e'] for r in rs]); p = np.array([r['prem'] for r in rs])
    beta = np.array([r['beta'] for r in rs]); z = np.array([r['zeta'] for r in rs])
    bins = {}
    for r in rs:
        bins[(r['unit'], r['bin'])] = r['prem']
    v = S <= e + 1e-9
    fin = np.isfinite(beta)
    return dict(rows=len(rs), bins=len(bins), premise=float(np.mean(list(bins.values()))),
                valid=float(v.mean()), fail_prem=int((p & ~v).sum()), Se=float(np.median(S / e)),
                Se_mean=float(np.mean(S / e)), speaks=float(np.mean(S > 1e-9)),
                abstain=float(np.mean(~fin)),
                beta_over_zeta=float(np.median(beta[fin] / np.maximum(z[fin], 1e-9))) if fin.any() else math.inf)


def report():
    if not any((OUT / ('%s_rows.pkl' % n)).exists() for n in MA.DATASETS):
        print('no compare/*_rows.pkl (not committed): keeping the saved compare/results.json')
        return
    res, lines = {}, []
    hdr = '%-6s %-8s %-38s %6s %8s %7s %6s %6s %7s %7s %8s' % ('band', 'rule', 'name', 'rows', 'premise', 'valid',
                                                           'fail', 'S/e', 'speaks', 'abstain', 'beta/z')
    for name in MA.DATASETS:
        f = OUT / ('%s_rows.pkl' % name)
        if not f.exists():
            continue
        R = pickle.load(open(f, 'rb'))
        lines += ['', MA.DATASETS[name]['title'].upper(), hdr, '-' * len(hdr)]
        for scen in sorted({r['scen'] for r in R}):
            for rule in RULES:
                rs = [r for r in R if r['scen'] == scen and r['rule'] == rule]
                if not rs:
                    continue
                s = summarise(rs)
                res['%s|%s|%s' % (name, scen, rule)] = s
                lines.append('%-6s %-8s %-38s %6d %8.3f %7.3f %6d %6.2f %7.2f %7.2f %8.1f' % (
                    scen, rule, NAMES[rule], s['rows'], s['premise'], s['valid'], s['fail_prem'], s['Se'],
                    s['speaks'], s['abstain'], s['beta_over_zeta']))
    lines.append('\npremise = share of unit-bins whose law error was inside beta. valid = S <= e. '
                 'fail = failures where the premise held (must be 0).\nS/e = median share of the true error proven. '
                 'speaks = S > 0. abstain = beta infinite (too few fleet units).')
    txt = '\n'.join(lines)
    (OUT / 'report.txt').write_text(txt); (OUT / 'results.json').write_text(json.dumps(res, indent=1))
    print(txt)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    if sys.argv[1] == 'run':
        for n in sys.argv[2:]:
            run(n)
    else:
        report()
