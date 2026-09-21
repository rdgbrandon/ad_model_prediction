"""S_ASES: anchor-symmetry error certificate (Rodriguez, Prop. 1).

    f(T_lam x) = A_lam f(x) + c_lam + zeta_lam(x),   ||zeta_lam(x)|| <= beta_lam
    D_th(x,lam) = || f_th(T_lam x) - A_lam f_th(x) - c_lam ||_2
    ||e_th(x)|| >= [ D_th - b_lam - beta_lam ]_+ / ||A_lam||_2
    S(x)        = max over admissible anchors;  abstain if none are admissible.

Instantiated for a 1-parameter additive shift on the log control parameter
(u = ln P), which is the form the proposal argues for: A_lam = I (or a
permutation, for the false-transform controls) so ||A_lam||_2 = 1 for every
case, and c_lam = q * ln(lam) with a per-output-component exponent vector q.
"""
import numpy as np


def conformal_quantile(resid, level):
    """Finite-sample conformal upper quantile at `level` (=1-alpha/m)."""
    n = len(resid)
    k = int(np.ceil((n + 1) * level))
    if k > n:
        return np.inf            # not enough calibration points for this level
    return np.sort(resid)[k - 1]


class ShiftLaw:
    """c_lam = q * dlnP, optional output permutation A (a false-transform knob)."""
    def __init__(self, q, perm=None):
        self.q = np.asarray(q, float)
        self.perm = perm                      # None => A = I
        self.A_norm = 1.0                     # identity or permutation: ||A||_2 = 1

    def apply_A(self, Y):
        return Y if self.perm is None else Y[..., self.perm]

    def c(self, dlnP):
        return self.q * dlnP


def defect(pred_u, u, u_anchor, law, i=0):
    """D_th(x, lam) for one case u and a vector of anchor positions.

    pred_u(u_array, i) evaluates the surrogate along the transform orbit of
    case i: only the control coordinate moves, every other input is held."""
    fx = pred_u(np.array([u]), i)[0]                    # (d,)
    fa = pred_u(np.asarray(u_anchor, float), i)         # (m, d)
    dl = np.asarray(u_anchor, float) - u
    return np.linalg.norm(fa - law.apply_A(fx)[None, :] - law.c(dl[:, None]), axis=1)


def sases(pred_u, u_cases, u_anchor_grid, law, b_of_anchor, beta_fn, cal_lo, cal_hi):
    """Returns S (nan where abstained), the chosen anchor, and D at that anchor."""
    u_anchor_grid = np.asarray(u_anchor_grid, float)
    adm_all = (u_anchor_grid >= cal_lo) & (u_anchor_grid <= cal_hi)
    S = np.full(len(u_cases), np.nan)
    best = np.full(len(u_cases), np.nan)
    Dbest = np.full(len(u_cases), np.nan)
    for i, u in enumerate(u_cases):
        ua = u_anchor_grid[adm_all]
        if ua.size == 0:
            continue                                     # Lambda_anc(x) empty -> abstain
        D = defect(pred_u, u, ua, law, i)
        b = np.asarray([b_of_anchor(a) for a in ua], float)
        bt = np.asarray([beta_fn(abs(a - u)) for a in ua], float)
        cand = np.maximum(D - b - bt, 0.0) / law.A_norm
        j = int(np.argmax(cand))
        S[i] = cand[j]; best[i] = ua[j]; Dbest[i] = D[j]
    return S, best, Dbest


def metrics(S, e):
    """Proposal section 5. Validity is over non-abstained cases only."""
    ok = ~np.isnan(S)
    out = dict(anchor_coverage=float(ok.mean()), n=int(len(S)), n_scored=int(ok.sum()))
    if ok.sum() == 0:
        return dict(out, validity=np.nan, non_vacuity=np.nan, median_S=np.nan,
                    median_e=np.nan)
    Ss, ee = S[ok], e[ok]
    out.update(validity=float((ee >= Ss).mean()),
               non_vacuity=float((Ss > 0).mean()),
               median_S=float(np.median(Ss)), median_e=float(np.median(ee)),
               median_S_nonvac=float(np.median(Ss[Ss > 0])) if (Ss > 0).any() else 0.0)
    return out


def spearman(a, b):
    from scipy.stats import spearmanr
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3 or np.ptp(a[m]) == 0 or np.ptp(b[m]) == 0:
        return np.nan
    return float(spearmanr(a[m], b[m]).correlation)
