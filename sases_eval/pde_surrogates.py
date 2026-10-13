"""Anchor-symmetry certificate on neural PDE surrogates. Protocol: PDE_PROTOCOL.md.
Run with the torch environment:  ..\\.venv-torch\\Scripts\\python.exe pde_surrogates.py all
Writes pde/<system>_*.  Exact Fourier solutions; PDEBench-style initial conditions.
"""
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

HERE = Path(__file__).resolve().parent
OUT = HERE / 'pde'
N = 128
X = np.arange(N) / N
K = np.fft.fftfreq(N, d=1.0 / N)                 # integer wavenumbers
NU_AD = 0.003
SYS = {
    'advection': dict(p_tr=(0.1, 1.0), p_te=[1.5, 2.0, 3.0, 4.0], t_max=2.0, law='exact'),
    'diffusion': dict(p_tr=(0.002, 0.02), p_te=[0.03, 0.04, 0.06, 0.08], t_max=1.0, law='exact'),
    'advdiff': dict(p_tr=(0.1, 1.0), p_te=[1.5, 2.0, 3.0, 4.0], t_max=2.0, law='approx'),
}
M_ANCH, ALPHA = 4, 0.10
torch.set_num_threads(16)


# ------------------------------------------------------------------ exact solutions
def initial(rng, n):
    u = np.zeros((n, N))
    for _ in range(2):
        k = rng.integers(1, 9, n)[:, None]; A = rng.uniform(0, 1, n)[:, None]; ph = rng.uniform(0, 2 * np.pi, n)[:, None]
        u += A * np.sin(2 * np.pi * k * X[None, :] + ph)
    return u


def solve(system, u0, p, t):
    """Exact solution at time t for each row (p, t arrays)."""
    U = np.fft.fft(u0, axis=1)
    p = np.asarray(p)[:, None]; t = np.asarray(t)[:, None]
    if system == 'advection':
        F = np.exp(-2j * np.pi * K[None, :] * p * t)
    elif system == 'diffusion':
        F = np.exp(-(2 * np.pi * K[None, :]) ** 2 * p * t)
    else:
        F = np.exp(-2j * np.pi * K[None, :] * p * t - NU_AD * (2 * np.pi * K[None, :]) ** 2 * t)
    return np.real(np.fft.ifft(U * F, axis=1))


def dataset(system, n, rng, test=False):
    s = SYS[system]
    u0 = initial(rng, n)
    lo, hi = s['p_tr']
    if system != 'diffusion':
        p = rng.uniform(lo, hi, n)
    else:
        p = np.exp(rng.uniform(np.log(lo), np.log(hi), n))
    t = rng.uniform(0, s['t_max'], n)
    return u0, p, t, solve(system, u0, p, t)


# ------------------------------------------------------------------ surrogates
class SpectralConv1d(nn.Module):
    def __init__(self, c, modes):
        super().__init__()
        self.modes = modes
        self.w = nn.Parameter((1 / c) * torch.randn(c, c, modes, dtype=torch.cfloat))

    def forward(self, x):
        xf = torch.fft.rfft(x)
        out = torch.zeros(x.shape[0], x.shape[1], x.shape[-1] // 2 + 1, dtype=torch.cfloat)
        out[:, :, :self.modes] = torch.einsum('bix,iox->box', xf[:, :, :self.modes], self.w)
        return torch.fft.irfft(out, n=x.shape[-1])


class FNO1d(nn.Module):
    """Li et al. (2021): lift, four Fourier layers with pointwise skip, project."""

    def __init__(self, modes=16, width=32):
        super().__init__()
        self.lift = nn.Conv1d(4, width, 1)
        self.spec = nn.ModuleList([SpectralConv1d(width, modes) for _ in range(4)])
        self.skip = nn.ModuleList([nn.Conv1d(width, width, 1) for _ in range(4)])
        self.proj = nn.Sequential(nn.Conv1d(width, 128, 1), nn.GELU(), nn.Conv1d(128, 1, 1))

    def forward(self, z):
        h = self.lift(z)
        for k, (s, w) in enumerate(zip(self.spec, self.skip)):
            h = s(h) + w(h)
            if k < 3:
                h = nn.functional.gelu(h)
        return self.proj(h)[:, 0]


class ResCNN(nn.Module):
    def __init__(self, depth=4, width=48):
        super().__init__()
        self.inp = nn.Conv1d(4, width, 5, padding=2, padding_mode='circular')
        self.blocks = nn.ModuleList([nn.Sequential(nn.Conv1d(width, width, 5, padding=2, padding_mode='circular'),
                                                   nn.GELU(), nn.Conv1d(width, width, 5, padding=2, padding_mode='circular'))
                                     for _ in range(depth)])
        self.out = nn.Conv1d(width, 1, 1)

    def forward(self, z):
        h = self.inp(z)
        for b in self.blocks:
            h = h + b(nn.functional.gelu(h))
        return self.out(h)[:, 0]


class MLP(nn.Module):
    def __init__(self, hidden=512):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(N + 2, hidden), nn.GELU(), nn.Linear(hidden, hidden), nn.GELU(),
                                 nn.Linear(hidden, N))

    def forward(self, z):
        return self.net(torch.cat([z[:, 0], z[:, 1, :1], z[:, 2, :1]], 1))


def zoo():
    out = []
    for modes in (8, 16):
        for seed in (0, 1, 2):
            out.append(('fno_m%d' % modes, seed, lambda m=modes: FNO1d(m, 32)))
    for depth in (3, 6):
        for seed in (0, 1):
            out.append(('rescnn_d%d' % depth, seed, lambda d=depth: ResCNN(d)))
    for hidden in (256, 1024):
        out.append(('mlp_h%d' % hidden, 0, lambda h=hidden: MLP(h)))
    return out


def features(system, u0, p, t):
    s = SYS[system]
    lo, hi = s['p_tr']
    pn = (np.log(p) - np.log(lo)) / (np.log(hi) - np.log(lo))      # 0..1 inside the training range
    tn = t / s['t_max']
    z = np.stack([u0, np.repeat(pn[:, None], N, 1), np.repeat(tn[:, None], N, 1), np.repeat(X[None, :], len(p), 0)], 1)
    return torch.tensor(z, dtype=torch.float32)


def train(system, model, seed, data, epochs=60):
    torch.manual_seed(seed); np.random.seed(seed)
    u0, p, t, u = data
    Z = features(system, u0, p, t); Y = torch.tensor(u, dtype=torch.float32)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    for ep in range(epochs):
        perm = torch.randperm(len(Z))
        for i in range(0, len(Z), 64):
            ix = perm[i:i + 64]
            opt.zero_grad()
            loss = ((model(Z[ix]) - Y[ix]) ** 2).mean()
            loss.backward(); opt.step()
        sched.step()
    model.eval()
    return model


def predict(system, model, u0, p, t):
    with torch.no_grad():
        out = []
        for i in range(0, len(p), 512):
            out.append(model(features(system, u0[i:i + 512], p[i:i + 512], t[i:i + 512])).numpy())
    return np.concatenate(out)


rms = lambda a: np.sqrt(np.mean(a ** 2, axis=-1))


def conformal(scores, level):
    n = len(scores); k = math.ceil((n + 1) * level)
    return float(np.sort(scores)[min(k, n) - 1])


# ------------------------------------------------------------------ experiment
def test_set(system, rng, per=100):
    """per initial conditions x each test parameter, t drawn so that an anchor exists."""
    s = SYS[system]; p_max, t_max = s['p_tr'][1], s['t_max']
    u0s, ps, ts = [], [], []
    for p in s['p_te']:
        u0s.append(initial(rng, per)); ps.append(np.full(per, p))
        ts.append(rng.uniform(0.05 * t_max, 0.98 * t_max * p_max / p, per))        # p t <= p_max t_max
    u0, p, t = np.concatenate(u0s), np.concatenate(ps), np.concatenate(ts)
    return u0, p, t, solve(system, u0, p, t)


def run(system):
    OUT.mkdir(exist_ok=True)
    s = SYS[system]; rng = np.random.default_rng({'advection': 1, 'diffusion': 2, 'advdiff': 3}[system])
    tr = dataset(system, 4000, rng); cal = dataset(system, 1000, rng)
    p_max, t_max = s['p_tr'][1], s['t_max']
    tests = {'dev': test_set(system, rng)}
    tests['confirm'] = test_set(system, np.random.default_rng(100 + {'advection': 1, 'diffusion': 2, 'advdiff': 3}[system]))
    te_u0, te_p, te_t, te_u = tests['dev']
    # Law allowance (approximate law only): kappa from in-range symmetry pairs, labels only.
    kappa = 0.0
    if s['law'] != 'exact':
        u0 = tr[0][:400]; p1 = rng.uniform(0.2, p_max, 400); t1 = rng.uniform(0.1, 0.5 * t_max, 400)
        top = np.log(np.maximum(np.minimum(p1 / s['p_tr'][0], t_max / t1), 1.3))
        lp = np.exp(rng.uniform(np.log(1.2), top, 400))
        r1 = rms(solve(system, u0, p1, t1) - solve(system, u0, p1 / lp, lp * t1))
        kappa = float(np.max(r1 / np.log(lp)))
    # Lipschitz baseline constant from training labels (pairs in parameter-time space).
    i, j = rng.integers(0, 4000, 3000), rng.integers(0, 4000, 3000)
    same_u0 = solve(system, tr[0][i], tr[1][j], tr[2][j])                 # same initial condition, other (p, t)
    dz = np.hypot((np.log(tr[1][i]) - np.log(tr[1][j])), (tr[2][i] - tr[2][j]) / t_max)
    L = 2 * float(np.max(rms(tr[3][i] - same_u0) / np.maximum(dz, 1e-6)))
    rows, meta = [], []
    for name, seed, make in zoo():
        t0 = time.time()
        model = train(system, make(), seed, tr)
        f_cal = predict(system, model, *cal[:3])
        cal_err = rms(f_cal - cal[3])
        b = conformal(cal_err, 1 - ALPHA / M_ANCH)
        q90 = conformal(cal_err, 0.9)
        cal_z = cal[1] * cal[2]
        edges = np.quantile(cal_z, np.linspace(0, 1, 11)); edges[0], edges[-1] = -np.inf, np.inf
        zbin = np.digitize(cal_z, edges[1:-1])
        b_bin = np.array([conformal(cal_err[zbin == k], 1 - ALPHA / M_ANCH) for k in range(10)])
        (OUT / 'models').mkdir(exist_ok=True)
        torch.save(model.state_dict(), OUT / 'models' / ('%s_%s_s%d.pt' % (system, name, seed)))
        for tag, (te_u0, te_p, te_t, te_u) in tests.items():
            lam_lo, lam_hi = te_p / p_max, np.minimum(t_max / te_t, te_p / s['p_tr'][0])
            ok = lam_lo <= lam_hi
            lams = np.exp(np.linspace(np.log(lam_lo), np.log(np.maximum(lam_lo, lam_hi)), M_ANCH)).T
            b_loc = b_bin[np.digitize(te_p * te_t, edges[1:-1])]
            fx = predict(system, model, te_u0, te_p, te_t)
            e = rms(fx - te_u)
            S = np.zeros(len(te_p)); S_nob = np.zeros(len(te_p)); S_loc = np.zeros(len(te_p))
            prem = np.ones(len(te_p), bool)
            for k in range(M_ANCH):
                fa = predict(system, model, te_u0, te_p / lams[:, k], te_t * lams[:, k])
                D = rms(fa - fx)
                beta = 2 * kappa * np.log(lams[:, k])
                S = np.maximum(S, np.where(ok, np.maximum(D - b - beta, 0), 0))
                S_nob = np.maximum(S_nob, np.where(ok, np.maximum(D - b, 0), 0))
                S_loc = np.maximum(S_loc, np.where(ok, np.maximum(D - b_loc - beta, 0), 0))
                if s['law'] != 'exact':
                    res = rms(solve(system, te_u0, te_p / lams[:, k], te_t * lams[:, k]) - te_u)
                    prem &= res <= beta + 1e-12
            pa = np.minimum(te_p, p_max)
            fl = predict(system, model, te_u0, pa, te_t)
            S_lip = np.maximum(rms(fx - fl) - b - L * np.abs(np.log(te_p) - np.log(pa)), 0)
            for n_ in range(len(te_p)):
                rows.append(dict(set=tag, model=name, seed=seed, p=float(te_p[n_]), t=float(te_t[n_]), point=n_,
                                 e=float(e[n_]), S=float(S[n_]), S_nobeta=float(S_nob[n_]), S_loc=float(S_loc[n_]),
                                 S_lip=float(S_lip[n_]), q90=q90, prem=bool(prem[n_]), ok=bool(ok[n_])))
        e = np.array([r['e'] for r in rows if r['model'] == name and r['seed'] == seed and r['set'] == 'dev'])
        meta.append(dict(model=name, seed=seed, b=b, cal_rmse=float(np.median(cal_err)), test_e=float(np.median(e)),
                         seconds=round(time.time() - t0, 1)))
        print('%-10s %-11s seed %d  b %.4f  in-range %.4f  test e %.4f  (%.0fs)'
              % (system, name, seed, b, np.median(cal_err), np.median(e), time.time() - t0), flush=True)
    json.dump(dict(rows=rows, meta=meta, kappa=kappa, L=L), open(OUT / ('%s.json' % system), 'w'))


def report():
    from scipy.stats import spearmanr
    res, lines = {}, []
    for system in SYS:
        f = OUT / ('%s.json' % system)
        if not f.exists():
            continue
        d = json.load(open(f))
        for tag in ('dev', 'confirm'):
            R = [r for r in d['rows'] if r.get('set', 'dev') == tag]
            if not R:
                continue
            g = lambda k: np.array([r[k] for r in R])
            e, S, Sl, Sn, Sloc, q, prem = g('e'), g('S'), g('S_lip'), g('S_nobeta'), g('S_loc'), g('q90'), g('prem')
            fno = np.array([r['model'].startswith('fno') for r in R])
            pts = {}
            for i, r in enumerate(R):
                pts.setdefault(r['point'], []).append(i)
            rho = lambda v: float(np.nanmean([spearmanr(v[ix], e[ix]).correlation for ix in pts.values()
                                              if np.ptp(v[ix]) > 1e-12 and np.ptp(e[ix]) > 1e-12] or [np.nan]))
            o = dict(rows=len(R), valid=float(np.mean(S <= e + 1e-9)), valid_nobeta=float(np.mean(Sn <= e + 1e-9)),
                     Se=float(np.median(S / e)), nonzero=float(np.mean(S > 0)), rho=rho(S),
                     valid_loc=float(np.mean(Sloc <= e + 1e-9)), Se_loc=float(np.median(Sloc / e)),
                     Se_loc_fno=float(np.median((Sloc / e)[fno])), Se_loc_pos=float(np.median((Sloc / e)[Sloc > 0])) if (Sloc > 0).any() else 0.0,
                     nonzero_loc=float(np.mean(Sloc > 0)), rho_loc=rho(Sloc),
                     valid_lip=float(np.mean(Sl <= e + 1e-9)), Se_lip=float(np.median(Sl / e)),
                     nonzero_lip=float(np.mean(Sl > 0)), rho_lip=rho(Sl), conf_cover=float(np.mean(e <= q)),
                     premise=float(prem.mean()), kappa=d['kappa'], L=d['L'])
            res['%s|%s' % (system, tag)] = o
            lines.append('%-10s %-7s | global b: valid %.3f (no beta %.3f) S>0 %.2f S/e %.2f rho %.2f | local b(z): valid %.3f '
                         'S>0 %.2f S/e %.2f (FNO %.2f, when >0 %.2f) rho %.2f | Lipschitz S>0 %.2f | conformal cover %.2f | premise %.3f'
                         % (system, tag, o['valid'], o['valid_nobeta'], o['nonzero'], o['Se'], o['rho'], o['valid_loc'],
                            o['nonzero_loc'], o['Se_loc'], o['Se_loc_fno'], o['Se_loc_pos'], o['rho_loc'], o['nonzero_lip'],
                            o['conf_cover'], o['premise']))
        res[system + '|meta'] = d['meta']
    (OUT / 'results.json').write_text(json.dumps(res, indent=1)); (OUT / 'report.txt').write_text(chr(10).join(lines))
    print(chr(10).join(lines))


if __name__ == '__main__':
    if sys.argv[1] == 'all':
        for sy in SYS:
            run(sy)
        report()
    elif sys.argv[1] == 'report':
        report()
    else:
        run(sys.argv[1])
