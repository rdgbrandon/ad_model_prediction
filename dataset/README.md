# Capillary-wave turbulence: a ~50 MB working copy of a 315 GB deposit

This is an **approximate** copy of the surface-height data from

> Orosco, Jeremy; Connacher, William; Friend, James (2023).
> *Data from: Identification of weakly- to strongly-turbulent three-wave processes
> in a micro-scale system.* UC San Diego Library Digital Collections.
> https://doi.org/10.6075/J0WW7HVJ

The original deposit is **320.7 GB** of raw frames. This file is **50.3 MB**, a
**6,382x** reduction. It is not a lossless copy and is not a substitute for the
deposit — it is a copy you can put on a laptop and actually work with.

> **Read `PROVENANCE.md` first.** Short version: the numbers are real
> measurements, lossily compressed. The reduction pipeline, the decoder and this
> documentation were AI-written. There are only **21 trials** — see the sample-size
> note in `PROVENANCE.md` before you fit anything.

Please cite the original authors, not this file. The original is
CC-licensed by UC San Diego; this repackaging changes nothing about that.

---

## Files

| file | what it is |
|---|---|
| `b200_50MB.h5` | the data |
| `decode.py` | the reader (**v1.1**). `Package(path)` and you are done |
| `example_analysis.py` | five worked analyses that run on the file as shipped |
| `README.md` | this |
| `PROVENANCE.md` | what is measured, what is AI-generated, and how many trials there really are |

Requires `numpy`, `h5py`, `scipy` (and `matplotlib` for the example figures).

```bash
python decode.py b200_50MB.h5            # what is in here
python example_analysis.py b200_50MB.h5  # figures into ./figures
```

---

## Quick start

```python
from decode import Package
p = Package('b200_50MB.h5')

p.print_summary()             # every trial, its drive power, its fidelity
p.by_power()                  # trial names ordered by drive power

t = p.time('_66_1')           # seconds
c = p.centre('_66_1')         # centre-pixel height, full 115.2 kHz  <- see below
z = p.field('_66_1', 0, 512)  # (512, 200, 200) reconstructed surface, microns
w = p.wave('_66_1', 0, 512)   # just the wave part, piston and topography removed
p.params('_66_1')             # {'P_mW': 350.0, 'vib_cm_s': 32.0, ...}
```

`wave()` and `field()` return **float32** and cost about 16 MB per 100 frames.
For anything longer than a few thousand frames, stream it instead of
materialising it:

```python
ss = n = 0
for i0, i1, w in p.wave_chunks('_66_1', 0, 20000, chunk=512):
    ss += float((w.astype(np.float64) ** 2).sum()); n += w.size
rms = (ss / n) ** 0.5
```

Pass `dtype=np.float64` if you need it. You almost certainly do not: the stored
quantisation step is orders of magnitude coarser than float32 epsilon.

The surface is stored as a decomposition, and `field()` just adds it back up:

```
z(t,x,y)  =  a(t)  +  s(x,y)  +  w(t,x,y)
             piston   static      the actual waves
                      topography
```

---

## The experiment

A thin film of liquid (40 µl, 3/8" circular Kapton pool) driven at **7.001 MHz**
by a surface-acoustic-wave device, imaged by digital holographic microscopy at
**10x**, **115.2 kfps**, over a **312.1 µm** field of view on a 200x200 grid
(1.5684 µm/pixel). 21 experiments: one quiescent noise-floor measurement and 20
drive powers from 7 to 350 mW. Roughly 2.0 million frames in total.

Two things to know before you use the trial list:

- **`_6_1` is not an experiment.** Its parameter file says
  `NOISE FLOOR MEASUREMENT` — zero drive, zero vibration velocity. It is a direct
  measurement of what the instrument reads when nothing is happening, which makes
  it the reference for what is signal and what is not. Use it as your noise floor.
- **`_9_1` (7 mW) is labelled `STATIC MODE MEASUREMENT`**, not a turbulence run.
  It is ~94% temporally white at the pixel level. It is stored at low fidelity
  here (8.7% of coherent energy) because there is very little coherent field in
  it to store.
- `_42_1` and `_45_1` are both **54 mW**, repeat runs on different days.

---

## What is exact, what is approximate

**This is the part that matters.** Different quantities in this file are held to
very different standards.

| quantity | fidelity |
|---|---|
| `centre(trial)` centre-pixel time series | **full 115.2 kHz, quantised to 1% of the wave std.** Effectively exact. |
| `piston(trial)` = `a(t)`, the frame-mean | **full rate**, same quantisation. This is 75–95% of the total variance. |
| `static(trial)` = `s(x,y)` topography | float16, stored once. Stable to corr 0.997 across a run. |
| `psd_temporal()`, `psd_spatial()` | computed during reduction from a central **4096-frame block (~36 ms)** of the |k|<48 field. **Not** limited by the per-trial cutoffs below — but a central block, not the whole run. |
| `w_std(trial)` | wave amplitude measured on the |k|<48 field **before** this copy's band-limiting. Use this for amplitude-vs-power, not `wave().std()`. |
| `params()`, `time()`, `frames()` | exact (`t` is regenerated as `frames/fs`, agreeing with the stored original to one float32 ULP, 6e-8 s — 0.0007% of a sample period). |
| `wave(trial)` / `field(trial)` the 3-D wave field | **band-limited and time-decimated, per trial.** This is where the compression is. See below. |

### The wave field is band-limited — check `p.info(trial)` before you trust it

Each trial stores `w` only up to a spatial cutoff and a temporal cutoff, chosen
per trial to fit the budget:

```python
p.info('_66_1')
# {'min_wavelength_um': 19.5, 'max_frequency_kHz': 14.4, ...}
```

**Structure finer than `min_wavelength_um`, or faster than `max_frequency_kHz`,
is not in this file.** It was not lost to rounding; it was deliberately not sent.
If your analysis depends on it, go to the original deposit.

Two reasons this costs less than it sounds:

1. The microscope could not resolve below **6.5 µm** anyway (the DHM optical
   limit at 10x). The measured spatial spectrum has a **70x cliff** there.
   Everything above that wavenumber is instrument noise, not waves.
2. At the strong drive powers where there is real signal, the field is
   **low-wavenumber and low-frequency**: at 350 mW, 92% of the wave energy sits
   below |k|=8 cycles/box and 90% of the temporal energy below ~6 kHz of a
   57.6 kHz Nyquist.

### Why the quiescent and 7 mW trials are stored so coarsely

Budget was allocated to maximise **total coherent wave energy** across the whole
deposit, where "coherent" means above the measured per-mode instrument-noise
floor. The quiescent trial is *by definition* pure instrument noise, and the 7 mW
static-mode run is ~94% noise. Spending bits reproducing noise faithfully would
have come straight out of the trials that contain waves. Their `a(t)`,
centre-pixel series, topography and full-data spectra are all still here at full
fidelity — only their spatial `w` is coarse.

---

## The bit you probably actually want

The paper's entire bispectrum / bicoherence / nonlinear-resonance-broadening
analysis runs on the **centre-pixel time series**, not on the 3-D field. All 21
of those series, at the full 115.2 kHz, are about **8 MB** — they were always the
scientifically operative data. They are in here at essentially full precision,
and the paper's bicoherence computed on this copy matches the same quantity
computed on the original 315 GB to **corr > 0.999999**.

```python
c = p.centre('_66_1'); t = p.time('_66_1')
# then the deposit's own capillary_wave_analysis.py:
#   f, B = wav_bicoherence(c - c.mean(), t, p.fs, 500., 20000., Ns=128)
```

`example_analysis.py` will use that official tool if it is importable and fall
back to a self-contained implementation otherwise. **For published numbers, use
the official tool** — it ships with the deposit at the DOI above.

---

## Measured fidelity

Every number below was measured by decoding this file and comparing against the
**original raw frames**, not estimated. `err/w_std` is the reconstruction error
of the wave field relative to that field's own standard deviation; `inband_err`
is the error restricted to the band this trial actually claims to store.

| trial | drive | λ_min (µm) | f_max (kHz) | in-band err | err/w_std | PSD_t err | PSD_k err | kurtosis pkg / raw |
|---|---|---|---|---|---|---|---|---|
| `_9_1` | 7 mW | 52.0 | 1.8 | **0.7276** | 1.152 | 0.9215 | 0.6603 | 4.012 / 5.144 |
| `_12_1` | 12 mW | 19.5 | 1.8 | **0.0168** | 0.243 | 0.0332 | 0.0178 | 6.177 / 6.372 |
| `_15_1` | 16 mW | 39.0 | 1.8 | **0.0061** | 0.288 | 0.0620 | 0.0102 | 4.171 / 4.016 |
| `_18_1` | 18 mW | 19.5 | 1.8 | **0.0207** | 0.263 | 0.0203 | 0.0185 | 4.756 / 4.702 |
| `_21_1` | 22 mW | 19.5 | 1.8 | **0.0136** | 0.267 | 0.0199 | 0.0152 | 3.731 / 3.691 |
| `_24_1` | 24 mW | 19.5 | 1.8 | **0.0101** | 0.250 | 0.0289 | 0.0117 | 3.866 / 3.732 |
| `_27_1` | 26 mW | 19.5 | 1.8 | **0.0148** | 0.227 | 0.0288 | 0.0156 | 3.719 / 3.656 |
| `_30_1` | 28 mW | 19.5 | 1.8 | **0.0102** | 0.220 | 0.0302 | 0.0103 | 5.042 / 4.846 |
| `_33_1` | 36 mW | 9.8 | 1.8 | **0.0267** | 0.219 | 0.0129 | 0.0298 | 5.500 / 5.441 |
| `_36_1` | 41 mW | 13.0 | 3.6 | **0.0033** | 0.161 | 0.0170 | 0.0045 | 5.860 / 5.718 |
| `_39_1` | 46 mW | 13.0 | 3.6 | **0.0058** | 0.166 | 0.0155 | 0.0047 | 3.806 / 3.728 |
| `_42_1` | 54 mW | 13.0 | 3.6 | **0.0208** | 0.215 | 0.0247 | 0.0178 | 4.263 / 4.248 |
| `_45_1` | 54 mW | 9.8 | 3.6 | **0.0120** | 0.177 | 0.0150 | 0.0112 | 3.910 / 3.874 |
| `_48_1` | 106 mW | 9.8 | 3.6 | **0.0227** | 0.203 | 0.0149 | 0.0227 | 3.197 / 3.247 |
| `_51_1` | 125 mW | 13.0 | 7.2 | **0.0083** | 0.175 | 0.0166 | 0.0042 | 3.805 / 3.779 |
| `_54_1` | 146 mW | 13.0 | 7.2 | **0.0576** | 0.285 | 0.0172 | 0.0526 | 3.919 / 3.922 |
| `_57_1` | 192 mW | 9.8 | 7.2 | **0.0591** | 0.278 | 0.0138 | 0.0540 | 3.981 / 3.957 |
| `_60_1` | 250 mW | 13.0 | 14.4 | **0.0530** | 0.297 | 0.0204 | 0.0498 | 3.841 / 3.849 |
| `_63_1` | 300 mW | 19.5 | 14.4 | **0.0938** | 0.381 | 0.0338 | 0.0920 | 3.617 / 3.676 |
| `_66_1` | 350 mW | 19.5 | 14.4 | **0.1837** | 0.476 | 0.0386 | 0.1834 | 3.932 / 3.995 |
| `_6_1` | **quiescent** | 52.0 | 1.8 | **0.3396** | 1.045 | 0.7317 | 0.3068 | 3.641 / 3.626 |

Read the two columns differently: `inband_err` is how well the file delivers what
it says it delivers; `err/w_std` includes the deliberately discarded
sub-resolution band and so is dominated by noise you did not want.

---

## Provenance

Produced from the deposit by a two-stage reduction:
one streaming pass over all 320.7 GB extracting `a(t)`, `s(x,y)`, the centre-pixel
series and `w` band-limited to the 6.5 µm optical cutoff; then a budget-constrained
packer that allocates bandwidth across trials by measured coherent energy.
Quantised residuals are LZMA-compressed. The reduction is reproducible from the
deposit in principle; the reduction scripts are not distributed with this package.
See `PROVENANCE.md`.

---

## Reader v1.1

The `.h5` payload is **byte-identical** to v1.0 and its checksums are unchanged.
Only `decode.py` and `example_analysis.py` changed.

- `wave()` / `field()` no longer resample the whole trial before slicing, and
  expand the spatial spectrum in time-chunks. Peak memory for a 4096-frame
  request drops from **4.7–7.2 GB to about 1.5 GB**, so the example analyses now
  run on a normal laptop. v1.0 was killed by the OOM reaper on an 8 GB machine.
- `wave()` / `field()` return **float32** by default. `dtype=np.float64` restores
  the old type. Verified identical to v1.0 output to float64 rounding —
  worst observed deviation was 4e-15 of one quantisation step.
- New `wave_chunks(name, t0, t1, chunk)` generator for streaming reductions.
- `by_power()` now really does put the quiescent trial first, as its docstring
  always claimed. **If you relied on the old order, this will change your
  results** — in v1.0 the quiescent trial sorted last.
- A `ResourceWarning` is emitted before any allocation over 1 GB. It does not
  stop you.
- `CHECKSUMS.md5` now contains only MD5 lines, so `md5sum -c` runs clean. The
  SHA-256 moved to `CHECKSUMS.sha256`.
