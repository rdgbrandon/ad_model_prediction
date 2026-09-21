"""Build the per-window log-spectrum dataset from the centre-pixel series.

Unit of analysis: a WINDOW of the centre-pixel time series (grouped by trial).
Target y in R^B: natural log of band-averaged temporal PSD, B log-spaced bands
over 500 Hz - 20 kHz (the band the source paper's bicoherence analysis uses).
Input x: ln(drive power / 1 mW).
"""
import os, sys, numpy as np
from pathlib import Path
from scipy.signal import welch
REPO = Path(__file__).resolve().parents[1]
# The 50 MB HDF5 is not redistributed here; see dataset/README.md for the DOI.
# Point SASES_DATASET at the unpacked deposit, or drop b200_50MB.h5 in dataset/.
ROOT = Path(os.environ.get('SASES_DATASET') or REPO / 'dataset')
H5 = ROOT / 'b200_50MB.h5'
if not H5.exists():
    raise SystemExit(
        "Dataset not found at {}. Download the deposit from "
        "https://doi.org/10.6075/J0WW7HVJ and place b200_50MB.h5 there, "
        "or set SASES_DATASET to its directory. The derived spectra in "
        "sases_eval/spec.npz let every audit run without this step.".format(H5))
sys.path.insert(0, str(ROOT))
from decode import Package

WIN, STRIDE, NPERSEG = 8192, 4096, 2048
FLO, FHI, NBANDS = 500.0, 20000.0, 12

p = Package(str(H5))
fs = p.fs
edges = np.geomspace(FLO, FHI, NBANDS + 1)
fcent = np.sqrt(edges[:-1] * edges[1:])

rows_y, rows_P, rows_trial, rows_wi = [], [], [], []
srms = {}
for n in p.by_power():
    P = p.power(n)
    srms[n] = float(np.std(p.static(n)))
    if not np.isfinite(P) or P <= 0:
        continue
    c = p.centre(n).astype(np.float64)
    c = c - c.mean()
    nw = 0
    for i0 in range(0, len(c) - WIN + 1, STRIDE):
        seg = c[i0:i0 + WIN]
        f, Pxx = welch(seg, fs=fs, nperseg=NPERSEG, noverlap=NPERSEG // 2,
                       window='hann', detrend='linear')
        y = np.empty(NBANDS)
        for b in range(NBANDS):
            m = (f >= edges[b]) & (f < edges[b + 1])
            y[b] = np.log(Pxx[m].mean())
        rows_y.append(y); rows_P.append(P); rows_trial.append(n); rows_wi.append(nw)
        nw += 1
    print(f"{n:9s} P={P:6.1f} mW  windows={nw}  s_rms={srms[n]:7.3f}", flush=True)

Y = np.array(rows_y); Pw = np.array(rows_P)
trial = np.array(rows_trial); wi = np.array(rows_wi)
np.savez(Path(__file__).resolve().parent / 'spec.npz',
         Y=Y, P=Pw, trial=trial, wi=wi, fcent=fcent, edges=edges,
         srms_names=np.array(list(srms.keys())), srms_vals=np.array(list(srms.values())))
print("\nY", Y.shape, " trials", len(set(trial)))
