#!/usr/bin/env python3
"""Decoder for the b200-semantic-v1 package.  (reader v1.1)

v1.1 changes -- reader only, the .h5 payload is untouched and its checksums
are unchanged:
  * wave()/field() no longer resample the whole trial before slicing, and
    expand the spectrum in time-chunks. Peak memory for wave(t, 0, 4096) drops
    from ~4.7-7.2 GB to ~0.8 GB.
  * wave()/field() return float32 by default; pass dtype=np.float64 for the
    old behaviour. The quantisation step is far larger than float32 epsilon,
    so this discards nothing real.
  * wave_chunks() streams a trial in blocks, for reductions over long windows.
  * by_power() now really does put the quiescent trial first.
  * a warning is emitted before any allocation over ~1 GB.


    z(t, x, y) = a(t) + s(x, y) + w(t, x, y)

  a    piston / k=0 mode, full 115.2 kHz rate
  s    static topography, 200x200
  w    wave field, stored band-limited to |kx|,|ky| < K and time-decimated by D,
       upsampled back to the 200x200 / 115.2 kHz grid on read

Usage
-----
    from decode import Package
    p = Package('b200_50MB.h5')
    p.trials()                      # list trial names
    p.info('_66_1')                 # what fidelity this trial was stored at
    z  = p.field('_66_1', 0, 512)   # (512,200,200) reconstructed surface height
    c  = p.centre('_66_1')          # centre-pixel series, full rate, ~exact
    a  = p.piston('_66_1')          # a(t), full rate

`centre()` is the input to the source paper's bispectrum / bicoherence / NRB
analysis and is stored at full rate and near-exact precision. `field()` is an
approximation: see p.info() for the wavelength and frequency limits that apply.
"""
import lzma
import warnings
import numpy as np, h5py
from scipy.signal import resample_poly

# Warn before handing back an array larger than this (bytes).
_BIG = 1_000_000_000
# Time-chunk the spectral expansion so the complex128 FFT scratch buffer
# stays near this size (bytes) regardless of how many frames were asked for.
_FFT_SCRATCH = 200_000_000


def _warn_big(nbytes, what):
    if nbytes > _BIG:
        warnings.warn(
            "%s will allocate %.2f GB. This is fine if you have the RAM; if not, "
            "use a shorter window or stream it with p.wave_chunks(). Proceeding."
            % (what, nbytes / 1e9), ResourceWarning, stacklevel=3)

def _unq(ds):
    a = ds.attrs
    B = np.frombuffer(lzma.decompress(ds[:].tobytes()), dtype=np.dtype(a['dt']))
    return (B.reshape(tuple(a['shape'])).astype(np.float64) + a['lo']) * a['q']

def _expand(small, H, W, dtype=np.float32, out=None):
    """(T,N,N) -> (T,H,W) by zero-padding the spatial spectrum.

    Identical arithmetic to v1.0, but evaluated in time-chunks so the
    complex128 scratch buffer stays bounded no matter how large T is.
    """
    T, N, _ = small.shape
    K = N // 2
    if out is None:
        out = np.empty((T, H, W), dtype)
    step = max(1, int(_FFT_SCRATCH // (H * W * 16)))
    scale = (H * W) / float(N * N)
    for i in range(0, T, step):
        j = min(i + step, T)
        S = np.fft.fft2(small[i:j].astype(np.float64), axes=(1, 2))
        F = np.zeros((j - i, H, W), complex)
        F[:, :K, :K] = S[:, :K, :K]; F[:, :K, -K:] = S[:, :K, -K:]
        F[:, -K:, :K] = S[:, -K:, :K]; F[:, -K:, -K:] = S[:, -K:, -K:]
        out[i:j] = (np.fft.ifft2(F, axes=(1, 2)).real * scale).astype(dtype, copy=False)
        del S, F
    return out


def _resample_window(x, D, o0, o1):
    """resample_poly(x, D, 1, axis=0)[o0:o1] without building the whole thing.

    Upsampling is local, so only a neighbourhood of the requested output
    window is needed. The margin is many times the polyphase filter's
    half-length, which makes the edge transient negligible.
    """
    if D <= 1:
        return x[o0:o1]
    # resample_poly's polyphase filter spans ~10*max(up,down) samples in the
    # UPSAMPLED domain, i.e. ~10 input samples here. 64 is a generous margin.
    margin = 64
    i0 = max(0, o0 // D - margin)
    i1 = min(x.shape[0], -(-o1 // D) + margin)
    y = resample_poly(x[i0:i1], D, 1, axis=0)
    s = o0 - i0 * D
    return y[s:s + (o1 - o0)]

class Package:
    def __init__(self, path):
        self.h = h5py.File(path, 'r'); self.fs = float(self.h.attrs['fs'])
    def trials(self):
        return sorted(self.h.keys(), key=lambda k: int(k.split('_')[1]))
    def info(self, name):
        a = self.h[name].attrs
        return dict(frames=int(a['T']), K=int(a['K']), D=int(a['D']),
                    min_wavelength_um=312.1 / int(a['K']),
                    max_frequency_kHz=self.fs / 2 / int(a['D']) / 1e3,
                    quant_rel=float(a['rel']), coherent_energy_kept=float(a['coh_kept']))
    def piston(self, name):  return _unq(self.h[name]['a_q'])
    def centre(self, name):  return _unq(self.h[name]['ctr_q'])
    def static(self, name):
        d = self.h[name]['s_q']
        return np.frombuffer(lzma.decompress(d[:].tobytes()),
                             dtype=np.float16).reshape(tuple(d.attrs['shape'])).astype(np.float64)
    def _w_small(self, name):
        """The stored, still-decimated wave block. Small: tens of MB at most."""
        g = self.h[name]; a = g.attrs
        B = np.frombuffer(lzma.decompress(g['w_q'][:].tobytes()), dtype=np.dtype(a['dt']))
        return (B.reshape(tuple(a['wshape'])).astype(np.float64) + a['lo']) * a['q']

    def wave(self, name, t0=0, t1=None, dtype=np.float32):
        """Wave field w(t,x,y) in microns, (t1-t0, 200, 200).

        Band-limited and time-decimated per trial -- see info(name) for the
        wavelength and frequency limits that actually apply.

        dtype defaults to float32. The stored quantisation step is orders of
        magnitude coarser than float32 epsilon, so float64 buys nothing but
        memory; pass dtype=np.float64 if you need it for interoperability.
        """
        g = self.h[name]; a = g.attrs
        T, D = int(a['T']), int(a['D'])
        H, W = int(a['H']), int(a['W'])
        t1 = T if t1 is None else min(t1, T)
        t0 = max(0, t0)
        if t1 <= t0:
            return np.empty((0, H, W), dtype)
        _warn_big((t1 - t0) * H * W * np.dtype(dtype).itemsize,
                  "wave(%r, %d, %d)" % (name, t0, t1))
        x = _resample_window(self._w_small(name), D, t0, min(t1, T))
        return _expand(x, H, W, dtype)

    def wave_chunks(self, name, t0=0, t1=None, chunk=512, dtype=np.float32):
        """Yield (i0, i1, w) blocks of the wave field.

        Use this for reductions over long windows -- means, variances, spectra --
        instead of materialising the whole array:

            ss = n = 0
            for i0, i1, w in p.wave_chunks('_66_1', 0, 4096):
                ss += float((w.astype(np.float64) ** 2).sum()); n += w.size
            rms = (ss / n) ** 0.5
        """
        g = self.h[name]; a = g.attrs
        T, D = int(a['T']), int(a['D'])
        H, W = int(a['H']), int(a['W'])
        t1 = T if t1 is None else min(t1, T)
        t0 = max(0, t0)
        small = self._w_small(name)
        for i in range(t0, t1, chunk):
            j = min(i + chunk, t1)
            yield i, j, _expand(_resample_window(small, D, i, j), H, W, dtype)

    def field(self, name, t0=0, t1=None, dtype=np.float32):
        """Reconstructed surface height z = a(t) + s(x,y) + w(t,x,y), microns."""
        T = int(self.h[name].attrs['T']); t1 = T if t1 is None else min(t1, T)
        t0 = max(0, t0)
        z = self.wave(name, t0, t1, dtype)
        z += self.static(name)[None].astype(dtype, copy=False)
        z += self.piston(name)[t0:t1, None, None].astype(dtype, copy=False)
        return z
    def frames(self, name):
        """Frame index. Stored delta-coded; older packages store it raw."""
        m = self.h[name]['meta']
        if 'frames_d' in m:
            d = m['frames_d']
            return np.cumsum(d[:].astype(np.int64)) + int(d.attrs['first'])
        return m['frames'][:]

    def time(self, name):
        """Sample times, seconds. Derived as frames/fs where the package says so
        -- the stored original agreed to one float32 ULP (attrs['t_max_dev_s'])."""
        m = self.h[name]['meta']
        if 't' in m:
            return m['t'][:]
        return (self.frames(name).astype(np.float64) / self.fs).astype(np.float32)

    def xy(self, name):
        """(x, y) coordinate vectors in microns."""
        m = self.h[name]['meta']
        return m['x'][:], m['y'][:]

    # -- experiment parameters -------------------------------------------
    def params(self, name):
        """Experimental parameters for a trial, from the deposit's own params
        file. Empty if add_params.py was never run on this package."""
        a = self.h[name].attrs
        keys = ('experiment', 'P_mW', 'f_MHz', 'Vpp', 'Ipp_mA', 'vib_cm_s',
                'generator', 'volume_ul', 'magnification')
        return {k: (a[k].item() if hasattr(a[k], 'item') else a[k])
                for k in keys if k in a}

    def power(self, name):
        """Drive power in mW. nan for the quiescent noise-floor trial."""
        return float(self.h[name].attrs.get('P_mW', float('nan')))

    def by_power(self):
        """Trial names sorted by drive power, quiescent first."""
        return sorted(self.trials(),
                      key=lambda n: (-np.inf if np.isnan(self.power(n)) else self.power(n)))

    # -- stored spectra (computed on the FULL 315 GB, not on this copy) ----
    def w_std(self, name):
        """Std of the wave field in microns, measured during reduction on the
        |k|<48 field BEFORE this copy's per-trial band-limiting. Use this, not
        wave().std(), for amplitude-vs-power: it is not biased by how coarsely a
        given trial happens to be stored here."""
        return float(self.h[name].attrs['w_std'])

    def psd_temporal(self, name):
        """(f, P) temporal PSD of the wave field.

        Computed during reduction from a central 4096-frame block (~36 ms) of the
        |k|<48 field, Hanning-windowed, averaged over pixels. So it is NOT
        limited by this trial's stored K/D -- but it is a central block, not the
        full run, and it excludes |k|>=48 (the microscope's own resolution
        limit)."""
        P = self.h[name]['psd_t'][:]
        return np.fft.rfftfreq(2 * (len(P) - 1), 1.0 / self.fs), P

    def psd_spatial(self, name):
        """Spatial PSD of the wave field, same central-block provenance as
        psd_temporal (|k| grid in cycles per 312.1 um box)."""
        return self.h[name]['psd_k'][:]

    def summary(self):
        """One row per trial: what it is and what fidelity it was stored at."""
        rows = []
        for n in self.by_power():
            i = self.info(n); p = self.power(n)
            rows.append(dict(trial=n, P_mW=p, frames=i['frames'],
                             min_wavelength_um=i['min_wavelength_um'],
                             max_frequency_kHz=i['max_frequency_kHz'],
                             coherent_energy_kept=i['coherent_energy_kept']))
        return rows

    def print_summary(self):
        hdr = (f"{'trial':9s} {'P (mW)':>7s} {'frames':>7s} {'lam_min (um)':>13s} "
               f"{'f_max (kHz)':>12s} {'coh. kept':>10s}")
        print(hdr); print('-' * len(hdr))
        for r in self.summary():
            pw = ' quiesc' if np.isnan(r['P_mW']) else f"{r['P_mW']:7.1f}"
            print(f"{r['trial']:9s} {pw} {r['frames']:7d} {r['min_wavelength_um']:13.1f} "
                  f"{r['max_frequency_kHz']:12.1f} {r['coherent_energy_kept']*100:9.1f}%")

if __name__ == '__main__':
    import sys
    Package(sys.argv[1] if len(sys.argv) > 1 else 'b200_50MB.h5').print_summary()
