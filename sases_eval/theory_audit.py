"""Retrospective, calibration-only theory candidates; see RERUN_PROTOCOL.md."""
import csv
import hashlib
import os
import json
import platform
from pathlib import Path
from importlib.metadata import version

import numpy as np
from scipy.stats import beta as beta_distribution

HERE = Path(__file__).resolve().parent
METHODS = ('fitted', 'historical_2x', 'theory_slope', 'theory_boundary')


def theory_parameters(q_high, anchor_y, ceiling_y, shift_at_ceiling, flux_power=1.0):
    """Only calibration arrays enter this function; no test labels or globals.

    r(u) = y_anchor - y(u) - c(u) - c0.
    If ||dy/du - q_high|| <= k on [u0,u], integration gives
    ||r(u)|| <= ||r(u0)|| + k*(u-u0). The KZ gap supplies a candidate
    k, not evidence that the derivative assumption holds.
    """
    q = np.asarray(q_high, float)
    k = float(np.linalg.norm(q - 0.5 * flux_power))
    r0 = float(np.linalg.norm(np.asarray(anchor_y) - ceiling_y - shift_at_ceiling))
    return dict(kappa=k, boundary=r0, flux_power=flux_power)


def allowance(method, delta, fitted, theory):
    if delta < 0:
        raise ValueError('This audit only implements extrapolation beyond the ceiling')
    if method == 'fitted':
        return fitted * delta
    if method == 'historical_2x':
        return 2 * fitted * delta
    if method == 'theory_slope':
        return theory['kappa'] * delta
    if method == 'theory_boundary':
        return theory['boundary'] + theory['kappa'] * delta
    raise ValueError(method)


def score(defect, b, bt):
    return max(float(defect - b - bt), 0.0) if np.isfinite(bt) else None


def binomial_reference(k, n):
    return 0.0 if k == 0 else float(beta_distribution.ppf(.05, k, n-k+1))


def summarize(rows):
    scored = [r for r in rows if r['S'] is not None]
    groups = {}
    for r in scored:
        groups.setdefault(r['trial'], []).append(r)
    k = sum(all(r['covered'] for r in rs) for rs in groups.values())
    kv = sum(all(r['valid'] for r in rs) for rs in groups.values())
    n = len(groups)
    return dict(rows=len(rows), scored=len(scored), unique_test_trials=n,
                pooled_coverage=float(np.mean([r['covered'] for r in scored])) if scored else None,
                all_configurations_covered_trials=k,
                cp95_lower_nominal=binomial_reference(k, n) if n else None,
                all_configurations_valid_trials=kv,
                validity_cp95_lower_nominal=binomial_reference(kv, n) if n else None,
                pooled_validity=float(np.mean([r['valid'] for r in scored])) if scored else None,
                useful_fraction=float(np.mean([r['S'] > 1 for r in scored])) if scored else None,
                mean_S_over_e=float(np.mean([r['S']/r['e'] for r in scored if r['e'] > 0])) if scored else None,
                min_margin=min((r['margin'] for r in scored), default=None),
                both_premises_rows=sum(r['covered'] and r['anchor_covered'] for r in scored))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run():
    from piecewise import NAMES, TP, TM, TRAIN, ANCHOR, lp, slopes
    from honest_beta import law_from
    from setupc import splits, kappa_defensible, fit_surrogate
    from threadpoolctl import threadpool_limits

    outdir = HERE / 'rerun'
    outdir.mkdir(exist_ok=True)
    fits, rows = [], []
    canonical = [(f'canonical_{hi}', [n for n in NAMES if 106 <= TP[n] <= hi],
                  [n for n in NAMES if TP[n] > hi], [ANCHOR]) for hi in (146, 192)]
    configs = canonical + [(f'sweep_{i:02d}', lc, ts, TRAIN) for i, (lc, ts) in enumerate(splits())]
    # Freeze all law allowances before computing any test residual.
    for tag, lc, ts, anchors in configs:
        assert not (set(lc) & set(ts) or set(TRAIN) & set(ts) or set(TRAIN) & set(lc))
        c, c0, _, _ = law_from(lc)
        top = max(lc, key=lambda n: TP[n])
        for a in anchors:
            theory = theory_parameters(slopes(lc), TM[a], TM[top], c(lp[a], lp[top]) + c0)
            kap, nr = kappa_defensible(lc, a)
            fits.append(dict(config=tag, lawcal=lc, test=ts, anchor=a, ceiling=top,
                             q_high=slopes(lc).tolist(), theory=theory,
                             fitted_kappa=float(kap) if np.isfinite(kap) else None,
                             holdout_ratio_count=nr))
    (outdir / 'calibration_fits.json').write_text(json.dumps(fits, indent=2, allow_nan=False))
    print('Frozen calibration fits:', len(fits), flush=True)
    models = [('mlp8', s) for s in range(3)] + [('mlp16x16', s) for s in range(3)] + [('linear', 0)]
    with threadpool_limits(limits=1):
        for kind, seed in models:
            print('Fitting', kind, seed, flush=True)
            g, b_loto = fit_surrogate(kind, seed)
            for fit in fits:
                # Sweep uses one fixed model to avoid manufacturing replicates.
                if fit['config'].startswith('sweep') and (kind, seed) != ('mlp8', 0):
                    continue
                lc, a, top = fit['lawcal'], fit['anchor'], fit['ceiling']
                c, c0, _, _ = law_from(lc)
                fa = g(np.array([[lp[a]]]))[0]
                b_anchor = float(np.linalg.norm(fa - TM[a]))
                kap = fit['fitted_kappa'] if fit['fitted_kappa'] is not None else float('nan')
                for t in fit['test']:
                    delta = float(lp[t] - lp[top])
                    ft = g(np.array([[lp[t]]]))[0]
                    shift = c(lp[a], lp[t]) + c0
                    D = float(np.linalg.norm(fa - ft - shift))
                    z = float(np.linalg.norm(TM[a] - TM[t] - shift))
                    e = float(np.linalg.norm(ft - TM[t]))
                    for method in METHODS:
                        bt = allowance(method, delta, kap, fit['theory'])
                        for b_mode, b in [('legacy_loto', b_loto), ('labelled_anchor', b_anchor)]:
                            S = score(D, b, bt)
                            covered = bool(z <= bt + 1e-10) if np.isfinite(bt) else None
                            valid = bool(S <= e + 1e-10) if S is not None else None
                            anchor_ok = bool(b_anchor <= b + 1e-10)
                            if covered and anchor_ok:
                                assert valid, 'Triangle inequality violated'
                            rows.append(dict(config=fit['config'], model=kind, seed=seed,
                                             method=method, b_mode=b_mode, anchor=a, trial=t,
                                             P=float(TP[t]), ceiling=float(TP[top]), delta=delta,
                                             D=D, b=b, beta=float(bt) if np.isfinite(bt) else None,
                                             zeta=z, margin=float(bt-z) if np.isfinite(bt) else None,
                                             S=S, e=e, covered=covered, valid=valid,
                                             anchor_covered=anchor_ok))
    with (outdir / 'audit_rows.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {}
    for group in ('canonical_146', 'canonical_192', 'sweep'):
        for method in METHODS:
            for bm in ('legacy_loto', 'labelled_anchor'):
                key = '|'.join((group, method, bm))
                rs = [r for r in rows if r['config'].startswith(group) and r['method'] == method
                      and r['b_mode'] == bm and r['model'] == 'mlp8' and r['seed'] == 0]
                summary[key] = summarize(rs)
    old, new = np.load(HERE/'spec_before_rerun.npz'), np.load(HERE/'spec.npz')
    comparison = {k: bool(np.array_equal(old[k], new[k], equal_nan=True))
                  if new[k].dtype.kind in 'fc' else bool(np.array_equal(old[k], new[k])) for k in new.files}
    manifest = dict(python=platform.python_version(),
                    versions={p: version(p) for p in ['numpy', 'scipy', 'scikit-learn', 'h5py', 'matplotlib', 'reportlab']},
                    sha256={str(p.relative_to(HERE.parent)): (sha(p) if p.exists() else None) for p in
                            [Path(os.environ.get('SASES_DATASET') or HERE.parent/'dataset')/'b200_50MB.h5', HERE/'spec.npz',
                             HERE/'RERUN_PROTOCOL.md', HERE/'theory_audit.py', HERE/'build_dataset.py',
                             HERE/'capillary2.py', HERE/'piecewise.py', HERE/'honest_beta.py', HERE/'setupc.py', HERE/'sases.py']},
                    rebuilt_arrays_exactly_equal=comparison,
                    max_abs_spectrum_difference=float(np.max(np.abs(old['Y']-new['Y']))),
                    train_trials=TRAIN, models=models, summary=summary,
                    inference='CP bounds are nominal IID-binomial references, not guarantees for power-selected trials.')
    (outdir/'results.json').write_text(json.dumps(manifest, indent=2, allow_nan=False))
    for key, result in summary.items():
        if key.endswith('legacy_loto'):
            print(key, json.dumps(result), flush=True)
    return rows, fits, manifest


if __name__ == '__main__':
    run()
