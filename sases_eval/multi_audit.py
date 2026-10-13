"""The break-law certificate on seven datasets. Protocol: MULTI_DATASET_PROTOCOL.md.

  python multi_audit.py build <name>      raw files -> multi/<name>_records.npz (new datasets)
  python multi_audit.py run <name> ...    surrogates + certificate -> multi/<name>_rows.pkl
  python multi_audit.py report

Total bound, three terms: S = max(D - b - beta, 0), D = ||f(x) - f(a) - (c(x) - c(a))||,
b = ||f(a) - y(a)|| (exact: y(a) is measured), beta the law allowance. The ceiling form
S_c = max(||f(x) - y(a) - (c(x) - c(a))|| - beta, 0) >= S is reported alongside.
"""
import csv
import io
import json
import math
import pickle
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import warnings
warnings.filterwarnings('ignore')

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / 'external_data'
OUT = HERE / 'multi'
MODELS = [('linear', 0), ('poly3', 0), ('knn5', 0), ('krr_rbf', 0), ('rf200', 0),
          ('gbrt', 0), ('mlp8', 0), ('mlp16x16', 0), ('mlp32x32', 0)]
WIND_EDGES = np.round(np.arange(4.5, 14.5 + 1e-9, 0.5), 2)
WIND_BANDS = {'TRAIN': (4.5, 6.5), 'LAWCAL': (6.5, 8.5), 'A': (8.5, 10.5), 'B': (11.5, 14.5)}
PV_EDGES = np.arange(150.0, 1100.0 + 1e-9, 50.0)
PV_BANDS = {'TRAIN': (150, 350), 'LAWCAL': (350, 550), 'A': (550, 800), 'B': (900, 1100)}

DATASETS = {
    'kelmarsh': dict(title='Kelmarsh wind 2020', kind='wind', outputs=['Power (kW)', 'Rotor speed (rpm)'],
                     caps=[2050.0, 15.0], q_th=[3.0, 1.0], x='Wind speed (m/s)'),
    'penmanshiel': dict(title='Penmanshiel wind 2017 (WT11-15)', kind='wind',
                        outputs=['Power (kW)', 'Rotor speed (rpm)'], caps=[2050.0, 17.1], q_th=[3.0, 1.0],
                        x='Wind speed (m/s)'),
    'lahauteborne': dict(title='La Haute Borne wind 2014-15', kind='wind', outputs=['Power (kW)'],
                         caps=[2050.0], q_th=[3.0], x='Wind speed (m/s)'),
    'hilloftowie': dict(title='Hill of Towie wind 2019', kind='wind', outputs=['Power (kW)'],
                        caps=[2300.0], q_th=[3.0], x='Wind speed (m/s)'),
    'pv9068': dict(title='PVDAQ 9068 solar 2018-19 (DC current)', kind='pv', outputs=['DC current (A)'],
                   caps=None, x_cap=823.0, q_th=[1.0], x='Irradiance (W/m$^2$)'),
    'pv2107': dict(title='PVDAQ 2107 solar (inverter AC power)', kind='pv', outputs=['AC power (kW)'],
                   caps=[27.6], q_th=[1.0], x='Irradiance (W/m$^2$)', sensitivity_caps=[30.0]),
    'capillary': dict(title='Capillary waves (b200), ctr12', kind='capillary', outputs=None, caps=None,
                      q_th=None, x='Drive power (mW)'),
}


# ======================================================================= unit object
class GUnit:
    """Bins of the input play the role of trials; outputs are logged."""

    def __init__(self, x, Y, edges, bands, half, min_records=6):
        self.u = np.log(np.asarray(x, float)); self.y = np.log(np.asarray(Y, float))
        self.bands, self.half = bands, half
        b = np.digitize(x, edges) - 1
        self.names, self.TP, self.TM, self.lp, self.members, self.left = [], {}, {}, {}, {}, {}
        for k in range(len(edges) - 1):
            m = b == k
            if m.sum() >= min_records:
                n = float(edges[k] + half)
                self.names.append(n); self.members[n] = m; self.left[n] = float(edges[k])
                self.lp[n] = float(self.u[m].mean()); self.TP[n] = float(np.exp(self.lp[n]))
                self.TM[n] = self.y[m].mean(0)

    def band(self, key):
        lo, hi = self.bands[key]
        return [n for n in self.names if lo <= self.left[n] < hi]

    def windows(self, bins):
        m = np.zeros(len(self.u), bool)
        for n in bins:
            m |= self.members[n]
        return self.u[m], self.y[m]

    def slopes(self, bins):
        x = np.array([self.lp[n] for n in bins]); Y = np.array([self.TM[n] for n in bins])
        return np.array([np.polyfit(x, Y[:, j], 1)[0] for j in range(Y.shape[1])])


# ======================================================================= builders
def read_cubico(zpath, prefix, months=range(1, 13)):
    """Cubico (Kelmarsh/Penmanshiel) 10-min turbine CSVs, filters as build_wind.py."""
    z = zipfile.ZipFile(zpath)
    cols = ('Date and time', 'Wind speed (m/s)', 'Power (kW)', 'Rotor speed (RPM)')
    out = []
    for name in sorted(n for n in z.namelist() if n.startswith(prefix)):
        t = int(name.split('_')[3])
        f = io.TextIOWrapper(z.open(name), encoding='utf-8', errors='replace', newline='')
        header = None
        for line in f:
            if line.startswith('# Date and time'):
                header = next(csv.reader([line[2:]])); break
        idx = [header.index(c) for c in cols]
        n_kept = 0
        for row in csv.reader(f):
            try:
                stamp = row[idx[0]]; U, P, W = (float(row[i]) for i in idx[1:])
            except (ValueError, IndexError):
                continue
            if not (np.isfinite(U) and np.isfinite(P) and np.isfinite(W)) or P <= 10 or W <= 0 or U <= 0:
                continue
            m = int(stamp[5:7])
            if m in months:
                out.append((t, m, U, P, W)); n_kept += 1
        print('  %s turbine %d: %d records' % (prefix, t, n_kept), flush=True)
    return np.array(out)


def build(name):
    OUT.mkdir(exist_ok=True)
    if name == 'penmanshiel':
        A = read_cubico(RAW / 'penmanshiel' / 'Penmanshiel_SCADA_2017_WT11-15_3115.zip', 'Turbine_Data_Penmanshiel_')
        np.savez_compressed(OUT / 'penmanshiel_records.npz', unit_a=A[:, 0], unit_b=A[:, 1], x=A[:, 2],
                            Y=A[:, 3:5])
    elif name == 'lahauteborne':
        z = zipfile.ZipFile(RAW / 'lahauteborne' / 'la_haute_borne.zip')
        f = io.TextIOWrapper(z.open('la-haute-borne-data-2014-2015.csv'), encoding='utf-8', newline='')
        r = csv.DictReader(f)
        tid = {}; rows = []
        for row in r:
            try:
                U, P = float(row['Ws_avg']), float(row['P_avg'])
            except (ValueError, TypeError):
                continue
            if not (np.isfinite(U) and np.isfinite(P)) or P <= 10 or U <= 0:
                continue
            t = tid.setdefault(row['Wind_turbine_name'], len(tid) + 1)
            ym = int(row['Date_time'][:4]) * 100 + int(row['Date_time'][5:7])
            rows.append((t, ym, U, P))
        A = np.array(rows)
        np.savez_compressed(OUT / 'lahauteborne_records.npz', unit_a=A[:, 0], unit_b=A[:, 1], x=A[:, 2],
                            Y=A[:, 3:4], turbines=np.array(list(tid)))
    elif name == 'hilloftowie':
        z = zipfile.ZipFile(RAW / 'hilloftowie' / '2019.zip')
        names = z.namelist()
        rows = []
        for m in range(1, 13):
            fw = [n for n in names if n.split('/')[-1].startswith('tblSCTurbine_2019_%02d' % m)]
            fp = [n for n in names if n.split('/')[-1].startswith('tblSCTurGrid_2019_%02d' % m)]
            if not fw or not fp:
                print('  month %d missing' % m); continue
            ws = {}
            for row in csv.DictReader(io.TextIOWrapper(z.open(fw[0]), encoding='utf-8', newline='')):
                ws[(row['TimeStamp'], row['StationId'])] = row['wtc_AcWindSp_mean']
            k = 0
            for row in csv.DictReader(io.TextIOWrapper(z.open(fp[0]), encoding='utf-8', newline='')):
                key = (row['TimeStamp'], row['StationId'])
                try:
                    U, P = float(ws[key]), float(row['wtc_ActPower_mean'])
                except (KeyError, ValueError, TypeError):
                    continue
                if not (np.isfinite(U) and np.isfinite(P)) or P <= 10 or U <= 0:
                    continue
                rows.append((int(row['StationId']) - 2304509, m, U, P)); k += 1
            print('  month %d: %d records' % (m, k), flush=True)
        A = np.array(rows)
        np.savez_compressed(OUT / 'hilloftowie_records.npz', unit_a=A[:, 0], unit_b=A[:, 1], x=A[:, 2],
                            Y=A[:, 3:4])
    elif name == 'pv2107':
        G = {}
        with open(RAW / 'pvdaq_2107' / '2107_irradiance_data.csv', newline='') as f:
            r = csv.reader(f); next(r)
            for row in r:
                try:
                    g = float(row[1])
                except (ValueError, IndexError):
                    continue
                if 150.0 <= g < 1100.0:
                    G[row[0]] = g
        rows = []
        with open(RAW / 'pvdaq_2107' / '2107_electrical_data.csv', newline='') as f:
            r = csv.reader(f); hdr = next(r)
            cols = [(k, int(h[4:6])) for k, h in enumerate(hdr) if '_ac_power_' in h]
            for row in r:
                g = G.get(row[0])
                if g is None:
                    continue
                ym = int(row[0][:4]) * 100 + int(row[0][5:7])
                for k, inv in cols:
                    try:
                        p = float(row[k])
                    except (ValueError, IndexError):
                        continue
                    if np.isfinite(p) and p > 0.1:
                        rows.append((inv, ym, g, p))
        A = np.array(rows)
        print('  pv2107 records %d, inverters %d' % (len(A), len(set(A[:, 0]))))
        np.savez_compressed(OUT / 'pv2107_records.npz', unit_a=A[:, 0], unit_b=A[:, 1], x=A[:, 2], Y=A[:, 3:4])
    print('built', name)


# ======================================================================= units
def load_units(name):
    """{unit name: GUnit-like} for the dataset."""
    meta = DATASETS[name]
    if name == 'kelmarsh':
        R = np.load(HERE / 'wind' / '2020' / 'records.npz')
        ua, ub, x, Y = R['turbine'], R['month'], R['U'], np.stack([R['P'], R['omega']], 1)
    elif name == 'pv9068':
        import pv_audit as PA
        return {n: c for n, y, comb, c in PA.units() if y in (2018, 2019)}
    else:
        R = np.load(OUT / ('%s_records.npz' % name))
        ua, ub, x, Y = R['unit_a'], R['unit_b'], R['x'], R['Y']
    edges, bands, half = (WIND_EDGES, WIND_BANDS, 0.25) if meta['kind'] == 'wind' else (PV_EDGES, PV_BANDS, 25.0)
    out = {}
    for a in sorted(set(ua.tolist())):
        for b in sorted(set(ub[ua == a].tolist())):
            m = (ua == a) & (ub == b)
            if m.sum() < 48:
                continue
            c = GUnit(x[m], Y[m], edges, bands, half)
            if len(c.band('TRAIN')) == 4 and len(c.band('LAWCAL')) == 4:
                out['%s-%d-%d' % (name, int(a), int(b))] = c
    return out


def law_parts(name, c, caps=None):
    """q, top, kappa, centre function delta -> (line, capped), delta*."""
    from perband_audit import hop_kappas, e1_hops
    meta = DATASETS[name]
    q = c.slopes(c.band('LAWCAL')); top = max(c.band('LAWCAL'), key=lambda n: c.TP[n])
    kappa = hop_kappas(c, e1_hops(c))[0]
    caps = meta['caps'] if caps is None else caps
    if caps is not None:
        lc = np.log(caps)
        ds = [(lc[j] - c.TM[top][j]) / q[j] if q[j] > 0 else np.inf for j in range(len(lc))]
        dstar = max(0.0, max(ds))
        cap_fn = lambda d: np.minimum(c.TM[top] + q * d, lc)
    elif meta.get('x_cap'):
        dstar = max(0.0, math.log(meta['x_cap']) - c.lp[top])
        cap_fn = lambda d: c.TM[top] + q * min(d, dstar)
    else:
        dstar = np.inf
        cap_fn = lambda d: c.TM[top] + q * d
    return q, top, kappa, (lambda d: c.TM[top] + q * d), cap_fn, dstar


def cert(fx, fa, ya, yx, cx, ca, beta, fT=None, yT=None, cT=None):
    D = float(np.linalg.norm(fx - fa - (cx - ca))); b = float(np.linalg.norm(fa - ya))
    Dc = float(np.linalg.norm(fx - ya - (cx - ca)))
    e = float(np.linalg.norm(fx - yx)); z = float(np.linalg.norm(yx - ya - (cx - ca)))
    S = max(D - b - beta, 0.0) if np.isfinite(beta) else 0.0
    Sc = max(Dc - beta, 0.0) if np.isfinite(beta) else 0.0
    prem = bool(z <= beta + 1e-10)
    assert Sc + 1e-9 >= S, 'ceiling form must dominate the three-term form'
    out = dict(D=D, b=b, beta=beta, S=S, Sc=Sc, e=e, zeta=z, prem=prem)
    if fT is not None:
        # POST HOC: anchor at the top TRAIN bin, where the surrogate was fitted.
        # Law allowance = beta + ||r_T||, r_T = the law's measured residual at that anchor.
        rT = float(np.linalg.norm(yT - cT))
        DT = float(np.linalg.norm(fx - fT - (cx - cT))); bT = float(np.linalg.norm(fT - yT))
        ST = max(DT - bT - beta - rT, 0.0) if np.isfinite(beta) else 0.0
        assert ST <= Sc + 1e-9
        out.update(DT=DT, bT=bT, rT=rT, betaT=beta + rT, ST=ST)
    if prem:
        assert S <= e + 1e-8 and Sc <= e + 1e-8 and out.get('ST', 0) <= e + 1e-8,             'bound failed where its premise held'
    return out


def _unit_job(args):
    name, uname, c, caps_variants = args
    from threadpoolctl import threadpool_limits
    from multimodel_audit import fit_model
    rows = []
    parts = {k: law_parts(name, c, caps) for k, caps in caps_variants.items()}
    q, top, kappa, line, capped, dstar = parts['primary']
    tests = {s: c.band(s) for s in ('A', 'B')}
    if not any(len(v) >= 2 for v in tests.values()):
        return rows
    U, Yt = c.windows(c.band('TRAIN'))
    m = Yt.shape[1]
    with threadpool_limits(limits=1):
        for kind, seed in MODELS:
            g = fit_model(kind, seed, U, Yt)
            pr = lambda u: np.asarray(g(np.array([[u]]))).reshape(-1)[:m]
            fa, ya = pr(c.lp[top]), c.TM[top]
            aT = max(c.band('TRAIN'), key=lambda n: c.TP[n]); dT = c.lp[aT] - c.lp[top]
            fT, yT = pr(c.lp[aT]), c.TM[aT]
            for scen, bins in tests.items():
                if len(bins) < 2:
                    continue
                for t in bins:
                    d = c.lp[t] - c.lp[top]; fx = pr(c.lp[t]); yx = c.TM[t]
                    base = dict(unit=uname, scen=scen, bin=t, model=kind, delta=d)
                    for var, (q_, top_, k_, line_, capped_, ds_) in parts.items():
                        rules = [('L', line_, 2 * k_ * d)] if var == 'primary' else []
                        rules += [('K-L', capped_, 2 * k_ * d), ('K-S1', capped_, 2 * k_ * min(d, ds_))]
                        for rule, cf, beta in rules:
                            tag = rule if var == 'primary' else '%s@%s' % (rule, var)
                            rows.append(dict(base, rule=tag, **cert(fx, fa, ya, yx, cf(d), cf(0), beta,
                                                                    fT, yT, cf(dT))))
    return rows


def run(name):
    t0 = time.time()
    if name == 'capillary':
        rows = run_capillary()
    else:
        units = load_units(name)
        meta = DATASETS[name]
        variants = {'primary': None}
        for cap in meta.get('sensitivity_caps', []):
            variants['cap%g' % cap] = [cap]
        jobs = [(name, u, c, variants) for u, c in units.items()]
        rows = []
        with ProcessPoolExecutor(max_workers=16) as ex:
            for rr in ex.map(_unit_job, jobs, chunksize=2):
                rows += rr
    pickle.dump(rows, open(OUT / ('%s_rows.pkl' % name), 'wb'))
    print('%s: %d units, %d row-rule pairs (%.0fs)' % (name, len({r['unit'] for r in rows}), len(rows),
                                                      time.time() - t0), flush=True)


def _cap_job(args):
    ds, kind, seed = args
    from threadpoolctl import threadpool_limits
    import multimodel_audit as M
    from perband_audit import hop_kappas, p_hops
    c = M.Corpus(ds)
    rows = []
    with threadpool_limits(limits=1):
        U, Yt = c.windows(c.train)
        g = M.fit_model(kind, seed, U, Yt)
        for tag, hi in M.CONFIGS:
            lawcal = [n for n in c.names if M.LAWCAL_LO <= c.TP[n] <= hi]
            q = c.slopes(lawcal); top = max(lawcal, key=lambda n: c.TP[n])
            kappa = hop_kappas(c, p_hops(c, lawcal))[0]
            fa = g(np.array([[c.lp[top]]]))[0]
            aT = max(c.train, key=lambda n: c.TP[n]); dT = c.lp[aT] - c.lp[top]
            fT = g(np.array([[c.lp[aT]]]))[0]
            for t in [n for n in c.names if c.TP[n] > hi]:
                d = c.lp[t] - c.lp[top]
                fx = g(np.array([[c.lp[t]]]))[0]
                base = dict(unit='%s|%s' % (ds, tag), dataset=ds, scen=tag, bin=t, model='%s#%d' % (kind, seed),
                            delta=d)
                for rule in ('L', 'K-L', 'K-S1'):        # no published cap: all three coincide
                    rows.append(dict(base, rule=rule, **cert(fx, fa, c.TM[top], c.TM[t], c.TM[top] + q * d,
                                                             c.TM[top], 2 * kappa * d,
                                                             fT, c.TM[aT], c.TM[top] + q * dT)))
    return rows


def run_capillary():
    import multimodel_audit as M
    rows = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for rr in ex.map(_cap_job, [(ds, k, s) for ds in M.DATASETS for k, s in M.MODELS]):
            rows += rr
    return rows


# ======================================================================= report
def summarise(rs):
    S = np.array([r['S'] for r in rs]); Sc = np.array([r['Sc'] for r in rs]); e = np.array([r['e'] for r in rs])
    p = np.array([r['prem'] for r in rs]); v = S <= e + 1e-9
    bins = {(r['unit'], r['bin']): r['prem'] for r in rs}
    return dict(rows=len(rs), units=len({r['unit'] for r in rs}), bins=len(bins),
                premise=float(np.mean(list(bins.values()))), valid=float(v.mean()),
                valid_c=float(np.mean(Sc <= e + 1e-9)), fail_prem=int((p & ~v).sum()),
                Se=float(np.median(S / e)), Se_c=float(np.median(Sc / e)),
                silent=float(np.mean(S <= 0.01)),
                med_D=float(np.median([r['D'] for r in rs])), med_b=float(np.median([r['b'] for r in rs])),
                med_beta=float(np.median([r['beta'] for r in rs if np.isfinite(r['beta'])])),
                med_S=float(np.median(S)), med_e=float(np.median(e)),
                Se_T=float(np.median([r['ST'] / r['e'] for r in rs])) if 'ST' in rs[0] else None,
                valid_T=float(np.mean([r['ST'] <= r['e'] + 1e-9 for r in rs])) if 'ST' in rs[0] else None,
                med_bT=float(np.median([r['bT'] for r in rs])) if 'bT' in rs[0] else None,
                med_rT=float(np.median([r['rT'] for r in rs])) if 'rT' in rs[0] else None)


def report():
    res, lines = {}, []
    hdr = '%-16s %-12s %6s %5s %8s %7s %6s %7s %7s %7s %7s' % ('scenario', 'rule', 'rows', 'units', 'premise',
                                                         'valid', 'fail|p', 'S/e', 'Sc/e', 'ST/e', 'silent')
    for name, meta in DATASETS.items():
        f = OUT / ('%s_rows.pkl' % name)
        if not f.exists():
            continue
        R = pickle.load(open(f, 'rb'))
        if name == 'capillary':
            R_show = [r for r in R if r['dataset'] == 'ctr12']
        else:
            R_show = R
        lines += ['', '%s  [%s]' % (meta['title'].upper(), name), hdr, '-' * len(hdr)]
        for scen in sorted({r['scen'] for r in R_show}):
            for rule in sorted({r['rule'] for r in R_show}, key=lambda x: (len(x), x)):
                rs = [r for r in R_show if r['scen'] == scen and r['rule'] == rule]
                if not rs:
                    continue
                s = summarise(rs)
                res['%s|%s|%s' % (name, scen, rule)] = s
                lines.append('%-16s %-12s %6d %5d %8.3f %7.3f %6d %7.2f %7.2f %7.2f %7.3f' % (
                    scen, rule, s['rows'], s['units'], s['premise'], s['valid'], s['fail_prem'], s['Se'],
                    s['Se_c'], s['Se_T'] if s['Se_T'] is not None else float('nan'), s['silent']))
        if name == 'capillary':
            for scen in sorted({r['scen'] for r in R}):
                s = summarise([r for r in R if r['scen'] == scen and r['rule'] == 'L'])
                res['capillary_all7|%s|L' % scen] = s
    lines.append('\nS = three-term total bound (D - b - beta); Sc = ceiling form. fail|p must be 0.')
    txt = '\n'.join(lines)
    (OUT / 'report.txt').write_text(txt); (OUT / 'results.json').write_text(json.dumps(res, indent=1))
    print(txt)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    cmd = sys.argv[1]
    if cmd == 'build':
        for n in sys.argv[2:]:
            build(n)
    elif cmd == 'run':
        for n in sys.argv[2:]:
            run(n)
    else:
        report()
