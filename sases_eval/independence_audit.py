"""How dependent are the scored rows, and what sample size do they carry?

Protocol: INDEPENDENCE_PROTOCOL.md. Reads stored results only.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta, spearmanr

HERE = Path(__file__).resolve().parent
OUT = HERE / 'independence'
RNG = np.random.default_rng(20261002)
NPERM = 10000

# As on the comparison slide: which side each method is read on.
METHODS = [('sases', 'SASES consensus', 'lower'),
           ('sample_max_heuristic', 'Calibration maximum', 'lower'),
           ('raw_defect', 'Raw defect', 'upper'),
           ('ols_error_heuristic', 'OLS error predictor', 'upper')]


def cp(k, n, alpha=.05):
    """Two-sided Clopper-Pearson; k and n may be non-integer (effective sizes)."""
    lo = 0.0 if k <= 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k >= n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def eta2(y, groups):
    y = np.asarray(y, float)
    sst = float(((y - y.mean()) ** 2).sum())
    if sst == 0:
        return None
    ssb = sum(len(idx) * (y[idx].mean() - y.mean()) ** 2
              for idx in group_index(groups).values())
    return float(ssb / sst)


def group_index(groups):
    out = {}
    for i, g in enumerate(groups):
        out.setdefault(g, []).append(i)
    return {g: np.array(v) for g, v in out.items()}


def icc1(y, groups):
    """One-way random-effects ICC(1) for unbalanced groups."""
    y = np.asarray(y, float)
    gi = group_index(groups)
    G, N = len(gi), len(y)
    sizes = np.array([len(v) for v in gi.values()])
    means = {g: y[v].mean() for g, v in gi.items()}
    ssb = sum(len(v) * (means[g] - y.mean()) ** 2 for g, v in gi.items())
    ssw = sum(((y[v] - means[g]) ** 2).sum() for g, v in gi.items())
    msb, msw = ssb / (G - 1), ssw / (N - G)
    n0 = (N - (sizes ** 2).sum() / N) / (G - 1)
    denom = msb + (n0 - 1) * msw
    return float((msb - msw) / denom) if denom > 0 else None, float(sizes.mean())


def codes(groups):
    """Integer labels: tuple labels would become 2-D object arrays when permuted."""
    lut = {}
    return np.array([lut.setdefault(g, len(lut)) for g in groups])


def perm_eta2(y, groups):
    """Exchangeability test: is the between-group share larger than chance?"""
    obs = eta2(y, groups)
    if obs is None:
        return None, None
    g = codes(groups)
    null = np.array([eta2(y, RNG.permutation(g)) for _ in range(NPERM)])
    return obs, float((1 + (null >= obs).sum()) / (NPERM + 1))


def perm_chi2(fail, groups):
    """Are failures concentrated in some groups? Permutation chi-square."""
    fail = np.asarray(fail, bool)
    if fail.all() or not fail.any():
        return None, None

    def stat(gs):
        s = 0.0
        p = fail.mean()
        for idx in group_index(gs).values():
            o = fail[idx].sum(); e = p * len(idx)
            s += (o - e) ** 2 / e + ((len(idx) - o) - (len(idx) - e)) ** 2 / (len(idx) - e)
        return s
    obs = stat(list(groups))
    g = codes(groups)
    null = np.array([stat(list(RNG.permutation(g))) for _ in range(NPERM)])
    return float(obs), float((1 + (null >= obs).sum()) / (NPERM + 1))


def rank_rho(rows, key):
    out = []
    for k in sorted({(r['dataset'], r['config'], r['trial']) for r in rows}):
        rs = [r for r in rows if (r['dataset'], r['config'], r['trial']) == k]
        x = np.array([r[key] for r in rs]); y = np.array([r['error'] for r in rs])
        if len(x) > 2 and np.ptp(x) > 1e-12:
            out.append(spearmanr(x, y).correlation)
    return float(np.mean(out)) if out else None


def analyse_method(rows, key, label, side):
    v = np.array([r[key] for r in rows], float)
    e = np.array([r['error'] for r in rows], float)
    hold = (v <= e + 1e-9) if side == 'lower' else (v >= e - 1e-9)
    margin = (e - v) / e if side == 'lower' else (v - e) / e
    trial = [r['trial'] for r in rows]
    case = [(r['config'], r['trial']) for r in rows]
    cell = [(r['dataset'], r['config'], r['trial']) for r in rows]
    N = len(rows)

    icc, mbar = icc1(margin, trial)
    deff = 1 + (mbar - 1) * max(icc or 0.0, 0.0)
    n_eff = N / deff

    per_trial = {}
    for t, idx in group_index(trial).items():
        per_trial[t] = dict(rows=len(idx), held=int(hold[idx].sum()),
                            rate=float(hold[idx].mean()),
                            P=float(rows[idx[0]]['P']))
    trials_all_held = sum(d['held'] == d['rows'] for d in per_trial.values())
    cases_all_held = sum(bool(hold[idx].all()) for idx in group_index(case).values())
    cells_all_held = sum(bool(hold[idx].all()) for idx in group_index(cell).values())
    n_case, n_cell = len(group_index(case)), len(group_index(cell))

    shares = {name: eta2(margin, grp) for name, grp in [
        ('physical test trial', trial),
        ('calibration split', [r['config'] for r in rows]),
        ('representation', [r['dataset'] for r in rows]),
        ('surrogate family', [r['model'] for r in rows]),
        ('surrogate fit (family, seed)', [(r['model'], r['seed']) for r in rows]),
        ('case (repr, split, trial)', cell)]}
    obs, p_exch = perm_eta2(margin, trial)
    chi, p_conc = perm_chi2(~hold, trial)

    loto = {}
    for t in sorted(per_trial, key=lambda t: per_trial[t]['P']):
        rs = [r for r in rows if r['trial'] != t]
        vv = np.array([r[key] for r in rs]); ee = np.array([r['error'] for r in rs])
        loto[t] = dict(median_ratio=float(np.median(vv / ee)), rank=rank_rho(rs, key))

    # Rows are cross-classified by surrogate fit and test trial. A single-factor
    # Kish correction on trial alone ignores the larger fit effect, so the
    # crossed estimate Var(mean) ~ s2_fit/n_fit + s2_trial/n_trial + s2_res/N is
    # also given. Shares stand in for variance components; it is approximate.
    fits = [(r['model'], r['seed']) for r in rows]
    s_fit, s_tri = shares['surrogate fit (family, seed)'] or 0.0, shares['physical test trial'] or 0.0
    s_res = max(1 - s_fit - s_tri, 0.0)
    n_fit, n_tri = len(group_index(fits)), len(per_trial)
    var_ratio = s_fit / n_fit + s_tri / n_tri + s_res / N
    n_eff_crossed = 1.0 / var_ratio if var_ratio > 0 else float(N)

    # Generalising to a new surrogate is a different claim from generalising to
    # a new experiment, with a different sample size: fits and families.
    fit_idx = group_index(fits)
    fam_idx = group_index([r['model'] for r in rows])
    fits_all_held = sum(bool(hold[i].all()) for i in fit_idx.values())
    fams_all_held = sum(bool(hold[i].all()) for i in fam_idx.values())
    fam_fail = {f: float(1 - hold[i].mean()) for f, i in fam_idx.items()}
    _, p_exch_fit = perm_eta2(margin, fits)
    _, p_conc_fam = perm_chi2(~hold, [r['model'] for r in rows])

    k = int(hold.sum())
    return dict(
        hold_by_trial={t: bool(hold[i].all()) for t, i in group_index(trial).items()},
        hold_by_fit={'%s|%s' % f: bool(hold[i].all()) for f, i in fit_idx.items()},
        hold_by_family={f: bool(hold[i].all()) for f, i in fam_idx.items()},
        fits=n_fit, fits_all_held=fits_all_held, ci_fits=cp(fits_all_held, n_fit),
        families=len(fam_idx), families_all_held=fams_all_held,
        ci_families=cp(fams_all_held, len(fam_idx)), failure_rate_by_family=fam_fail,
        exchangeability_p_fit=p_exch_fit, failure_concentration_p_family=p_conc_fam,
        n_eff_crossed=n_eff_crossed, ci_n_eff_crossed=cp(k / N * n_eff_crossed, n_eff_crossed),
        method=label, side=side, rows=N, held=k, rate=k / N,
        ci_rows=cp(k, N),
        cases=n_cell, cells_all_held=cells_all_held, ci_cells=cp(cells_all_held, n_cell),
        splits_x_trials=n_case, cases_all_held=cases_all_held,
        ci_cases=cp(cases_all_held, n_case),
        trials=len(per_trial), trials_all_held=trials_all_held,
        ci_trials=cp(trials_all_held, len(per_trial)),
        icc_trial=icc, mean_cluster_size=mbar, design_effect=deff, n_eff=n_eff,
        ci_n_eff=cp(k / N * n_eff, n_eff),
        variance_share=shares, exchangeability_eta2=obs, exchangeability_p=p_exch,
        failure_concentration_chi2=chi, failure_concentration_p=p_conc,
        per_trial=per_trial, leave_one_trial_out=loto,
        median_ratio=float(np.median(v / e)), rank=rank_rho(rows, key))


def run():
    OUT.mkdir(exist_ok=True)
    fb = json.loads((HERE / 'fair_baselines/results.json').read_text())['rows']
    methods = [analyse_method(fb, k, lab, side) for k, lab, side in METHODS]

    # Paired comparison against SASES. The same trials and fits score every
    # method, so the right test is an exact sign test on discordant units, not a
    # two-sample test. With four trials the smallest one-sided p attainable is
    # 1/16 = 0.0625, whatever the data.
    from scipy.stats import binom
    sases = methods[0]
    paired = []
    for m in methods[1:]:
        for unit, key in [('test trial', 'hold_by_trial'), ('surrogate fit', 'hold_by_fit'),
                          ('surrogate family', 'hold_by_family')]:
            a, b = sases[key], m[key]
            s_only = sum(a[u] and not b[u] for u in a)
            c_only = sum(b[u] and not a[u] for u in a)
            n = s_only + c_only
            p = float(binom.sf(s_only - 1, n, .5)) if n else None
            paired.append(dict(method=m['method'], unit=unit, units=len(a),
                               sases_only=s_only, competitor_only=c_only, p_one_sided=p,
                               smallest_attainable_p=float(.5 ** len(a))))

    mm = json.loads((HERE / 'multimodel/results.json').read_text())['rows']
    sweep = {}
    for name, flag in [('premise held (target in ball)', 'covered'),
                       ('certificate valid (S <= e)', 'valid')]:
        h = np.array([r[flag] for r in mm], bool)
        trials = group_index([r['trial'] for r in mm])
        cells = group_index([(r['dataset'], r['config'], r['trial']) for r in mm])
        ta = sum(bool(h[i].all()) for i in trials.values())
        ca = sum(bool(h[i].all()) for i in cells.values())
        sweep[name] = dict(rows=len(mm), held=int(h.sum()), ci_rows=cp(int(h.sum()), len(mm)),
                           cells=len(cells), cells_all_held=ca, ci_cells=cp(ca, len(cells)),
                           trials=len(trials), trials_all_held=ta,
                           ci_trials=cp(ta, len(trials)))
    data = dict(methods=methods, paired=paired, sweep=sweep, permutations=NPERM,
                note='CIs are two-sided 95% Clopper-Pearson. The trial level is the only '
                     'one that counts independent physical outcomes.',
                protocol_sha256=hashlib.sha256((HERE / 'INDEPENDENCE_PROTOCOL.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    tmp = OUT / 'results.tmp'
    tmp.write_text(json.dumps(data, indent=1, allow_nan=False))
    tmp.replace(OUT / 'results.json')
    print('-> independence/results.json')
    return data


if __name__ == '__main__':
    run()
