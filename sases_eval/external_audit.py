"""Does the ceiling-centred lower bound work outside the capillary corpus?

Runs the certificate of CEILING_PROTOCOL.md on several datasets under the
generic rules fixed in EXTERNAL_PROTOCOL.md, where the KZ reference exponent
is replaced by the drift slope measured on the training region.

    python external_audit.py            # all datasets
    python external_audit.py yacht      # one dataset

Writes external/results.json and external/rows.csv.
"""
import csv
import hashlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy.stats import beta as beta_distribution
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LinearRegression
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
DATA = HERE / 'external_data'
MIN_CALIBRATION_LEVELS = 3
MODELS = ('linear', 'mlp8', 'mlp16x16')
SEEDS = (0, 1, 2)


# --------------------------------------------------------------------------
# Datasets. Each returns levels sorted by control, plus optional per-sample
# training rows when a dataset has repeats within a level.
# --------------------------------------------------------------------------

class Dataset(object):
    def __init__(self, name, control, targets, kind, samples=None, note=''):
        order = np.argsort(control)
        self.name = name
        self.control = np.asarray(control, float)[order]
        self.targets = np.asarray(targets, float)[order]
        self.kind = kind                      # 'measured' or 'mechanism'
        self.note = note
        # samples: (control_per_sample, target_per_sample) for surrogate fitting
        self.samples = samples
        if np.any(self.control <= 0):
            raise ValueError('%s: control must be positive for a log law' % name)

    @property
    def n_levels(self):
        return len(self.control)

    def training_rows(self, mask):
        """Rows used to fit the surrogate, restricted to the training levels."""
        if self.samples is None:
            return self.control[mask], self.targets[mask]
        keep = np.isin(self.samples[0], self.control[mask])
        return self.samples[0][keep], self.samples[1][keep]


def maybe_log(y, name):
    """Protocol rule: strictly positive and spanning >1 decade -> log."""
    if np.all(y > 0) and (y.max() / y.min()) > 10:
        print('   %s: log-transformed target (span %.1fx)' % (name, y.max() / y.min()))
        return np.log(y), True
    return y, False


def load_capillary(stem, name):
    path = HERE / stem
    with np.load(path, allow_pickle=False) as ds:
        Y, P = ds['Y'], ds['P']
        trial = ds['trial'] if 'trial' in ds.files else None
    if trial is None or len(np.unique(trial)) == len(P):
        levels, targets = P, Y
        samples = None
    else:
        levels = np.array([P[trial == t][0] for t in dict.fromkeys(trial)])
        targets = np.array([Y[trial == t].mean(0) for t in dict.fromkeys(trial)])
        samples = (P.astype(float), Y)
    # Already log PSD; the rule leaves it raw.
    targets, _ = maybe_log(targets, name)
    return Dataset(name, levels, targets, 'measured', samples,
                   'capillary recordings, 20 drive powers')


def load_yacht():
    raw = np.loadtxt(DATA / 'yacht_hydrodynamics.data')
    hulls = sorted(set(tuple(r[:5]) for r in raw))
    froude = np.array(sorted(set(raw[:, 5])))
    table = np.full((len(froude), len(hulls)), np.nan)
    index = {f: i for i, f in enumerate(froude)}
    hidx = {h: j for j, h in enumerate(hulls)}
    for r in raw:
        table[index[r[5]], hidx[tuple(r[:5])]] = r[6]
    if np.isnan(table).any():
        raise SystemExit('yacht: incomplete Froude x hull table')
    table, _ = maybe_log(table, 'yacht')
    return Dataset('yacht', froude, table, 'measured', None,
                   'Delft yacht series, residuary resistance over 22 hulls')


def load_airfoil():
    raw = np.loadtxt(DATA / 'airfoil_self_noise.dat')
    freqs = np.array(sorted(set(raw[:, 0])))[:16]          # 200 Hz .. 6300 Hz
    cfg = {}
    for r in raw:
        cfg.setdefault((r[1], r[2], r[3]), {})[r[0]] = r[5]
    keep = sorted(c for c, d in cfg.items() if all(f in d for f in freqs))
    table = np.array([[cfg[c][f] for c in keep] for f in freqs])
    table, _ = maybe_log(table, 'airfoil')
    return Dataset('airfoil', freqs, table, 'measured', None,
                   'NASA airfoil self-noise, SPL over %d configurations' % len(keep))


# ---- mechanism families: the only place the premise is known in advance ----

def synth(name, slope_fn, levels=16, dim=12, noise=0.05, seed=0, note=''):
    rng = np.random.default_rng(seed)
    P = np.geomspace(1.0, 100.0, levels)
    q = rng.normal(size=dim)
    c0 = rng.normal(size=dim) * 2
    Y = np.array([c0 + slope_fn(np.log(p), q) + rng.normal(size=dim) * noise
                  for p in P])
    return Dataset(name, P, Y, 'mechanism', None, note)


def mechanism_families():
    rng = np.random.default_rng(7)
    kink = np.log(np.geomspace(1.0, 100.0, 16)[10])        # inside the test range
    bend = rng.normal(size=12) * 1.6
    return [
        synth('synth_loglinear', lambda u, q: q * u,
              note='exact log-linear drift; the premise should hold'),
        synth('synth_break',
              lambda u, q: q * u + (bend * (u - kink) if u > kink else 0.0),
              note='slope changes above a threshold; the premise should FAIL'),
        synth('synth_curved', lambda u, q: q * u + 0.30 * q * u ** 2,
              note='quadratic drift; degradation should grow with delta'),
    ]


def load_burgers():
    """Real numerics: 1-D viscous Burgers, energy spectrum vs forcing amplitude.

    Spectral solver, fixed initial phases, amplitude swept geometrically. At
    large amplitude shocks steepen and the spectral slope changes on its own,
    so whether the premise holds here is not known in advance.
    """
    n, L, nu, T, steps = 256, 2 * np.pi, 5e-3, 0.5, 6000
    x = np.linspace(0, L, n, endpoint=False)
    k = np.fft.rfftfreq(n, d=L / n) * 2 * np.pi
    mask = np.abs(k) < (2.0 / 3.0) * k.max()                # 2/3 dealiasing
    rng = np.random.default_rng(3)
    phase = rng.uniform(0, 2 * np.pi, 6)
    base = sum(np.sin((m + 1) * x + phase[m]) / (m + 1) for m in range(6))
    amps = np.geomspace(0.05, 3.0, 14)
    edges = np.geomspace(1, n // 3, 11)
    dt = T / steps

    def rhs(vh):
        v = np.fft.irfft(vh, n)
        conv = 0.5j * k * np.fft.rfft(v * v) * mask
        return -conv - nu * k ** 2 * vh

    rows = []
    for a in amps:
        uh = np.fft.rfft(a * base) * mask
        for _ in range(steps):                              # RK2 (midpoint)
            uh = uh + dt * rhs(uh + 0.5 * dt * rhs(uh))
        if not np.all(np.isfinite(uh)):
            raise SystemExit('burgers: solver diverged at A=%.3f' % a)
        power = np.abs(uh) ** 2 + 1e-30
        kk = np.arange(len(power))
        rows.append([np.log(power[(kk >= edges[b]) & (kk < edges[b + 1])].mean())
                     for b in range(10)])
        print('   burgers A=%.3f  ln E %.2f .. %.2f'
              % (a, min(rows[-1]), max(rows[-1])), flush=True)
    return Dataset('pde_burgers', amps, np.array(rows), 'mechanism', None,
                   '1-D viscous Burgers spectra vs forcing amplitude')


# --------------------------------------------------------------------------
# Certificate
# --------------------------------------------------------------------------

def drift_slope(control, targets):
    """Least-squares slope of the target against ln(control)."""
    u = np.log(control)
    u = u - u.mean()
    denom = float(u @ u)
    if denom <= 0:
        raise ValueError('degenerate control range')
    return (u @ (targets - targets.mean(0))) / denom


def certificate(prediction, ceiling_target, slope, delta, rate):
    if delta < 0 or rate < 0:
        raise ValueError('delta and rate must be non-negative')
    centre = ceiling_target + slope * delta
    radius = rate * delta
    return centre, radius, max(float(np.linalg.norm(prediction - centre) - radius), 0.0)


def fit_surrogate(kind, seed, x, y):
    if kind == 'linear':
        model = LinearRegression()
    else:
        layers = (8,) if kind == 'mlp8' else (16, 16)
        model = MLPRegressor(hidden_layer_sizes=layers, max_iter=20000,
                             random_state=seed, learning_rate_init=0.01,
                             tol=1e-7, n_iter_no_change=200)
    pipe = make_pipeline(StandardScaler(), model)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', ConvergenceWarning)
        pipe.fit(np.log(np.asarray(x, float)).reshape(-1, 1), y)
    return pipe


def predict(pipe, control):
    return pipe.predict(np.array([[np.log(control)]]))[0]


def audit(ds):
    """Every admissible (ceiling, test level, model, seed) row for one dataset."""
    n = ds.n_levels
    n_train = n // 2
    train_mask = np.zeros(n, bool)
    train_mask[:n_train] = True
    x_tr, y_tr = ds.training_rows(train_mask)
    if len(np.unique(x_tr)) < 2:
        raise SystemExit('%s: not enough distinct training levels' % ds.name)
    q_ref = drift_slope(np.asarray(x_tr, float), np.asarray(y_tr, float))

    # The surrogate depends only on the training region, which no ceiling
    # changes, so fit each one once rather than per ceiling.
    fitted = [(kind, seed, fit_surrogate(kind, seed, x_tr, y_tr))
              for kind in MODELS for seed in (SEEDS if kind != 'linear' else (0,))]

    rows = []
    for ceiling in range(n_train + MIN_CALIBRATION_LEVELS - 1, n - 1):
        cal = slice(n_train, ceiling + 1)
        q_cal = drift_slope(ds.control[cal], ds.targets[cal])
        rate = float(np.linalg.norm(q_cal - q_ref))
        # Rule B boundary term: how badly the fitted law misses the calibration
        # levels it was fitted on. Calibration labels only, no test label.
        u_cal = np.log(ds.control[cal])
        law = ds.targets[cal].mean(0) + np.outer(u_cal - u_cal.mean(), q_cal)
        boundary = float(np.max(np.linalg.norm(ds.targets[cal] - law, axis=1)))
        # Rule C: the incumbent capillary rule, fixed 1/2 reference exponent.
        rate_c = float(np.linalg.norm(q_cal - 0.5))
        for kind, seed, pipe in fitted:
            for t in range(ceiling + 1, n):
                delta = float(np.log(ds.control[t] / ds.control[ceiling]))
                pred = predict(pipe, ds.control[t])
                centre, radius, S = certificate(
                    pred, ds.targets[ceiling], q_cal, delta, rate)
                # Rules B and C share the centre; only the radius differs.
                radius_b = radius + boundary
                S_b = max(float(np.linalg.norm(pred - centre) - radius_b), 0.0)
                radius_c = rate_c * delta
                S_c = max(float(np.linalg.norm(pred - centre) - radius_c), 0.0)
                truth = ds.targets[t]
                e = float(np.linalg.norm(pred - truth))
                residual = float(np.linalg.norm(truth - centre))
                covered = bool(residual <= radius + 1e-9)
                covered_b = bool(residual <= radius_b + 1e-9)
                if covered and S > e + 1e-8:
                    raise AssertionError('%s: rule A reverse triangle violated' % ds.name)
                covered_c = bool(residual <= radius_c + 1e-9)
                if covered_b and S_b > e + 1e-8:
                    raise AssertionError('%s: rule B reverse triangle violated' % ds.name)
                if covered_c and S_c > e + 1e-8:
                    raise AssertionError('%s: rule C reverse triangle violated' % ds.name)
                rows.append(dict(
                    dataset=ds.name, kind=ds.kind, model=kind, seed=seed,
                    ceiling_level=int(ceiling), test_level=int(t),
                    ceiling_control=float(ds.control[ceiling]),
                    test_control=float(ds.control[t]), delta=delta,
                    radius=float(radius), rate=rate, boundary=boundary,
                    margin=float(radius - residual),
                    tube_residual=residual, S=float(S), e=e, covered=covered,
                    useful=bool(S > 1e-9),
                    S_over_e=float(S / e) if e > 0 else 0.0,
                    radius_b=float(radius_b), S_b=float(S_b), covered_b=covered_b,
                    margin_b=float(radius_b - residual),
                    useful_b=bool(S_b > 1e-9),
                    S_over_e_b=float(S_b / e) if e > 0 else 0.0,
                    radius_c=float(radius_c), S_c=float(S_c), covered_c=covered_c,
                    margin_c=float(radius_c - residual),
                    useful_c=bool(S_c > 1e-9),
                    S_over_e_c=float(S_c / e) if e > 0 else 0.0))
    return rows


def cp_lower(successes, trials, level=0.95):
    if trials == 0 or successes == 0:
        return 0.0                      # beta.ppf is undefined at a=0 (returns nan)
    if successes == trials:
        return float((1 - level) ** (1.0 / trials))
    return float(beta_distribution.ppf(1 - level, successes, trials - successes + 1))


def summarize(rows):
    if not rows:
        return {}
    # A distinct case is one (dataset, test level); models/seeds/ceilings repeat it.
    cases = {}
    for r in rows:
        cases.setdefault((r['dataset'], r['test_level']), []).append(r)
    out = dict(rows=len(rows), distinct_cases=len(cases),
               median_delta=float(np.median([r['delta'] for r in rows])),
               max_delta=float(np.max([r['delta'] for r in rows])))
    for tag, cov, s_e, use, marg in (
            ('', 'covered', 'S_over_e', 'useful', 'margin'),
            ('_b', 'covered_b', 'S_over_e_b', 'useful_b', 'margin_b'),
            ('_c', 'covered_c', 'S_over_e_c', 'useful_c', 'margin_c')):
        worst = sum(1 for v in cases.values() if all(x[cov] for x in v))
        out['pooled_coverage' + tag] = float(np.mean([r[cov] for r in rows]))
        out['all_configurations_covered_cases' + tag] = worst
        out['cp95_lower_distinct' + tag] = cp_lower(worst, len(cases))
        out['useful_fraction' + tag] = float(np.mean([r[use] for r in rows]))
        out['mean_S_over_e' + tag] = float(np.mean([r[s_e] for r in rows]))
        out['min_margin' + tag] = float(np.min([r[marg] for r in rows]))
    return out


def build(selection=None):
    loaders = [
        ('capillary_psdt', lambda: load_capillary('spec.npz', 'capillary_psdt')),
        ('capillary_psdk', lambda: load_capillary('spec_k.npz', 'capillary_psdk')),
        ('yacht', load_yacht),
        ('airfoil', load_airfoil),
        ('pde_burgers', load_burgers),
    ]
    out = []
    for name, fn in loaders:
        if selection and name not in selection:
            continue
        print(' loading %s' % name, flush=True)
        out.append(fn())
    for ds in mechanism_families():
        if not selection or ds.name in selection:
            out.append(ds)
    return out


def run(selection=None):
    datasets = build(selection)
    rows, summary = [], {}
    for ds in datasets:
        print('\n== %s (%s, %d levels, %d dims) %s'
              % (ds.name, ds.kind, ds.n_levels, ds.targets.shape[1], ds.note), flush=True)
        got = audit(ds)
        rows.extend(got)
        summary[ds.name] = dict(summarize(got), kind=ds.kind, note=ds.note,
                                levels=ds.n_levels, dims=int(ds.targets.shape[1]))
        s = summary[ds.name]
        print('   rows %3d / %d distinct levels | max delta %.2f' %
              (s['rows'], s['distinct_cases'], s['max_delta']), flush=True)
        print('   rule A: coverage %.3f  S/e %.3f  useful %.2f' %
              (s['pooled_coverage'], s['mean_S_over_e'], s['useful_fraction']), flush=True)
        print('   rule B: coverage %.3f  S/e %.3f  useful %.2f' %
              (s['pooled_coverage_b'], s['mean_S_over_e_b'],
               s['useful_fraction_b']), flush=True)
        print('   rule C: coverage %.3f  S/e %.3f  useful %.2f   (incumbent)' %
              (s['pooled_coverage_c'], s['mean_S_over_e_c'],
               s['useful_fraction_c']), flush=True)

    measured = [r for r in rows if r['kind'] == 'measured']
    summary['ALL_MEASURED'] = dict(summarize(measured), kind='measured',
                                   note='pooled over measured datasets only')
    out = HERE / 'external'
    out.mkdir(exist_ok=True)
    result = dict(
        summary=summary, rows=rows,
        protocol_sha256=hashlib.sha256((HERE / 'EXTERNAL_PROTOCOL.md').read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        inference='Clopper-Pearson bounds are nominal; levels within a dataset '
                  'share an apparatus or solver and are not independent.')
    tmp = out / 'results.tmp'
    tmp.write_text(json.dumps(result, allow_nan=False))
    tmp.replace(out / 'results.json')
    fields = [k for k in rows[0] if k not in ('kind',)]
    with (out / 'rows.csv').open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('\n--- pooled over measured datasets ---')
    print(json.dumps(summary['ALL_MEASURED'], indent=2))
    return result


if __name__ == '__main__':
    run(set(sys.argv[1:]) or None)
