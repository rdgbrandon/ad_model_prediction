# -*- coding: utf-8 -*-
"""Honest beta: an upper quantile plus a penalty for extrapolating the law
beyond the calibration region, audited afterwards.

IMPORTANT, and stated in every table this writes: alpha covers b ONLY. b is a
conformal bound at level 1-alpha over held-out trials. beta carries NO
probabilistic guarantee - it is a declared envelope. That asymmetry is exactly
why the audit column exists.
"""
import json, numpy as np, warnings
warnings.filterwarnings('ignore')
from piecewise import (NAMES, TP, TM, TRAIN, ANCHOR, lp, slopes, B, LREF,
                       predictor, loto_b, fit_law, clopper)
from capillary2 import build, windows, ALPHA
from sases import conformal_quantile, metrics

ABOVE = [n for n in NAMES if TP[n] >= 106]


def law_from(sub):
    """Piecewise law calibrated on `sub` (above-break trials). Returns c, c0."""
    q_low, q_hi = slopes(TRAIN), slopes(sub)
    c = lambda ua, uc: q_hi * (LREF - uc) + q_low * (ua - LREF)
    J = [(a, cc) for cc in sub for a in TRAIN]
    R = np.array([TM[a] - TM[cc] - c(lp[a], lp[cc]) for a, cc in J])
    return c, R.mean(0), J, R


def beta_model(lawcal, anchor, alpha=ALPHA):
    """beta(d, P_case) = upper (1-alpha) quantile in-support  +  kappa * extrapolation.

    kappa is fitted by holding out the TOP calibration trial and measuring how
    far the law degrades past the calibrated power range - never on test data.
    """
    c, c0, J, R = law_from(lawcal)
    d = np.array([abs(lp[cc] - lp[a]) for a, cc in J])
    r = np.linalg.norm(R - c0, axis=1)

    def beta0(dd):
        for w in (0.35, 0.5, 0.8, 10.0):
            m = np.abs(d - dd) <= w
            if m.sum() >= 8:
                return float(np.quantile(r[m], 1 - alpha))
        return float(np.quantile(r, 1 - alpha))

    # --- extrapolation penalty, fitted by leave-the-top-out on LAWCAL ---
    pts = []
    srt = sorted(lawcal, key=lambda n: TP[n])
    for k in range(2, len(srt) + 1):
        for i in range(len(srt) - k + 1):
            sub = srt[i:i + k]
            for held in srt:
                if TP[held] <= max(TP[s] for s in sub):
                    continue
                cc_, c0_, _, _ = law_from(sub)
                res = float(np.linalg.norm(TM[anchor] - TM[held]
                                           - cc_(lp[anchor], lp[held]) - c0_))
                dlt = np.log(TP[held]) - max(lp[s] for s in sub)
                # slope on the RAW extrapolation residual: the bias component
                # starts near zero at delta = 0, so subtracting the in-support
                # scatter here would hide it entirely (it did: kappa came out 0).
                pts.append((dlt, res))
    if pts:
        P_ = np.array(pts)
        kappa = float(np.max(P_[:, 1] / np.maximum(P_[:, 0], 1e-6)))   # upper envelope
    else:
        kappa = 0.0
    top = max(lp[n] for n in lawcal)
    def beta(case):
        dd = abs(lp[case] - lp[anchor])
        return beta0(dd) + kappa * max(0.0, lp[case] - top)
    return c, c0, beta, kappa, pts


def noncross_beta(lawcal, anchor, alpha=ALPHA):
    """Same construction for anchors that do NOT cross the break: one exponent."""
    q_hi = slopes(lawcal)
    c = lambda ua, uc: q_hi * (ua - uc)
    src = [n for n in lawcal if n != anchor]
    R = np.array([TM[anchor] - TM[s] - c(lp[anchor], lp[s]) for s in src])
    c0 = R.mean(0) if len(R) else np.zeros(B)
    r = np.linalg.norm(R - c0, axis=1)
    b0 = float(np.quantile(r, 1 - alpha)) if len(r) else 0.0
    pts, srt = [], sorted(lawcal, key=lambda n: TP[n])
    for k in range(2, len(srt)):
        sub = srt[:k]
        for held in srt[k:]:
            qh = slopes(sub); cc = lambda ua, uc: qh * (ua - uc)
            s2 = [n for n in sub if n != anchor]
            if not s2: continue
            R2 = np.array([TM[anchor] - TM[s] - cc(lp[anchor], lp[s]) for s in s2])
            res = float(np.linalg.norm(TM[anchor] - TM[held]
                                       - cc(lp[anchor], lp[held]) - R2.mean(0)))
            pts.append((np.log(TP[held]) - max(lp[s] for s in sub), res))
    kappa = float(np.max([p[1] / max(p[0], 1e-6) for p in pts])) if pts else 0.0
    top = max(lp[n] for n in lawcal)
    return c, c0, (lambda case: b0 + kappa * max(0.0, lp[case] - top)), kappa


def run(lawcal, test, seed, mode='crossing', kind='mlp8'):
    if mode == 'crossing':
        anchor = ANCHOR
        c, c0, beta, kappa, _ = beta_model(lawcal, anchor)
        g = predictor(kind, seed, c, c0)
        b_src = loto_b(kind, seed)                       # held-out TRAIN trials
        b = conformal_quantile(b_src, 1 - ALPHA); b_ok = np.isfinite(b)
    else:
        anchor = max(lawcal, key=lambda n: TP[n])
        c, c0, beta, kappa = noncross_beta(lawcal, anchor)
        g = build(kind, seed, TRAIN, slopes(TRAIN))
        # b above the break: surrogate is trained on 12-54, these trials are held out
        b_src = np.array([float(np.linalg.norm(g(np.array([[lp[n]]]))[0] - TM[n]))
                          for n in lawcal])
        b = conformal_quantile(b_src, 1 - ALPHA)
        b_ok = np.isfinite(b)
        if not b_ok:
            b = float(b_src.max())                       # point estimate, NO guarantee
    ua = lp[anchor]; fa = g(np.array([[ua]]))[0]
    rows = []
    for t in test:
        uc = lp[t]
        D = float(np.linalg.norm(fa - g(np.array([[uc]]))[0] - c(ua, uc) - c0))
        bt = float(beta(t))
        zeta = float(np.linalg.norm(TM[anchor] - TM[t] - c(ua, uc) - c0))   # audit
        S = max(D - b - bt, 0.0)
        e = float(np.linalg.norm(g(np.array([[uc]]))[0] - TM[t]))
        rows.append(dict(trial=t, P=float(TP[t]), D=D, b=float(b), beta=bt, S=S, e=e,
                         zeta=zeta, covered=bool(zeta <= bt), valid=bool(e >= S)))
    return dict(rows=rows, anchor=float(TP[anchor]), kappa=kappa,
                b_conformal=bool(b_ok), n_b=int(len(b_src)),
                k_needed=int(np.ceil((len(b_src) + 1) * (1 - ALPHA))))


NOTE = ("alpha = %.2f covers b ONLY: b is a conformal bound over held-out trials.\n"
        "beta carries NO probabilistic guarantee - it is a declared envelope, which\n"
        "is why every table below reports the audited law residual next to it." % ALPHA)

if __name__ == '__main__':
    NS, OUT = 5, {}
    print("=== Honest beta: upper quantile + extrapolation penalty ===\n" + NOTE + "\n")
    for hi in (146, 192):
        lawcal = [n for n in NAMES if 106 <= TP[n] <= hi]
        test = [n for n in NAMES if TP[n] > hi]
        for mode in ('crossing', 'noncross'):
            reps = [run(lawcal, test, s, mode) for s in range(NS)]
            m0 = reps[0]
            key = "LAWCAL<=%d|%s" % (hi, mode)
            OUT[key] = reps
            agg = lambda f: np.mean([f(r) for rep in reps for r in rep['rows']])
            cov = agg(lambda r: r['covered']); nv = agg(lambda r: r['S'] > 0)
            val = agg(lambda r: r['valid'])
            print("--- LAWCAL<=%d (%d trials) | %s anchor = %.0f mW | TEST %s ---"
                  % (hi, len(lawcal), mode, m0['anchor'], [int(TP[t]) for t in test]))
            if not m0['b_conformal']:
                print("    !! b is NOT a conformal bound here: %d held-out trials, "
                      "level %.2f needs the %d-th. Reported b is the sample maximum,\n"
                      "       a point estimate with no guarantee. BLOCKING DATA NEED: "
                      ">= %d labelled trials above the break,\n       held out from "
                      "surrogate training." % (m0['n_b'], 1 - ALPHA, m0['k_needed'],
                                               m0['k_needed']))
            print("    kappa (extrapolation penalty) = %.2f per ln-unit above the "
                  "calibrated range" % m0['kappa'])
            print("    %-7s %7s %7s %7s %7s %7s %7s %6s %6s"
                  % ('trial', 'P(mW)', 'D', 'b', 'beta', 'S(x)', 'e(x)', 'zeta', 'cov'))
            for i, t in enumerate(test):
                rs = [rep['rows'][i] for rep in reps]
                f = lambda k: np.mean([r[k] for r in rs])
                print("    %-7s %7.0f %7.2f %7.2f %7.2f %7.2f %7.2f %6.2f %6s"
                      % (t, TP[t], f('D'), f('b'), f('beta'), f('S'), f('e'),
                         f('zeta'), 'yes' if f('covered') > .5 else 'NO'))
            n = len(test) * NS
            print("    beta coverage %.2f (target >= %.2f) | non-vacuity %.2f | "
                  "validity %.2f  [n = %d cases, %d trials x %d seeds]\n"
                  % (cov, 1 - ALPHA, nv, val, n, len(test), NS))
    json.dump(OUT, open('honest_beta_results.json', 'w'), indent=1, default=float)
    print("wrote honest_beta_results.json")
