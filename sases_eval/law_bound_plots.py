"""Reference-style figures (log-log curves coloured by drive level) for each dataset,
with the law's extrapolation, the certificate's allowance around it, and every
place a measured curve leaves that allowance.

  capillary  PSD vs frequency per drive power; law per band, ln S_b(P) linear in ln P
  wind       power and rotor speed vs wind speed per turbine-month (Kelmarsh 2017)
  solar      DC current vs irradiance per combiner-month (PVDAQ 9068)

Allowance rules, as in the audits: C = ||q_cal - q_th|| delta (the rule behind the
capillary headline numbers), P = 2 kappa' delta (paper Eq. 5), E1 = 2 kappa'_long
delta, E3 = fleet conformal (wind only). The premise is ||zeta|| <= beta; the bands
drawn on single outputs are its per-coordinate projection (|zeta_j| <= beta), which
is necessary but, for multi-output targets, not sufficient. The ratio panels use the
exact criterion. Writes law_bound/*.png and law_bound/law_bound.pdf. Read-only on data.
"""
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

import allowance_audit as AA
import pv_audit as PA
import wind_audit as W
from wind_paper_rule import kappa_fit

HERE = Path(__file__).resolve().parent
OUT = HERE / 'law_bound'
# Capillary package (decode.py + b200_50MB.h5): $SASES_DATASET, else dataset/, else the original folder.
PKG = Path(os.environ.get('SASES_DATASET') or next(
    (q for q in (HERE.parent / 'dataset', HERE.parent / 'b200_capillary_wave_50MB_v1.1') if (q / 'decode.py').exists()),
    HERE.parent / 'dataset'))

PAL = ['#e0201b', '#f39c12', '#9cbc1f', '#0b7a3a', '#62c4b8', '#2a3b8f', '#7b3f8f']
GREY, SLOPE, OUTC = '#d9d9d9', '#1f77b4', '#d0021b'
plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['DejaVu Serif'], 'font.size': 8.5,
    'axes.linewidth': 0.8, 'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.top': True, 'ytick.right': True, 'xtick.minor.visible': True,
    'ytick.minor.visible': True, 'legend.frameon': False, 'savefig.dpi': 220,
    'mathtext.fontset': 'dejavuserif'})


def palette(n):
    idx = np.linspace(0, len(PAL) - 1, n).round().astype(int)
    return [PAL[i] for i in idx]


def slope_line(ax, x0, x1, y0, a, label):
    """A reference power law y ~ x^a from (x0, y0) to x1, labelled like the reference."""
    xs = np.array([x0, x1])
    ax.plot(xs, y0 * (xs / x0) ** a, color=SLOPE, lw=1.6)
    ax.text(np.sqrt(x0 * x1) * 1.15, y0 * (np.sqrt(x1 / x0)) ** a * 1.9, r'$\alpha$=%s' % label,
            fontsize=9)


def ratio_panel(ax, curves, title, test_mask_fn=None, xlabel='', xlog=True, noun='curves'):
    """curves: list of (x array, ||zeta||/beta array). Line at 1 = the bound."""
    n_out = 0
    for x, r in curves:
        r = np.where(np.isfinite(r), np.clip(r, 1e-3, 1e3), np.nan)
        ax.plot(x, r, color='#b0b0b0', lw=0.6, alpha=0.6)
        over = r > 1
        if over.any():
            ax.plot(np.where(over, x, np.nan), np.where(over, r, np.nan), color=OUTC, lw=0.9, alpha=0.8)
            sel = over if test_mask_fn is None else over & test_mask_fn(x)
            sel &= np.isfinite(r)
            n_out += bool(sel.any())
    ax.axhline(1, color='k', lw=1.1)
    ax.set_yscale('log'); ax.set_xscale('log' if xlog else 'linear')
    ax.set_ylim(1e-3, 1.5e3)
    ax.set_title('%s:  %d of %d %s exceed' % (title, n_out, len(curves), noun), fontsize=8.5)
    ax.set_xlabel(xlabel)
    return n_out


# ======================================================================= capillary
def capillary_psd():
    """Geometric-mean Welch PSD per trial, same windows and parameters as build_dataset.py."""
    cache = OUT / 'capillary_psd.npz'
    if cache.exists():
        d = np.load(cache)
        return d['f'], {k: d[k] for k in d.files if k != 'f'}
    from scipy.signal import welch
    sys.path.insert(0, str(PKG))
    from decode import Package
    p = Package(str(PKG / 'b200_50MB.h5'))
    out = {}
    for n in p.trials():
        P = p.power(n)
        if not np.isfinite(P) or P <= 0:
            continue
        c = p.centre(n).astype(np.float64); c -= c.mean()
        L = []
        for i0 in range(0, len(c) - 8192 + 1, 4096):
            f, Pxx = welch(c[i0:i0 + 8192], fs=p.fs, nperseg=2048, noverlap=1024,
                           window='hann', detrend='linear')
            L.append(np.log(Pxx))
        out[n] = np.exp(np.mean(L, 0)) * 1e-12          # um^2/Hz -> m^2/Hz
    np.savez(cache, f=f, **out)
    return f, out


class CapUnit:
    """The capillary corpus with the interface wind_paper_rule.kappa_fit expects."""

    def __init__(self):
        d = np.load(HERE / 'spec.npz')
        self.Y, self.P, self.trial, self.fc, self.edges = d['Y'], d['P'], d['trial'], d['fcent'], d['edges']
        self.names = list(dict.fromkeys(self.trial))
        self.TP = {n: float(self.P[self.trial == n][0]) for n in self.names}
        self.TM = {n: self.Y[self.trial == n].mean(0) for n in self.names}
        self.lp = {n: np.log(self.TP[n]) for n in self.names}

    def slopes(self, bins):
        x = np.array([self.lp[n] for n in bins]); Y = np.array([self.TM[n] for n in bins])
        return np.array([np.polyfit(x, Y[:, j], 1)[0] for j in range(Y.shape[1])])


def capillary(pdf):
    f, psd = capillary_psd()
    c = CapUnit()
    LN = np.log(1e-12)                                       # band labels to m^2/Hz
    configs = {'canonical_146': 146.0, 'canonical_192': 192.0}
    res = {}
    for cfg, ceil in configs.items():
        lawcal = [n for n in c.names if 106 <= c.TP[n] <= ceil]
        top = max(lawcal, key=lambda n: c.TP[n])
        q = c.slopes(lawcal)
        kC, kP = float(np.linalg.norm(q - 0.5)), 2 * kappa_fit(c, lawcal)
        tests = [n for n in c.names if c.TP[n] > ceil]
        rows = []
        for t in tests:
            d = c.lp[t] - c.lp[top]
            centre = c.TM[top] + q * d
            z = c.TM[t] - centre
            rows.append(dict(trial=t, P=c.TP[t], delta=d, centre=centre, zeta=z,
                             beta_C=kC * d, beta_P=kP * d))
        res[cfg] = dict(top=top, q=q, rows=rows, lawcal=lawcal)

    order = sorted(psd, key=lambda n: c.TP[n])
    hl = ['_9_1', '_12_1', '_21_1', '_33_1', '_42_1', '_48_1', '_54_1', '_57_1', '_60_1', '_63_1', '_66_1']
    col = dict(zip(hl, palette(len(hl))))
    fig = plt.figure(figsize=(11, 8.2))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.25, 1], hspace=0.32, wspace=0.32)
    ax = fig.add_subplot(gs[0, :2])
    for n in order:
        if n not in col:
            ax.loglog(f[1:], psd[n][1:], color=GREY, lw=0.9)
    for n in order:
        if n in col:
            ax.loglog(f[1:], psd[n][1:], color=col[n], lw=1.3)
    slope_line(ax, 900, 1.1e4, 3e-12, -17 / 6, '−17/6')
    ax.set_xlim(50, 3e4)
    ax.set_xlabel('Frequency (Hz)'); ax.set_ylabel('PSD (m$^2$/Hz)')
    handles = [Line2D([], [], color=col.get(n, GREY), lw=2) for n in order]
    ax.legend(handles, ['%g' % c.TP[n] for n in order], title='Power input (mW)', ncol=3,
              fontsize=7, title_fontsize=8, loc='lower left', handlelength=1.6, columnspacing=1.0)
    ax.set_title('(a) Measured centre-pixel spectra, all 20 trials', fontsize=9)

    # (b) The law and its allowance at each test trial, ceiling 146 mW (4 tests).
    R = res['canonical_146']
    axb = fig.add_subplot(gs[0, 2:])
    for r in R['rows']:
        n = r['trial']; cc = col.get(n, '#555555')
        axb.loglog(f[1:], psd[n][1:], color=cc, lw=1.0, alpha=0.9)
        lab = np.exp(c.TM[n] + LN); cen = np.exp(r['centre'] + LN)
        axb.loglog(c.fc, cen, ls='--', color=cc, lw=1.0)
        for rule, ls, a in (('P', '-', 0.16),):
            b = r['beta_' + rule]
            axb.fill_between(c.fc, cen * np.exp(-b), cen * np.exp(b), color=cc, alpha=a, lw=0)
            axb.loglog(c.fc, cen * np.exp(b), color=cc, lw=1.4); axb.loglog(c.fc, cen * np.exp(-b), color=cc, lw=1.4)
        out = np.abs(r['zeta']) > r['beta_P']
        axb.plot(c.fc[~out], lab[~out], 'o', ms=4, color=cc, mec='k', mew=0.4)
        axb.plot(c.fc[out], lab[out], 'X', ms=7, color=OUTC, mec='k', mew=0.5)
    axb.set_xlim(400, 2.5e4)
    axb.set_xlabel('Frequency (Hz)'); axb.set_ylabel('PSD (m$^2$/Hz)')
    axb.set_title('(b) Law from %s mW ceiling, extrapolated to %s mW' % (
        '%g' % c.TP[R['top']], ', '.join('%g' % r['P'] for r in R['rows'])), fontsize=9)
    axb.legend([Line2D([], [], color='k', lw=1), Line2D([], [], color='k', ls='--', lw=1),
                Patch(color='k', alpha=0.16), Line2D([], [], ls='', marker='o', color='grey', mec='k'),
                Line2D([], [], ls='', marker='X', color=OUTC, mec='k', ms=7)],
               ['measured spectrum', 'law prediction (band centres)', 'allowance, rule P (paper Eq. 5)',
                'band label inside', 'band label OUTSIDE the allowance'], fontsize=7, loc='lower left')

    # (c) exact premise ratio ||zeta|| / beta per test trial, both ceilings, rules C and P.
    for k, rule in enumerate(('C', 'P')):
        a = fig.add_subplot(gs[1, k])
        curves = []
        for cfg, mk in (('canonical_146', 'o'), ('canonical_192', 's')):
            rr = res[cfg]['rows']
            x = np.array([r['P'] for r in rr]); y = np.array([np.linalg.norm(r['zeta']) / r['beta_' + rule] for r in rr])
            a.plot(x, y, mk + '-', color='k', ms=4, lw=0.6, zorder=4)
            curves += [(np.array([xx]), np.array([yy])) for xx, yy in zip(x, y)]
        ratio_panel(a, curves, '(c) rule %s' % rule, xlabel='Test drive power (mW)', noun='test points')
        a.set_ylim(1e-2, 1e2)
        a.set_xticks([200, 250, 300, 350]); a.set_xticklabels(['200', '250', '300', '350'])
        a.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if k == 0:
            a.set_ylabel('‖ζ‖ / β   (> 1: law not bounded)')
            a.legend([Line2D([], [], ls='', marker='o', color='k'), Line2D([], [], ls='', marker='s', color='k')],
                     ['ceiling 146 mW', 'ceiling 192 mW'], fontsize=7, loc='upper left')
    # (d) per-band size of the law residual vs the allowance, ceiling 146.
    a = fig.add_subplot(gs[1, 2:])
    for r in R['rows']:
        cc = col.get(r['trial'], '#555555')
        a.semilogx(c.fc, np.abs(r['zeta']), 'o-', color=cc, lw=1, ms=3, label='%g mW' % r['P'])
        a.axhline(r['beta_P'], color=cc, lw=0.8, ls='--')
        a.axhline(r['beta_C'], color=cc, lw=0.8, ls=':')
    a.set_xlabel('Band centre frequency (Hz)'); a.set_ylabel('|ζ| per band (ln units)')
    a.set_title('(d) Law residual per band (solid) vs allowance β (dashed P, dotted C)', fontsize=8.5)
    a.legend(fontsize=7, ncol=2, loc='upper left')
    fig.suptitle('Capillary waves: where the law is bounded', fontsize=11, y=0.94)
    fig.savefig(OUT / 'fig_capillary.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    summ = {cfg: [dict(P=r['P'], zeta=float(np.linalg.norm(r['zeta'])), beta_C=r['beta_C'], beta_P=r['beta_P'],
                       bands_outside_P=int((np.abs(r['zeta']) > r['beta_P']).sum()),
                       bands_outside_C=int((np.abs(r['zeta']) > r['beta_C']).sum())) for r in v['rows']]
            for cfg, v in res.items()}
    return summ


# ============================================================================ wind
def wind(pdf):
    units = AA.units_of(2017)
    z16 = AA.zetas(2016)
    rows = {}
    for u, (t, m, c) in units.items():
        q, top = AA.ceiling_line(c)
        kC = float(np.linalg.norm(q - W.Q_TH)); kP = 2 * kappa_fit(c, c.band('LAWCAL'))
        kE = 2 * AA.e1_kappa(c)[0]
        rr = []
        for n in c.names:
            d = c.lp[n] - c.lp[top]
            if d <= 0:
                continue
            centre = c.TM[top] + q * d
            pool = np.array([zz[n] for zz in z16.values() if n in zz])
            rr.append(dict(bin=n, U=c.TP[n], delta=d, centre=centre, zeta=c.TM[n] - centre,
                           C=kC * d, P=kP * d, E1=kE * d, E3=AA.conformal_upper(pool)))
        rows[u] = (c, q, top, rr)
    test = lambda x: ((x >= 8.5) & (x < 10.5)) | ((x >= 11.5) & (x < 14.5))
    want = ['T1-01', 'T2-03', 'T3-05', 'T4-07', 'T5-09', 'T6-11']
    hl = [u for u in want if u in rows][:6]
    col = dict(zip(hl, palette(len(hl))))

    fig = plt.figure(figsize=(11, 8.6))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.3, 1], hspace=0.34, wspace=0.34)
    for j, (name, unit, a_th, yl) in enumerate((('power', 'Power (kW)', 3, 'P'),
                                                 ('rotor speed', 'Rotor speed (rpm)', 1, 'ω'))):
        ax = fig.add_subplot(gs[0, 2 * j:2 * j + 2])
        for u, (c, q, top, rr) in rows.items():
            if u not in col:
                ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names], color=GREY, lw=0.8)
        for u in hl:
            c, q, top, rr = rows[u]; cc = col[u]
            ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names], color=cc, lw=1.4)
            x = np.array([r['U'] for r in rr]); cen = np.exp(np.array([r['centre'][j] for r in rr]))
            b = np.array([r['P'] for r in rr])
            ax.loglog(np.r_[c.TP[top], x], np.r_[np.exp(c.TM[top][j]), cen], ls='--', color=cc, lw=1)
            ax.fill_between(x, cen * np.exp(-b), cen * np.exp(b), color=cc, alpha=0.12, lw=0)
            lab = np.exp(np.array([c.TM[r['bin']][j] for r in rr]))
            out = np.abs(np.array([r['zeta'][j] for r in rr])) > b
            ax.plot(x[out], lab[out], 'X', ms=6, color=OUTC, mec='k', mew=0.4, zorder=5)
        x0 = 5.0
        y0 = 1.25 * np.median([np.exp(rows[u][0].TM[rows[u][0].names[0]][j]) for u in hl]) * (x0 / 4.75) ** a_th
        slope_line(ax, x0, 9.5, y0, a_th, str(a_th))
        for lo, hi, lab in ((6.5, 8.5, 'law cal.'), (8.5, 10.5, 'A'), (11.5, 14.5, 'B')):
            ax.axvspan(lo, hi, color='#f2f2f2', zorder=0)
            ax.text(np.sqrt(lo * hi), 0.97, lab, transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=7.5)
        ax.set_xlabel('Wind speed (m/s)'); ax.set_ylabel(unit)
        ax.set_xticks([5, 7, 10, 14]); ax.set_xticklabels(['5', '7', '10', '14'])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_title('(%s) Wind %s, 2017; band = rule P allowance' % ('ab'[j], name), fontsize=8.5)
        if j == 0:
            hs = [Line2D([], [], color=col[u], lw=2) for u in hl] + [Line2D([], [], color=GREY, lw=2),
                  Line2D([], [], color='k', ls='--'), Patch(color='k', alpha=0.12),
                  Line2D([], [], ls='', marker='X', color=OUTC, mec='k', ms=6)]
            ax.legend(hs, hl + ['other units', 'law extrapolation', 'allowance (rule P)', 'outside allowance'],
                      title='Turbine-month', fontsize=6.8, title_fontsize=7.5, loc='lower right', ncol=2)
    counts = {}
    for k, rule in enumerate(('C', 'P', 'E1', 'E3')):
        a = fig.add_subplot(gs[1, k])
        curves = [(np.array([r['U'] for r in rr]),
                   np.array([np.linalg.norm(r['zeta']) / r[rule] if np.isfinite(r[rule]) else np.nan for r in rr]))
                  for (_, _, _, rr) in rows.values()]
        counts[rule] = ratio_panel(a, curves, '(%s) rule %s' % ('cdef'[k], rule), test, 'Wind speed (m/s)')
        for lo, hi in ((8.5, 10.5), (11.5, 14.5)):
            a.axvspan(lo, hi, color='#f2f2f2', zorder=0)
        a.set_xticks([9, 11, 14]); a.set_xticklabels(['9', '11', '14'])
        a.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if k == 0:
            a.set_ylabel('‖ζ‖ / β   (> 1: law not bounded)')
    fig.suptitle('Wind turbines (Kelmarsh 2017): where the law is bounded', fontsize=11, y=0.95)
    fig.savefig(OUT / 'fig_wind.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    return dict(units=len(rows), curves_exceeding_in_test_bands=counts)


# =========================================================================== solar
def solar(pdf):
    rows = {}
    for name, year, comb, c in PA.units():
        q, top = PA.law(c)
        kC = float(np.linalg.norm(q - PA.Q_TH)); kP = 2 * kappa_fit(c, c.band('LAWCAL'))
        kE = 2 * AA.e1_kappa(c)[0]
        rr = []
        for n in c.names:
            d = c.lp[n] - c.lp[top]
            if d <= 0:
                continue
            centre = c.TM[top] + q * d
            rr.append(dict(bin=n, G=c.TP[n], centre=centre, zeta=c.TM[n] - centre, C=kC * d, P=kP * d, E1=kE * d))
        rows[name] = (year, c, q, top, rr)
    test = lambda x: ((x >= 550) & (x < 800)) | ((x >= 900) & (x < 1100))
    hl, seen = [], set()
    for u, (y, c, q, top, rr) in sorted(rows.items()):
        mon, comb = u[5:7], u[8:]
        if y == 2018 and mon not in seen and comb not in {h[8:] for h in hl}                 and max(c.names) >= 1075 and min(c.names) <= 175:
            hl.append(u); seen.add(mon)
    hl = hl[:6]
    col = dict(zip(hl, palette(len(hl))))

    fig = plt.figure(figsize=(11, 8.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.3, 1], hspace=0.34, wspace=0.3)
    ax = fig.add_subplot(gs[0, :])
    for u, (y, c, q, top, rr) in rows.items():
        if y == 2018 and u not in col:
            ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][0]) for n in c.names], color=GREY, lw=0.6)
    for u in hl:
        y, c, q, top, rr = rows[u]; cc = col[u]
        ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][0]) for n in c.names], color=cc, lw=1.4)
        x = np.array([r['G'] for r in rr]); cen = np.exp(np.array([r['centre'][0] for r in rr]))
        b = np.array([r['P'] for r in rr])
        ax.loglog(np.r_[c.TP[top], x], np.r_[np.exp(c.TM[top][0]), cen], ls='--', color=cc, lw=1)
        ax.fill_between(x, cen * np.exp(-b), cen * np.exp(b), color=cc, alpha=0.12, lw=0)
        lab = np.exp(np.array([c.TM[r['bin']][0] for r in rr]))
        out = np.abs(np.array([r['zeta'][0] for r in rr])) > b
        ax.plot(x[out], lab[out], 'X', ms=6, color=OUTC, mec='k', mew=0.4, zorder=5)
    slope_line(ax, 190, 420, 1.35 * np.median([np.exp(rows[u][1].TM[rows[u][1].names[0]][0]) for u in hl]), 1, '1')
    for lo, hi, lab in ((350, 550, 'law cal.'), (550, 800, 'A'), (900, 1100, 'B')):
        ax.axvspan(lo, hi, color='#f2f2f2', zorder=0)
        ax.text(np.sqrt(lo * hi), 0.97, lab, transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=7.5)
    ax.axvline(823, color='k', lw=0.6, ls=':'); ax.text(830, 0.03, 'spec clipping', transform=ax.get_xaxis_transform(), fontsize=7)
    ax.set_xlabel('Plane-of-array irradiance (W/m$^2$)'); ax.set_ylabel('DC current (A)')
    ax.set_xticks([200, 300, 500, 700, 1000]); ax.set_xticklabels(['200', '300', '500', '700', '1000'])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_title('(a) Solar DC current, 2018 combiner-months; bands: rule P around the law', fontsize=9)
    hs = [Line2D([], [], color=col[u], lw=2) for u in hl] + [Line2D([], [], color=GREY, lw=2),
          Line2D([], [], color='k', ls='--'), Patch(color='k', alpha=0.12),
          Line2D([], [], ls='', marker='X', color=OUTC, mec='k', ms=6)]
    ax.legend(hs, hl + ['other 2018 units', 'law extrapolation', 'allowance (rule P)', 'outside allowance'],
              title='Year-month-combiner', fontsize=7, title_fontsize=7.5, loc='upper left', ncol=2)
    counts = {}
    for k, rule in enumerate(('C', 'P', 'E1')):
        a = fig.add_subplot(gs[1, k])
        curves = [(np.array([r['G'] for r in rr]), np.array([abs(r['zeta'][0]) / max(r[rule], 1e-12) for r in rr]))
                  for (_, _, _, _, rr) in rows.values()]
        counts[rule] = ratio_panel(a, curves, '(%s) rule %s' % ('bcd'[k], rule), test, 'Irradiance (W/m$^2$)')
        for lo, hi in ((550, 800), (900, 1100)):
            a.axvspan(lo, hi, color='#f2f2f2', zorder=0)
        a.set_xticks([600, 800, 1000]); a.set_xticklabels(['600', '800', '1000'])
        a.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if k == 0:
            a.set_ylabel('|ζ| / β   (> 1: law not bounded)')
    fig.suptitle('Solar plant (PVDAQ 9068): where the law is bounded', fontsize=11, y=0.95)
    fig.savefig(OUT / 'fig_solar.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)
    return dict(units=len(rows), curves_exceeding_in_test_bands=counts)


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    with PdfPages(OUT / 'law_bound.pdf') as pdf:
        s = dict(capillary=capillary(pdf), wind=wind(pdf), solar=solar(pdf))
    (OUT / 'summary.json').write_text(json.dumps(s, indent=1))
    print(json.dumps({k: v for k, v in s.items() if k != 'capillary'}, indent=1))
    for cfg, rr in s['capillary'].items():
        for r in rr:
            print(cfg, r)
