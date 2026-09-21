# -*- coding: utf-8 -*-
"""Two-regime (piecewise) instantiation of the anchor-symmetry certificate.

The single-exponent law of Section 7 fails across the regime break, inflating
beta to 10-15 and making the certificate vacuous. Here the law carries one
exponent vector per regime:

    c_lam(case -> anchor) = q_high (ln P_ref - ln P_case)
                          + q_low  (ln P_anchor - ln P_ref) + c0

still affine with A_lam = I, so ||A_lam||_2 = 1. c0 absorbs the unknown break
location P_ref, which sits in the corpus's 55-105 mW data gap.

Three disjoint trial groups, all splits grouped by trial:
  TRAIN   12-54 mW    trains the surrogate; the anchor is its top edge
  LAWCAL  106-*  mW   labelled, never seen by the surrogate: fits q_high, c0, beta
  TEST    > LAWCAL    never used to fit anything
"""
import json, numpy as np, warnings
warnings.filterwarnings('ignore')
from capillary2 import NAMES, TP, TM, build, windows, ALPHA
from sases import conformal_quantile, metrics, spearman

lp = {n: np.log(TP[n]) for n in NAMES}
TRAIN = [n for n in NAMES if 12 <= TP[n] <= 54]
ANCHOR = max(TRAIN, key=lambda n: TP[n])
B = TM[TRAIN[0]].shape[0]
P_REF = np.sqrt(54 * 106)
LREF = np.log(P_REF)


def slopes(ts):
    x = np.array([lp[n] for n in ts]); Y = np.array([TM[n] for n in ts])
    return np.array([np.polyfit(x, Y[:, b], 1)[0] for b in range(B)])


def fit_law(lawcal, mode='piecewise', rng=None):
    """Returns c(anchor_u, case_u) and the beta envelope, from calibration only."""
    q_low = slopes(TRAIN)
    if mode == 'single':
        c = lambda ua, uc: q_low * (ua - uc)
    else:
        q_hi = slopes(lawcal)
        if mode == 'false':                      # control: scramble the exponents
            q_hi = rng.permutation(q_hi)
        c = lambda ua, uc: q_hi * (LREF - uc) + q_low * (ua - LREF)
    J = [(a, cc) for cc in lawcal for a in TRAIN]
    R = np.array([TM[a] - TM[cc] - c(lp[a], lp[cc]) for a, cc in J])
    c0 = R.mean(0) if mode != 'single' else np.zeros(B)
    d = np.array([abs(lp[cc] - lp[a]) for a, cc in J])
    nr = np.linalg.norm(R - c0, axis=1)
    # beta envelope: linear fit through the per-bin upper quantile (predeclared)
    edges = np.quantile(d, [0, .25, .5, .75, 1.0])
    xs, ys = [], []
    for i in range(4):
        m = (d >= edges[i]) & (d <= edges[i + 1])
        if m.sum() >= 3:
            xs.append(d[m].mean()); ys.append(np.quantile(nr[m], .9))
    sl, ic = np.polyfit(xs, ys, 1) if len(xs) >= 2 else (0.0, np.quantile(nr, .9))
    beta = lambda dd: float(max(ic + sl * dd, np.quantile(nr, .5)))
    return c, c0, beta, float(np.quantile(nr, .9)), (q_low, slopes(lawcal))


def law_audit(c, c0, test):
    """Oracle: the true law residual on the TEST jumps. Uses test labels, so it is
    an audit of whether beta was adequate - never an input to the certificate."""
    return np.array([np.linalg.norm(TM[t] * 0 + TM[ANCHOR] - TM[t]
                                    - c(lp[ANCHOR], lp[t]) - c0) for t in test])




def loto_b(kind, seed):
    """b bounds the surrogate error AT THE ANCHOR: leave-one-trial-out inside TRAIN."""
    errs = []
    for n in TRAIN:
        rest = [t for t in TRAIN if t != n]
        g = build(kind if kind.startswith('mlp') else 'linear', seed, rest, slopes(rest))
        errs.append(float(np.linalg.norm(g(np.array([[lp[n]]]))[0] - TM[n])))
    return np.array(errs)


def predictor(kind, seed, c, c0):
    """The surrogate. 'hardcoded' satisfies the ACTIVE law identically, so its
    defect is zero by construction - the blind spot the proposal predicts."""
    q_low = slopes(TRAIN)
    g = build('mlp8' if kind == 'hardcoded' else kind, seed, TRAIN, q_low)
    if kind != 'hardcoded':
        return g
    ua = lp[ANCHOR]; fa = g(np.array([[ua]]))[0]
    def h(U):
        U = np.asarray(U, float)
        out = np.empty((len(U), B))
        for i, u in enumerate(U[:, 0]):
            out[i] = g(np.array([[u]]))[0] if u <= ua else fa - c(ua, u) - c0
        return out
    return h


def run(kind, lawcal, test, seed, mode='piecewise', beta_mode='fitted'):
    rng = np.random.default_rng(31 + seed)
    c, c0, beta, beta_q90, (q_low, q_hi) = fit_law(lawcal, mode, rng)
    g = predictor(kind, seed, c, c0)
    b = conformal_quantile(loto_b(kind, seed), 1 - ALPHA)      # m = 1 anchor
    ua = lp[ANCHOR]; fa = g(np.array([[ua]]))[0]
    audit = law_audit(c, c0, test)

    S, D, E, BT, EW, SW = [], [], [], [], [], []
    for i, t in enumerate(test):
        uc = lp[t]
        Dv = float(np.linalg.norm(fa - g(np.array([[uc]]))[0] - c(ua, uc) - c0))
        # 'audit' beta = the law residual actually incurred (oracle; robustness only)
        bt = float(audit[i]) if beta_mode == 'audit' else beta(abs(uc - ua))
        D.append(Dv); BT.append(bt); S.append(max(Dv - b - bt, 0.0))
        E.append(float(np.linalg.norm(g(np.array([[uc]]))[0] - TM[t])))
        Uw, Yw, _ = windows([t])
        EW.append(np.linalg.norm(g(Uw[:, None]) - Yw, axis=1))
        SW.append(np.full(len(EW[-1]), S[-1]))

    S, D, E, BT = map(np.array, (S, D, E, BT))
    mt = metrics(S, E)
    mt.update(validity_window=metrics(np.concatenate(SW), np.concatenate(EW))['validity'],
              b=float(b), beta_q90=beta_q90, beta_at_test=BT.tolist(),
              beta_coverage=float((audit <= BT).mean()),
              D=D.tolist(), S=S.tolist(), e=E.tolist(), audit=audit.tolist(),
              q_low=q_low.tolist(), q_high=q_hi.tolist(), rho=spearman(S, E),
              power=[float(TP[t]) for t in test])
    return mt


def clopper(k, n):
    from scipy.stats import beta as Bd
    return 0.0 if k == 0 else float(Bd.ppf(0.05, k, n - k + 1))


if __name__ == '__main__':
    NS = 5
    print("=== Two-regime anchor-symmetry certificate ===")
    print("TRAIN %s mW | anchor %d mW | alpha %.2f, m=1 | P_ref %.1f mW\n"
          % ([int(TP[n]) for n in TRAIN], TP[ANCHOR], ALPHA, P_REF))
    OUT = {}
    KEYS = ('validity', 'validity_window', 'non_vacuity', 'beta_coverage')
    for hi in (146, 192):
        lawcal = [n for n in NAMES if 106 <= TP[n] <= hi]
        test = [n for n in NAMES if TP[n] > hi]
        tag = "LAWCAL<=%d" % hi
        print("--- %s (%d trials) -> TEST %s (%d trials) ---"
              % (tag, len(lawcal), [int(TP[n]) for n in test], len(test)))
        hdr = ("%-26s %7s %8s %8s %9s %6s %6s %7s" % ('surrogate / law', 'valid',
               'val(win)', 'non-vac', 'beta cov', 'b', 'beta', 'mean S'))
        print(hdr); print('-' * len(hdr))
        cases = [('mlp8', 'piecewise', 'fitted'), ('mlp8', 'single', 'fitted'),
                 ('mlp8', 'piecewise', 'audit'), ('mlp16x16', 'piecewise', 'fitted'),
                 ('hardcoded', 'piecewise', 'fitted'), ('mlp8', 'false', 'fitted')]
        for kind, mode, bm in cases:
            rs = [run(kind, lawcal, test, s, mode, bm) for s in range(NS)]
            OUT["%s|%s|%s|%s" % (tag, kind, mode, bm)] = rs
            nm = "%s / %s%s" % (kind, mode, '  [oracle beta]' if bm == 'audit' else '')
            print("%-26s %7.3f %8.3f %8.3f %9.3f %6.2f %6.2f %7.2f" % (
                nm, np.nanmean([r['validity'] for r in rs]),
                np.nanmean([r['validity_window'] for r in rs]),
                np.nanmean([r['non_vacuity'] for r in rs]),
                np.mean([r['beta_coverage'] for r in rs]),
                np.mean([r['b'] for r in rs]),
                np.mean([np.mean(r['beta_at_test']) for r in rs]),
                np.nanmean([np.mean(r['S']) for r in rs])))
        r0 = OUT["%s|mlp8|piecewise|fitted" % tag][0]
        print("\n  per-trial (mlp8, piecewise, seed 0):")
        print("  %-8s %6s %7s %7s %7s %7s %6s %8s %7s" % ('trial', 'P(mW)', 'D',
              'b+beta', 'S(x)', 'e(x)', 'e>=S', 'true ze', 'beta ok'))
        for i, t in enumerate(test):
            print("  %-8s %6.0f %7.2f %7.2f %7.2f %7.2f %6s %8.2f %7s" % (
                t, TP[t], r0['D'][i], r0['b'] + r0['beta_at_test'][i], r0['S'][i],
                r0['e'][i], 'yes' if r0['e'][i] >= r0['S'][i] else 'NO',
                r0['audit'][i],
                'yes' if r0['audit'][i] <= r0['beta_at_test'][i] else 'NO'))
        n = len(test) * NS
        k = int(round(np.nanmean([r['validity'] for r in
                      OUT["%s|mlp8|piecewise|fitted" % tag]]) * n))
        print("  validity %d/%d -> 95%% lower bound %.3f (n counts seeds, which are "
              "not independent cases)\n" % (k, n, clopper(k, n)))
    json.dump(OUT, open('piecewise_results.json', 'w'), indent=1, default=float)
    print("wrote piecewise_results.json")
