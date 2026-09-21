# -*- coding: utf-8 -*-
"""Stress-test Setup C (crossing anchor, law calibrated on >=4 above-break trials).

Six tests:
  1  estimator accuracy across every admissible law/test split
  2  anchor sensitivity (sweep all 12 TRAIN trials as anchor)
  3  surrogate sensitivity (3 model families x 3 seeds)
  4  premise -> conclusion (does validity track beta coverage?)
  5  planted-error control (does S rise when the model is made worse?)
  6  accurate-surrogate control (does S stay silent when the model is right?)

Surrogates and their leave-one-trial-out bounds depend only on (kind, seed),
never on the split or anchor, so they are fitted once and reused.
"""
import json, numpy as np, warnings
from itertools import combinations
warnings.filterwarnings('ignore')
from piecewise import NAMES, TP, TM, TRAIN, lp, slopes, B
from honest_beta import law_from
from capillary2 import build, ALPHA
from sases import conformal_quantile

ABOVE = sorted([n for n in NAMES if TP[n] >= 106], key=lambda n: TP[n])
DEFAULT_ANCHOR = max(TRAIN, key=lambda n: TP[n])
NSUB_MIN = 3


def splits():
    """LAWCAL = any >=4 above-break trials; TEST = every trial above LAWCAL's top."""
    out = []
    for i, top in enumerate(ABOVE):
        below = ABOVE[:i]
        test = ABOVE[i + 1:]
        if not test:
            continue
        for r in range(NSUB_MIN, len(below) + 1):
            for sub in combinations(below, r):
                out.append((list(sub) + [top], test))
    return out


def kappa_defensible(lawcal, anchor):
    """Upper quantile of zeta/delta over holdouts whose sub-law used >=3 trials."""
    srt = sorted(lawcal, key=lambda n: TP[n])
    rs = []
    for h in srt:
        if h == anchor:
            continue
        lower = [t for t in srt if TP[t] < TP[h] and t != anchor]
        for r in range(NSUB_MIN, len(lower) + 1):
            for sub in combinations(lower, r):
                d = np.log(TP[h]) - max(lp[s] for s in sub)
                if d <= 1e-9:
                    continue
                c, c0, _, _ = law_from(list(sub))
                z = float(np.linalg.norm(TM[anchor] - TM[h]
                                         - c(lp[anchor], lp[h]) - c0))
                rs.append(z / d)
    if not rs:
        return float('nan'), 0
    return float(np.quantile(rs, 1 - ALPHA)), len(rs)


def evaluate(g, b, lawcal, test, anchor, offset=None, oracle=False):
    """One (surrogate, split, anchor) -> a row per test trial."""
    kap, nr = kappa_defensible(lawcal, anchor)
    c, c0, _, _ = law_from(lawcal)
    lawmax = max(lp[n] for n in lawcal)
    ua = lp[anchor]
    pred = (lambda t: TM[t]) if oracle else (
        lambda t: g(np.array([[lp[t]]]))[0] + (offset if offset is not None else 0.0))
    fa = TM[anchor] if oracle else g(np.array([[ua]]))[0]
    rows = []
    for t in test:
        d = np.log(TP[t]) - lawmax
        ft = pred(t)
        D = float(np.linalg.norm(fa - ft - c(ua, lp[t]) - c0))
        z = float(np.linalg.norm(TM[anchor] - TM[t] - c(ua, lp[t]) - c0))
        beta = kap * d
        S = max(D - b - beta, 0.0) if np.isfinite(beta) else float('nan')
        e = float(np.linalg.norm(ft - TM[t]))
        rows.append(dict(P=float(TP[t]), delta=d, D=D, b=float(b), beta=beta,
                         zeta=z, S=S, e=e, kappa=kap, kappa_req=z / d, n_ratio=nr,
                         covered=bool(z <= beta) if np.isfinite(beta) else False,
                         valid=bool(e >= S) if np.isfinite(S) else True,
                         S_over_e=(S / e if (e and np.isfinite(S)) else 0.0)))
    return rows


def fit_surrogate(kind, seed):
    q = slopes(TRAIN)
    g = build(kind, seed, TRAIN, q)
    errs = []
    for n in TRAIN:
        rest = [t for t in TRAIN if t != n]
        gr = build(kind, seed, rest, slopes(rest))
        errs.append(float(np.linalg.norm(gr(np.array([[lp[n]]]))[0] - TM[n])))
    return g, float(conformal_quantile(np.array(errs), 1 - ALPHA))


def pct(v):
    v = np.asarray(v, float)
    return "med %5.2f  [%5.2f, %5.2f]" % (np.median(v), v.min(), v.max())


if __name__ == '__main__':
    SP = splits()
    CANON = ([n for n in ABOVE if TP[n] <= 192], [n for n in ABOVE if TP[n] > 192])
    print("Setup C stress-test. %d admissible splits; canonical = LAWCAL<=192.\n"
          "alpha=%.2f covers b only; beta is a declared envelope (audited via zeta).\n"
          % (len(SP), ALPHA))

    cache = {}
    for kind in ('mlp8', 'mlp16x16', 'linear'):
        for seed in range(3):
            cache[(kind, seed)] = fit_surrogate(kind, seed)
    g0, b0 = cache[('mlp8', 0)]
    OUT = {}

    print("=== TEST 1: estimator accuracy across all %d splits (mlp8 s0, anchor 54mW) ==="
          % len(SP))
    rows = []
    for lawcal, test in SP:
        rows += evaluate(g0, b0, lawcal, test, DEFAULT_ANCHOR)
    rows = [r for r in rows if np.isfinite(r['kappa'])]
    err = [100 * (r['kappa'] - r['kappa_req']) / r['kappa_req'] for r in rows]
    print("  cases %d | kappa' error %%: %s" % (len(rows), pct(err)))
    print("  fraction of cases where kappa' is TOO LOW: %.2f" % np.mean(np.array(err) < 0))
    print("  beta coverage %.2f | validity %.2f | S/e %s"
          % (np.mean([r['covered'] for r in rows]),
             np.mean([r['valid'] for r in rows]),
             pct([r['S_over_e'] for r in rows])))
    OUT['test1'] = rows

    print("\n=== TEST 2: anchor sensitivity (canonical split, mlp8 s0) ===")
    print("  %-8s %8s %8s %9s %8s %8s" % ('anchor', "kappa'", 'demand', 'err %',
                                          'coverage', 'mean S/e'))
    t2 = []
    for a in sorted(TRAIN, key=lambda n: TP[n]):
        rs = evaluate(g0, b0, CANON[0], CANON[1], a)
        if not np.isfinite(rs[0]['kappa']):
            continue
        e_ = 100 * (rs[0]['kappa'] - np.mean([r['kappa_req'] for r in rs])) / \
            np.mean([r['kappa_req'] for r in rs])
        print("  %5.0f mW %8.2f %8.2f %+8.0f%% %6d/%d %8.2f"
              % (TP[a], rs[0]['kappa'], np.mean([r['kappa_req'] for r in rs]), e_,
                 sum(r['covered'] for r in rs), len(rs),
                 np.mean([r['S_over_e'] for r in rs])))
        t2.append(dict(anchor=float(TP[a]), kappa=rs[0]['kappa'], err=e_,
                       cov=sum(r['covered'] for r in rs), n=len(rs)))
    OUT['test2'] = t2

    print("\n=== TEST 3: surrogate sensitivity (canonical split, anchor 54mW) ===")
    print("  %-11s %5s %8s %8s %8s %8s %8s" % ('model', 'seed', 'b', 'mean D',
                                               'mean e', 'mean S', 'mean S/e'))
    t3 = []
    for kind in ('mlp8', 'mlp16x16', 'linear'):
        for seed in range(3):
            g, b = cache[(kind, seed)]
            rs = evaluate(g, b, CANON[0], CANON[1], DEFAULT_ANCHOR)
            print("  %-11s %5d %8.2f %8.2f %8.2f %8.2f %8.2f"
                  % (kind, seed, b, np.mean([r['D'] for r in rs]),
                     np.mean([r['e'] for r in rs]), np.mean([r['S'] for r in rs]),
                     np.mean([r['S_over_e'] for r in rs])))
            t3.append(dict(kind=kind, seed=seed, b=b,
                           S=float(np.mean([r['S'] for r in rs])),
                           e=float(np.mean([r['e'] for r in rs])),
                           cov=int(sum(r['covered'] for r in rs))))
    OUT['test3'] = t3

    print("\n=== TEST 4: premise -> conclusion (all splits x all anchors, mlp8 s0) ===")
    allr = []
    for a in TRAIN:
        for lawcal, test in SP:
            allr += evaluate(g0, b0, lawcal, test, a)
    allr = [r for r in allr if np.isfinite(r['kappa'])]
    cov = [r for r in allr if r['covered']]
    unc = [r for r in allr if not r['covered']]
    print("  cases %d  (covered %d, not covered %d)" % (len(allr), len(cov), len(unc)))
    for tag, grp in (('beta COVERS  ', cov), ('beta FAILS   ', unc)):
        if grp:
            print("   %s validity %.3f | mean S %.2f | mean e %.2f"
                  % (tag, np.mean([r['valid'] for r in grp]),
                     np.mean([r['S'] for r in grp]), np.mean([r['e'] for r in grp])))
    print("  Prop 1 claims e >= S whenever BOTH bounds hold. Validity in the")
    print("  covered group is the number that tests it.")
    OUT['test4'] = dict(n=len(allr), n_cov=len(cov),
                        val_cov=float(np.mean([r['valid'] for r in cov])) if cov else None,
                        val_unc=float(np.mean([r['valid'] for r in unc])) if unc else None)

    print("\n=== TEST 5: planted-error control (canonical split, anchor 54mW) ===")
    print("  %-10s %8s %8s %8s %8s" % ('planted', 'mean D', 'mean S', 'mean e', 'S<=e'))
    t5 = []
    dirn = np.ones(B) / np.sqrt(B)
    for mag in (0.0, 2.0, 5.0, 10.0, 20.0):
        rs = evaluate(g0, b0, CANON[0], CANON[1], DEFAULT_ANCHOR, offset=mag * dirn)
        ok = all(r['valid'] for r in rs)
        print("  %10.1f %8.2f %8.2f %8.2f %8s"
              % (mag, np.mean([r['D'] for r in rs]), np.mean([r['S'] for r in rs]),
                 np.mean([r['e'] for r in rs]), 'yes' if ok else 'NO'))
        t5.append(dict(mag=mag, S=float(np.mean([r['S'] for r in rs])),
                       e=float(np.mean([r['e'] for r in rs])), valid=ok))
    OUT['test5'] = t5

    print("\n=== TEST 6: accurate-surrogate control (no false alarm?) ===")
    rs = evaluate(g0, b0, CANON[0], CANON[1], DEFAULT_ANCHOR, oracle=True)
    print("  a surrogate that is exactly right at every test power:")
    for r in rs:
        print("     P=%4.0f  D=%5.2f  b+beta=%5.2f  S=%5.2f  e=%5.2f"
              % (r['P'], r['D'], r['b'] + r['beta'], r['S'], r['e']))
    print("  -> S is %s" % ("silent (no false alarm)" if all(r['S'] == 0 for r in rs)
                            else "NON-ZERO: FALSE ALARM"))
    OUT['test6'] = rs

    json.dump(OUT, open('setupc_results.json', 'w'), indent=1, default=float)
    print("\nwrote setupc_results.json")
