"""Build the seven window-level target representations of MULTIMODEL_PROTOCOL.md.

Every representation uses a series stored at the full frame rate (centre pixel or
piston), so no representation's bandwidth depends on drive power. Unit of
analysis stays a WINDOW of one trial's series; splits are grouped by trial.
"""
import sys
from pathlib import Path
import numpy as np
from scipy.signal import welch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'b200_capillary_wave_50MB_v1.1'
sys.path.insert(0, str(ROOT))
from decode import Package

OUT = HERE / 'datasets'

# name -> (series, window, stride, nperseg, flo, fhi, nbands, spacing, average, shape_only)
SPECS = {
    'ctr12':    ('centre', 8192, 4096, 2048,  500., 20000., 12, 'log', 'mean',   False),
    'ctr24w':   ('centre', 8192, 4096, 2048,  200., 48000., 24, 'log', 'mean',   False),
    'ctrlin8':  ('centre', 8192, 4096, 2048,  500., 20000.,  8, 'lin', 'mean',   False),
    'ctrshort': ('centre', 2048, 1024,  512, 1000., 20000., 12, 'log', 'mean',   False),
    'ctrmed':   ('centre', 8192, 4096, 2048,  500., 20000., 12, 'log', 'median', False),
    'ctrshape': ('centre', 8192, 4096, 2048,  500., 20000., 12, 'log', 'mean',   True),
    'pist12':   ('piston', 8192, 4096, 2048,  500., 20000., 12, 'log', 'mean',   False),
}


def build(p, name):
    series, win, stride, nperseg, flo, fhi, nb, spacing, average, shape_only = SPECS[name]
    edges = np.geomspace(flo, fhi, nb + 1) if spacing == 'log' else np.linspace(flo, fhi, nb + 1)
    fcent = np.sqrt(edges[:-1] * edges[1:]) if spacing == 'log' else .5 * (edges[:-1] + edges[1:])
    rows_y, rows_P, rows_trial, rows_wi = [], [], [], []
    for n in p.by_power():
        P = p.power(n)
        if not np.isfinite(P) or P <= 0:
            continue
        c = (p.centre(n) if series == 'centre' else p.piston(n)).astype(np.float64)
        c = c - c.mean()
        nw = 0
        for i0 in range(0, len(c) - win + 1, stride):
            f, Pxx = welch(c[i0:i0 + win], fs=p.fs, nperseg=nperseg, noverlap=nperseg // 2,
                           window='hann', detrend='linear', average=average)
            y = np.empty(nb)
            for b in range(nb):
                m = (f >= edges[b]) & (f < edges[b + 1])
                if not m.any():
                    raise ValueError('Empty band %d in %s: resolution too coarse' % (b, name))
                y[b] = np.log(Pxx[m].mean())
            if shape_only:
                y = y - y.mean()
            rows_y.append(y); rows_P.append(P); rows_trial.append(n); rows_wi.append(nw)
            nw += 1
    Y = np.array(rows_y)
    OUT.mkdir(exist_ok=True)
    np.savez(OUT / (name + '.npz'), Y=Y, P=np.array(rows_P), trial=np.array(rows_trial),
             wi=np.array(rows_wi), fcent=fcent, edges=edges)
    print('%-9s Y=%s trials=%d windows/trial=%d' %
          (name, Y.shape, len(set(rows_trial)), rows_wi.count(0) and len(rows_wi) // len(set(rows_trial))),
          flush=True)
    return Y


if __name__ == '__main__':
    p = Package(str(ROOT / 'b200_50MB.h5'))
    for name in SPECS:
        build(p, name)
    # ctr12 must reproduce the audited spec.npz bit for bit in Y, P and trial.
    old = np.load(HERE / 'spec.npz', allow_pickle=False)
    new = np.load(OUT / 'ctr12.npz', allow_pickle=False)
    same = {k: bool(np.array_equal(old[k], new[k])) for k in ('Y', 'P', 'trial', 'wi')}
    print('ctr12 identical to spec.npz:', same, flush=True)
    assert all(same.values()), 'ctr12 must reproduce the audited dataset exactly'
