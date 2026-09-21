"""Capillary-wave benchmarks, corrected instantiation.

Two fixes over the first pass, both inside the proposal's own spec:

 1. b_lam must bound ||e_th(T_lam x)||, the surrogate's error against the TARGET
    FUNCTION at the anchor -- not against one noisy window. Calibrating it on
    window residuals made it bound the window scatter too, which D never
    contains. b is now estimated from leave-one-TRIAL-out refits against
    trial-mean spectra.
 2. The anchor rule is predeclared (the admissible calibration power nearest the
    case), so m = 1 and no union bound is needed. The m = 4 max-over-grid
    variant is reported alongside, union-bounded at 1 - alpha/m as in section 7.
"""
import numpy as np, warnings
from pathlib import Path
warnings.filterwarnings('ignore')
from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sases import ShiftLaw, sases, metrics, spearman, conformal_quantile

ALPHA, NSEED, BETA_LEVEL = 0.10, 5, 0.90
D = np.load(Path(__file__).resolve().parent / 'spec.npz', allow_pickle=False)
Y, P, TRIAL, FC = D['Y'], D['P'], D['trial'], D['fcent']
NAMES = list(dict.fromkeys(TRIAL))
TP = {n: P[TRIAL == n][0] for n in NAMES}
TM = {n: Y[TRIAL == n].mean(0) for n in NAMES}
B = Y.shape[1]


def windows(ts):
    m = np.isin(TRIAL, list(ts))
    return np.log(P[m]), Y[m], TRIAL[m]


def build(kind, seed, trials, q=None):
    U, Yt, _ = windows(trials)
    X = U[:, None]
    if kind == 'hardcoded':
        a = (Yt - q * U[:, None]).mean(0)
        return lambda V: a + q * np.asarray(V, float)[:, :1]
    if kind == 'linear':
        m = LinearRegression().fit(X, Yt)
        return lambda V: m.predict(np.asarray(V, float))
    hid = {'mlp8': (8,), 'mlp16x16': (16, 16)}[kind]
    sc = StandardScaler().fit(X)
    g = MLPRegressor(hidden_layer_sizes=hid, activation='tanh', alpha=1e-3,
                     max_iter=8000, random_state=seed, learning_rate_init=5e-3,
                     tol=1e-8, n_iter_no_change=400).fit(sc.transform(X), Yt)
    return lambda V: g.predict(sc.transform(np.asarray(V, float)))


def fit_law(trials):
    lp = np.array([np.log(TP[n]) for n in trials])
    tm = np.array([TM[n] for n in trials])
    return np.array([np.polyfit(lp, tm[:, b], 1)[0] for b in range(B)])


def fit_beta(trials, q):
    lp = np.array([np.log(TP[n]) for n in trials]); tm = np.array([TM[n] for n in trials])
    dl, z = [], []
    for i in range(len(trials)):
        for j in range(len(trials)):
            if i == j: continue
            dl.append(abs(lp[j] - lp[i]))
            z.append(np.linalg.norm(tm[j] - tm[i] - q * (lp[j] - lp[i])))
    return float(np.quantile(z, BETA_LEVEL)), float(np.max(dl))


def loto_errors(kind, seed, cal, q):
    """Held-out trial-level surrogate errors: the quantity b_lam must bound."""
    out = {}
    for n in cal:
        rest = [t for t in cal if t != n]
        g = build(kind, seed, rest, fit_law(rest) if kind == 'hardcoded' else q)
        out[n] = float(np.linalg.norm(g(np.array([[np.log(TP[n])]]))[0] - TM[n]))
    return out


def run(kind, cal_lo, cal_hi, shift, seed, law_mode='true', n_anchor=1,
        oracle_b=False):
    cal = [n for n in NAMES if cal_lo <= TP[n] <= cal_hi]
    cl, ch = np.log(cal_lo), np.log(cal_hi)
    q = fit_law(cal)
    beta0, reach = fit_beta(cal, q)
    g = build(kind, seed, cal, q)
    ens = [build('mlp16x16', 100 * seed + k + 1, cal) for k in range(5)]

    loto = loto_errors(kind, seed, cal, q)
    lvl = 1 - ALPHA / n_anchor
    b = conformal_quantile(np.array(list(loto.values())), lvl)

    if law_mode == 'true':
        law = ShiftLaw(q)
    elif law_mode == 'permq':
        law = ShiftLaw(np.random.default_rng(7 + seed).permutation(q))
    else:
        pm = np.random.default_rng(11 + seed).permutation(B)
        law = ShiftLaw(q[pm], perm=pm)

    grid = np.linspace(cl, ch, 4) if n_anchor > 1 else None
    pu = lambda uu, i: g(np.asarray(uu, float)[:, None])

    S, e_tr, e_wi_all, S_wi, D_at = [], [], [], [], []
    for n in shift:
        u = np.log(TP[n])
        if n_anchor == 1:
            cand = np.array([min(ch, u)])                     # predeclared: nearest admissible
        else:
            cand = grid
        ok = (cand >= cl) & (cand <= ch) & (np.abs(cand - u) <= reach)
        if not ok.any():
            s = np.nan; d = np.nan
        else:
            bb = b
            if oracle_b:
                bb = max(loto.values())
            bt = beta0
            ss, _, dd = sases(pu, [u], cand[ok], law, lambda a: bb, lambda dl: bt, cl, ch)
            s, d = ss[0], dd[0]
        S.append(s); D_at.append(d)
        e_tr.append(float(np.linalg.norm(g(np.array([[u]]))[0] - TM[n])))
        Uw, Yw, _ = windows([n])
        ew = np.linalg.norm(g(Uw[:, None]) - Yw, axis=1)
        e_wi_all.append(ew); S_wi.append(np.full(len(ew), s))

    S = np.array(S); e_tr = np.array(e_tr)
    Sw = np.concatenate(S_wi); ew = np.concatenate(e_wi_all)
    Uall = np.array([np.log(TP[n]) for n in shift])
    Pk = np.stack([m(Uall[:, None]) for m in ens])
    es = np.linalg.norm(Pk - Pk.mean(0), axis=2).mean(0)

    mt = metrics(S, e_tr)
    mw = metrics(Sw, ew)
    mt.update(validity_window=mw['validity'], rho_sases=spearman(S, e_tr),
              rho_ensemble=spearman(es, e_tr), b=b, beta=beta0, reach=reach,
              median_D=float(np.nanmedian(D_at)), mean_e=float(e_tr.mean()),
              mean_S=float(np.nanmean(S)))
    return mt, S, e_tr, D_at


def table(title, rows, keys):
    print("\n" + title)
    hdr = f"{'setting':28s}" + "".join(f"{k[:12]:>13s}" for k in keys)
    print(hdr); print('-' * len(hdr))
    for name, rs in rows:
        v = []
        for k in keys:
            a = np.array([r[k] for r in rs], float)
            v.append(np.nan if np.all(np.isnan(a)) else np.nanmean(a))
        print(f"{name:28s}" + "".join(
            ("      ---    " if not np.isfinite(x) else f"{x:13.3f}") for x in v))


KEYS = ('validity', 'validity_window', 'non_vacuity', 'anchor_coverage',
        'rho_sases', 'rho_ensemble')
KINDS = ('hardcoded', 'linear', 'mlp8', 'mlp16x16')

if __name__ == '__main__':
    print("=== Capillary-wave corpus (Orosco et al. 2023, 50 MB copy) ===")
    print("cases = trials in the shifted band; splits grouped by trial throughout")
    print(f"alpha = {ALPHA}; b = leave-one-trial-out conformal bound at level "
          f"{1-ALPHA:.2f} (m=1, predeclared anchor)")
    print(f"beta  = declared {BETA_LEVEL:.2f} quantile of calibration-band law residuals\n")

    for tag, lo, hi, thr in (("Config I : X_cal=[12,54] mW, shift=[106,350]", 12, 54, 106),
                             ("Config II: X_cal=[12,106] mW, shift=[125,350]", 12, 106, 125)):
        sh = [n for n in NAMES if TP[n] >= thr]
        res = {k: [run(k, lo, hi, sh, s)[0] for s in range(NSEED)] for k in KINDS}
        table(tag, [(k, v) for k, v in res.items()], KEYS)
        for k, v in res.items():
            print(f"  {k:10s} b={np.mean([x['b'] for x in v]):5.2f} "
                  f"beta={v[0]['beta']:5.2f} reach={v[0]['reach']:.2f}  "
                  f"med D={np.nanmean([x['median_D'] for x in v]):6.2f}  "
                  f"mean e={np.mean([x['mean_e'] for x in v]):6.2f}  "
                  f"mean S={np.nanmean([x['mean_S'] for x in v]):6.2f}")

    sh = [n for n in NAMES if TP[n] >= 125]
    print("\n--- m = 4 anchor grid, union-bounded at 1 - alpha/m (section 7 form) ---")
    res4 = {k: [run(k, 12, 106, sh, s, n_anchor=4)[0] for s in range(NSEED)] for k in KINDS}
    table("Config II, m=4", [(k, v) for k, v in res4.items()], KEYS)

    print("\n--- False-transform controls (Config II, mlp16x16) ---")
    ctl = []
    for mode, lbl in (('true', 'true transform'), ('permq', 'false: shuffled exponents'),
                      ('permband', 'false: permuted-band law')):
        ctl.append((lbl, [run('mlp16x16', 12, 106, sh, s, law_mode=mode)[0]
                          for s in range(NSEED)]))
    table("control", ctl, KEYS + ('median_D', 'mean_S'))

    print("\n--- per-trial detail (Config II, mlp16x16, seed 0) ---")
    mt, S, e, Dv = run('mlp16x16', 12, 106, sh, 0)
    print(f"{'trial':9s} {'P (mW)':>7s} {'D':>7s} {'b+beta':>7s} {'S(x)':>7s} {'e(x)':>7s} {'e>=S':>6s}")
    print('-' * 56)
    for i, n in enumerate(sh):
        print(f"{n:9s} {TP[n]:7.1f} {Dv[i]:7.2f} {mt['b']+mt['beta']:7.2f} "
              f"{S[i]:7.2f} {e[i]:7.2f} {'yes' if e[i] >= S[i] else 'NO':>6s}")
