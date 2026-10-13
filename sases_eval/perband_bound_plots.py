"""Reference-style figures for the per-output allowance test (PERBAND_PROTOCOL.md):
the measured curves, the law's extrapolation, the current sphere allowance and the
per-output allowance around it, and every point that leaves the per-output bound.

  capillary  ceilings 146 and 192 mW, rules C and P
  wind       Kelmarsh 2019 (the unseen confirmation year), rules C, P, E1, E3
  solar      one output, so per-output = sphere: see law_bound/fig_solar.png

Ratio panels use the exact premises: sphere ||zeta||/beta, per-output
max_j |zeta_j|/beta_j; above 1 the law is not bounded. Writes perband/fig_bound_*.png.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

import allowance_audit as AA
import law_bound_plots as LB                       # style, palette, slope line, ratio panel, PSDs
import wind_audit as W
from perband_audit import hop_kappas, p_hops, e1_hops, e3_betas, fleet_vectors

HERE = Path(__file__).resolve().parent
OUT = HERE / 'perband'
for _y in (2018, 2019):
    AA.YEARS[_y] = HERE / 'wind' / str(_y)
SPHC = '#2a78d6'


def ratios(curves_rows, rule, form):
    out = []
    for x, rows in curves_rows:
        if form == 'sph':
            r = [np.linalg.norm(z) / b[rule][0] if np.isfinite(b[rule][0]) else np.nan for z, b in rows]
        else:
            r = [np.max(np.abs(z) / b[rule][1]) if np.all(np.isfinite(b[rule][1])) else np.nan for z, b in rows]
        out.append((x, np.array(r)))
    return out


# ======================================================================= capillary
def capillary(pdf):
    f, psd = LB.capillary_psd()
    c = LB.CapUnit()
    LN = np.log(1e-12)
    res = {}
    for cfg, ceil in (('146', 146.0), ('192', 192.0)):
        lawcal = [n for n in c.names if 106 <= c.TP[n] <= ceil]
        top = max(lawcal, key=lambda n: c.TP[n]); q = c.slopes(lawcal)
        kP, kPv = hop_kappas(c, p_hops(c, lawcal))
        rows = []
        for t in [n for n in c.names if c.TP[n] > ceil]:
            d = c.lp[t] - c.lp[top]; centre = c.TM[top] + q * d
            rows.append(dict(trial=t, P=c.TP[t], centre=centre, z=c.TM[t] - centre,
                             C=(float(np.linalg.norm(q - .5)) * d, np.abs(q - .5) * d),
                             Pr=(2 * kP * d, 2 * kPv * d)))
        res[cfg] = dict(top=top, rows=rows)

    order = sorted(psd, key=lambda n: c.TP[n])
    hl = ['_9_1', '_12_1', '_21_1', '_33_1', '_42_1', '_48_1', '_54_1', '_57_1', '_60_1', '_63_1', '_66_1']
    col = dict(zip(hl, LB.palette(len(hl))))
    fig = plt.figure(figsize=(12, 11))
    gs = fig.add_gridspec(3, 4, height_ratios=[1.25, 1.0, 0.9], hspace=0.42, wspace=0.34)
    ax = fig.add_subplot(gs[0, :2])
    for n in order:
        ax.loglog(f[1:], psd[n][1:], color=col.get(n, LB.GREY), lw=1.3 if n in col else 0.9,
                  zorder=3 if n in col else 2)
    LB.slope_line(ax, 900, 1.1e4, 3e-12, -17 / 6, '−17/6')
    ax.set_xlim(50, 3e4); ax.set_xlabel('Frequency (Hz)'); ax.set_ylabel('PSD (m$^2$/Hz)')
    ax.legend([Line2D([], [], color=col.get(n, LB.GREY), lw=2) for n in order], ['%g' % c.TP[n] for n in order],
              title='Power input (mW)', ncol=3, fontsize=7, title_fontsize=8, loc='lower left',
              handlelength=1.6, columnspacing=1.0)
    ax.set_title('(a) Measured centre-pixel spectra, all 20 trials', fontsize=9)

    # (b) each test trial from the 146 mW ceiling, rule P: sphere band vs per-band steps.
    R = res['146']
    sub = gs[0, 2:].subgridspec(2, 2, hspace=0.35, wspace=0.08)
    edges = np.geomspace(500, 20000, 13)
    n_out = 0
    for k, r in enumerate(R['rows']):
        a = fig.add_subplot(sub[k // 2, k % 2])
        n = r['trial']; cc = col.get(n, '#555555')
        a.loglog(f[1:], psd[n][1:], color=cc, lw=1.0)
        cen = np.exp(r['centre'] + LN); lab = np.exp(c.TM[n] + LN)
        bs, bv = r['Pr']
        a.fill_between(c.fc, cen * np.exp(-bs), cen * np.exp(bs), color=SPHC, alpha=0.13, lw=0)
        for sgn in (1, -1):
            a.stairs(cen * np.exp(sgn * bv), edges, color=cc, lw=1.3, baseline=None)
        a.loglog(c.fc, cen, 'k--', lw=0.8)
        out = np.abs(r['z']) > bv
        n_out += int(out.any())
        a.plot(c.fc[~out], lab[~out], 'o', ms=3.5, color=cc, mec='k', mew=0.4)
        a.plot(c.fc[out], lab[out], 'X', ms=7, color=LB.OUTC, mec='k', mew=0.5, zorder=5)
        a.set_xlim(450, 2.2e4); a.set_ylim(1e-18, 1e-7)
        a.text(0.04, 0.06, '%g mW: %d of 12 bands outside' % (r['P'], out.sum()), transform=a.transAxes,
               fontsize=7.2)
        if k % 2:
            a.set_yticklabels([])
        if k < 2:
            a.set_xticklabels([])
        else:
            a.set_xlabel('Frequency (Hz)', fontsize=8)
        if k == 0:
            a.set_title('(b) Ceiling %g mW, rule P: sphere band (blue) vs per-band steps' % c.TP[R['top']],
                        fontsize=8.5, loc='left')
    # (c) ratio panels: rules C and P, sphere vs per-band, both ceilings.
    for k, (rule, key) in enumerate((('C', 'C'), ('P', 'Pr'))):
        for j, form in enumerate(('sph', 'pb')):
            a = fig.add_subplot(gs[1, 2 * k + j])
            curves = []
            for cfg, mk in (('146', 'o'), ('192', 's')):
                rr = res[cfg]['rows']
                x = np.array([r['P'] for r in rr])
                y = np.array([np.linalg.norm(r['z']) / r[key][0] if form == 'sph'
                              else np.max(np.abs(r['z']) / r[key][1]) for r in rr])
                a.plot(x, np.clip(y, 1e-3, 1e3), mk + '-', color='k', ms=4, lw=0.6, zorder=4)
                curves += [(np.array([xx]), np.array([yy])) for xx, yy in zip(x, y)]
            LB.ratio_panel(a, curves, 'rule %s, %s' % (rule, 'sphere' if form == 'sph' else 'per-band'),
                           xlabel='Test drive power (mW)', noun='points')
            a.set_ylim(1e-2, 1e2)
            a.set_xticks([200, 250, 300, 350]); a.set_xticklabels(['200', '250', '300', '350'])
            a.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            if k == 0 and j == 0:
                a.set_ylabel('law error / allowance\n(> 1: not bounded)')
                a.legend([Line2D([], [], ls='', marker='o', color='k'), Line2D([], [], ls='', marker='s', color='k')],
                         ['ceiling 146 mW', 'ceiling 192 mW'], fontsize=7, loc='upper left')
    # (d) per band, 350 mW test: what must be covered vs each allowance.
    for k, cfg in enumerate(('146', '192')):
        a = fig.add_subplot(gs[2, 2 * k:2 * k + 2])
        r = res[cfg]['rows'][-1]
        z = np.abs(r['z']); x = np.arange(12)
        a.bar(x, z, color='#bdbdbd', width=0.7)
        a.stairs(r['Pr'][1], np.arange(13) - 0.5, color='#7b3f8f', lw=1.8, baseline=None)
        a.stairs(r['C'][1], np.arange(13) - 0.5, color='#7b3f8f', lw=1.1, ls='--', baseline=None)
        a.axhline(r['Pr'][0], color=SPHC, lw=1.8); a.axhline(r['C'][0], color=SPHC, lw=1.1, ls='--')
        for jj in np.where(z > r['Pr'][1])[0]:
            a.plot(jj, z[jj] + 0.3, 'X', color=LB.OUTC, mec='k', mew=0.4, ms=7)
        a.set_xticks(x); a.set_xticklabels(['%.1f' % (v / 1e3) for v in c.fc], fontsize=7)
        a.set_xlabel('Band centre (kHz)'); a.set_ylabel('ln units' if k == 0 else '')
        a.set_title('(d) Ceiling %s mW → 350 mW: |ζ_j| per band (grey) vs allowances' % cfg, fontsize=8.5)
        if k == 1:
            a.legend([Patch(color='#bdbdbd'), Line2D([], [], color=SPHC, lw=1.8), Line2D([], [], color=SPHC, ls='--'),
                      Line2D([], [], color='#7b3f8f', lw=1.8), Line2D([], [], color='#7b3f8f', ls='--'),
                      Line2D([], [], ls='', marker='X', color=LB.OUTC, mec='k')],
                     ['|ζ_j| law error', 'sphere P', 'sphere C', 'per-band P', 'per-band C', 'outside per-band P'],
                     fontsize=7, ncol=2, loc='upper left')
    fig.suptitle('Capillary waves: sphere vs per-band allowance', fontsize=11, y=0.93)
    fig.savefig(OUT / 'fig_bound_capillary.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


# ============================================================================ wind
def wind(pdf, year=2019):
    units = AA.units_of(year)
    pool = {}
    for y in range(2016, year):
        pool.update(fleet_vectors(y))
    data, e3c = {}, {}
    for u, (t, m, c) in units.items():
        q, top = AA.ceiling_line(c)
        kP, kPv = hop_kappas(c, p_hops(c, c.band('LAWCAL')))
        kE, kEv = hop_kappas(c, e1_hops(c))
        rows = []
        for n in c.names:
            d = c.lp[n] - c.lp[top]
            if d <= 0:
                continue
            if n not in e3c:
                e3c[n] = e3_betas(pool, n)
            centre = c.TM[top] + q * d
            rows.append(dict(bin=n, U=c.TP[n], centre=centre, z=c.TM[n] - centre,
                             b={'C': (float(np.linalg.norm(q - W.Q_TH)) * d, np.abs(q - W.Q_TH) * d),
                                'P': (2 * kP * d, 2 * kPv * d), 'E1': (2 * kE * d, 2 * kEv * d),
                                'E3': e3c[n]}))
        data[u] = (c, q, top, rows)
    test = lambda x: ((x >= 8.5) & (x < 10.5)) | ((x >= 11.5) & (x < 14.5))
    hl = [u for u in ('T1-01', 'T2-03', 'T3-05', 'T4-07', 'T5-09', 'T6-11') if u in data]
    col = dict(zip(hl, LB.palette(len(hl))))

    fig = plt.figure(figsize=(12, 12))
    gs = fig.add_gridspec(3, 4, height_ratios=[1.3, 0.85, 0.85], hspace=0.45, wspace=0.34)
    for j, (name, ylab, a_th) in enumerate((('power', 'Power (kW)', 3), ('rotor speed', 'Rotor speed (rpm)', 1))):
        ax = fig.add_subplot(gs[0, 2 * j:2 * j + 2])
        for u, (c, q, top, rr) in data.items():
            if u not in col:
                ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names], color=LB.GREY, lw=0.8)
        for u in hl:
            c, q, top, rr = data[u]; cc = col[u]
            ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names], color=cc, lw=1.4)
            x = np.array([r['U'] for r in rr]); cen = np.exp(np.array([r['centre'][j] for r in rr]))
            bs = np.array([r['b']['P'][0] for r in rr]); bv = np.array([r['b']['P'][1][j] for r in rr])
            ax.loglog(np.r_[c.TP[top], x], np.r_[np.exp(c.TM[top][j]), cen], ls='--', color=cc, lw=1)
            ax.fill_between(x, cen * np.exp(-bs), cen * np.exp(bs), color=SPHC, alpha=0.06, lw=0)
            ax.loglog(x, cen * np.exp(bv), color=cc, lw=0.9, ls='-.'); ax.loglog(x, cen * np.exp(-bv), color=cc, lw=0.9, ls='-.')
            lab = np.exp(np.array([c.TM[r['bin']][j] for r in rr]))
            out = np.abs(np.array([r['z'][j] for r in rr])) > bv
            ax.plot(x[out], lab[out], 'X', ms=6, color=LB.OUTC, mec='k', mew=0.4, zorder=5)
        y0 = 1.25 * np.median([np.exp(data[u][0].TM[data[u][0].names[0]][j]) for u in hl]) * (5 / 4.75) ** a_th
        LB.slope_line(ax, 5.0, 9.5, y0, a_th, str(a_th))
        for lo, hi, lab in ((6.5, 8.5, 'law cal.'), (8.5, 10.5, 'A'), (11.5, 14.5, 'B')):
            ax.axvspan(lo, hi, color='#f2f2f2', zorder=0)
            ax.text(np.sqrt(lo * hi), 0.97, lab, transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=7.5)
        ax.set_xlabel('Wind speed (m/s)'); ax.set_ylabel(ylab)
        ax.set_xticks([5, 7, 10, 14]); ax.set_xticklabels(['5', '7', '10', '14'])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_title('(%s) Wind %s, %d; rule P' % ('ab'[j], name, year), fontsize=9)
        if j == 0:
            ax.legend([Line2D([], [], color=col[u], lw=2) for u in hl] +
                      [Line2D([], [], color=LB.GREY, lw=2), Line2D([], [], color='k', ls='--'),
                       Patch(color=SPHC, alpha=0.15), Line2D([], [], color='k', ls='-.'),
                       Line2D([], [], ls='', marker='X', color=LB.OUTC, mec='k', ms=6)],
                      hl + ['other units', 'law extrapolation', 'sphere allowance', 'per-output allowance',
                            'outside per-output'], title='Turbine-month', fontsize=6.8, title_fontsize=7.5,
                      loc='lower right', ncol=2)
    curves = [(np.array([r['U'] for r in rr]), [(r['z'], r['b']) for r in rr]) for (_, _, _, rr) in data.values()]
    for i, form in enumerate(('sph', 'pb')):
        for k, rule in enumerate(('C', 'P', 'E1', 'E3')):
            a = fig.add_subplot(gs[1 + i, k])
            LB.ratio_panel(a, ratios(curves, rule, form), '%s, %s' % (rule, 'sphere' if form == 'sph' else 'per-output'),
                           test, 'Wind speed (m/s)' if i == 1 else '')
            for lo, hi in ((8.5, 10.5), (11.5, 14.5)):
                a.axvspan(lo, hi, color='#f2f2f2', zorder=0)
            a.set_xticks([9, 11, 14]); a.set_xticklabels(['9', '11', '14'])
            a.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            if k == 0:
                a.set_ylabel('%s\nlaw error / allowance' % ('SPHERE' if form == 'sph' else 'PER-OUTPUT'))
    fig.suptitle('Wind turbines, Kelmarsh %d (unseen year): sphere vs per-output allowance' % year, fontsize=11, y=0.93)
    fig.savefig(OUT / 'fig_bound_wind.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    with PdfPages(OUT / 'perband_bound_figures.pdf') as pdf:
        capillary(pdf); wind(pdf)
    print('-> perband/fig_bound_capillary.png, fig_bound_wind.png, perband_bound_figures.pdf')
