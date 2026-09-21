"""Derive the per-trial radial spatial-PSD spectrum into spec_k.npz.

A second observable on the SAME 20 recordings as spec.npz. It is a different
prediction target, not additional experimental evidence.

Needs the HDF5 (see dataset/README.md); the committed spec_k.npz means the
external audit runs without it.
"""
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ROOT = Path(os.environ.get('SASES_DATASET') or REPO / 'dataset')
H5 = ROOT / 'b200_50MB.h5'
NBANDS = 10

if not H5.exists():
    raise SystemExit(
        "Dataset not found at {}. Download the deposit from "
        "https://doi.org/10.6075/J0WW7HVJ and place b200_50MB.h5 there, or set "
        "SASES_DATASET to its directory. spec_k.npz is committed, so the "
        "external audit runs without this step.".format(H5))

sys.path.insert(0, str(ROOT))
from decode import Package

p = Package(str(H5))
names, powers, rows = [], [], []
edges = None
for n in p.by_power():
    P = p.power(n)
    if not np.isfinite(P) or P <= 0:
        continue
    field = np.asarray(p.psd_spatial(n), dtype=np.float64)   # (nkx, nky) half-plane
    nx, ny = field.shape
    # Radial |k| in grid units, folding the half-plane about its kx origin.
    kx = np.fft.fftfreq(nx, d=1.0 / nx)[:, None]
    ky = np.arange(ny)[None, :]
    kr = np.sqrt(kx ** 2 + ky ** 2)
    if edges is None:
        edges = np.geomspace(1.0, min(nx // 2, ny - 1), NBANDS + 1)
    band = np.empty(NBANDS)
    for b in range(NBANDS):
        m = (kr >= edges[b]) & (kr < edges[b + 1]) & np.isfinite(field) & (field > 0)
        if not m.any():
            raise SystemExit('Empty radial band %d for trial %s' % (b, n))
        band[b] = np.log(field[m].mean())
    names.append(n)
    powers.append(P)
    rows.append(band)
    print('%-9s P=%6.1f mW  bands=%d  ln PSD_k %.2f .. %.2f'
          % (n, P, NBANDS, band.min(), band.max()), flush=True)

centres = np.sqrt(edges[:-1] * edges[1:])
np.savez(HERE / 'spec_k.npz', Y=np.array(rows), P=np.array(powers),
         trial=np.array(names), kcent=centres, edges=edges)
print('\nWrote spec_k.npz', np.array(rows).shape)
