"""Figure for SATURATING_PROTOCOL.md: wind 2020 (confirmation) curves with the break law and
both allowances, ratio panels for every unit, and coverage / S/e for every year.
Writes saturating/fig_saturating.png.
"""
import json
import pickle
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

import allowance_audit as AA
import law_bound_plots as LB
from bound_shape_audit import WIND_CAP, rates
from perband_audit import e1_hops
from saturating_audit import delta_star

HERE = Path(__file__).resolve().parent
OUT = HERE / 'saturating'
RES = json.loads((OUT / 'results.json').read_text())
AA.YEARS[2020] = HERE / 'wind' / '2020'
KL, KS = '#e0201b', '#2a3b8f'
YEAR = 2020


def unit_curves(units):
    out = {}
    for u, (t, m, c) in units.items():
        q, top = AA.ceiling_line(c)
        k = rates(c, c.band('LAWCAL'), q, top, e1_hops(c))['k']
        ds1 = float(np.max(np.maximum(delta_star(c, q, top), 0)))
        ns = [n for n in c.names if c.lp[n] > c.lp[top]]
        d = np.array([c.lp[n] - c.lp[top] for n in ns])
        brk = np.minimum(c.TM[top][None, :] + np.outer(d, q), WIND_CAP[None, :])
        lab = np.array([c.TM[n] for n in ns])
        out[u] = dict(c=c, top=top, x=np.array([c.TP[n] for n in ns]), brk=brk, lab=lab,
                      bKL=2 * k * d, bKS=2 * k * np.minimum(d, ds1))
    return out


def main():
    units = AA.units_of(YEAR)
    U = unit_curves(units)
    hl = [u for u in ('T1-01', 'T2-04', 'T3-07', 'T5-10') if u in U][:4]
    col = dict(zip(hl, LB.palette(len(hl))))
    fig = plt.figure(figsize=(12, 13))
    gs = fig.add_gridspec(3, 4, height_ratios=[1.3, 0.8, 0.85], hspace=0.5, wspace=0.34)
    for j, (name, ylab, a_th) in enumerate((('power', 'Power (kW)', 3), ('rotor speed', 'Rotor speed (rpm)', 1))):
        ax = fig.add_subplot(gs[0, 2 * j:2 * j + 2])
        for u, (t, m, c) in units.items():
            ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names],
                      color=col.get(u, LB.GREY), lw=1.4 if u in col else 0.7, zorder=3 if u in col else 1)
        for u in hl:
            v = U[u]; cc = col[u]; cen = v['brk'][:, j]
            ax.fill_between(v['x'], np.exp(cen - v['bKL']), np.exp(cen + v['bKL']), color=KL, alpha=0.06, lw=0)
            ax.fill_between(v['x'], np.exp(cen - v['bKS']), np.exp(cen + v['bKS']), color=KS, alpha=0.13, lw=0)
            ax.loglog(v['x'], np.exp(cen), ls='-.', color=cc, lw=1.1)
            out = np.linalg.norm(v['lab'] - v['brk'], axis=1) > v['bKS']
            ax.plot(v['x'][out], np.exp(v['lab'][out, j]), 'X', ms=7, color=LB.OUTC, mec='k', mew=0.4, zorder=5)
        ax.axhline(np.exp(WIND_CAP[j]), color='k', lw=0.7, ls=':')
        ax.text(4.8, np.exp(WIND_CAP[j]) * 1.05, 'spec: %s' % ('2,050 kW rated' if j == 0 else '15 rpm max'), fontsize=7.5)
        for lo, hi, lab in ((6.5, 8.5, 'law cal.'), (8.5, 10.5, 'A'), (11.5, 14.5, 'B')):
            ax.axvspan(lo, hi, color='#f2f2f2', zorder=0)
            ax.text(np.sqrt(lo * hi), 0.97, lab, transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=7.5)
        c0 = units[hl[0]][2]
        LB.slope_line(ax, 5.0, 9.0, (1.3 if j == 0 else 0.98) * np.exp(c0.TM[c0.names[0]][j]) * (5 / 4.75) ** a_th,
                      a_th, str(a_th))
        ax.set_xticks([5, 7, 10, 14]); ax.set_xticklabels(['5', '7', '10', '14'])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlabel('Wind speed (m/s)'); ax.set_ylabel(ylab)
        ax.set_title('(%s) Wind %s, %d (unseen confirmation year)' % ('ab'[j], name, YEAR), fontsize=9)
        if j == 0:
            ax.legend([Line2D([], [], color=col[u], lw=2) for u in hl] +
                      [Line2D([], [], color='k', ls='-.'), Patch(color=KL, alpha=0.15), Patch(color=KS, alpha=0.3),
                       Line2D([], [], ls='', marker='X', color=LB.OUTC, mec='k', ms=7)],
                      hl + ['law with spec-sheet break', 'K-L: allowance keeps growing',
                            'K-S1: allowance frozen at the cap', 'outside K-S1'],
                      title='Turbine-month', fontsize=6.8, title_fontsize=7.5, loc='lower right', ncol=2)
    # Ratio panels, every unit.
    test = lambda x: ((x >= 8.5) & (x < 10.5)) | ((x >= 11.5) & (x < 14.5))
    for k, (rule, key) in enumerate((('K-L, allowance keeps growing', 'bKL'), ('K-S1, frozen at the cap', 'bKS'))):
        a = fig.add_subplot(gs[1, 2 * k:2 * k + 2])
        curves = [(v['x'], np.linalg.norm(v['lab'] - v['brk'], axis=1) / v[key]) for v in U.values()]
        LB.ratio_panel(a, curves, '(%s) %s' % ('cd'[k], rule), test, 'Wind speed (m/s)')
        for lo, hi in ((8.5, 10.5), (11.5, 14.5)):
            a.axvspan(lo, hi, color='#f2f2f2', zorder=0)
        a.set_xticks([9, 10, 11, 12, 14]); a.set_xticklabels(['9', '10', '11', '12', '14'])
        a.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if k == 0:
            a.set_ylabel('law error / allowance\n(> 1: not bounded)')
    # Summary over years.
    years = [2016, 2017, 2018, 2019, 2020]
    for k, (key, lab) in enumerate((('premise', 'Premise held'), ('Se', 'Median S / e'))):
        a = fig.add_subplot(gs[2, 2 * k:2 * k + 2])
        x = np.arange(len(years) * 2); w = 0.26
        for i, (rule, cc) in enumerate((('L', '#9a9a9a'), ('K-L', KL), ('K-S1', KS))):
            vals = [RES['%d|%s|%s' % (y, s, rule)][key] for s in 'AB' for y in years]
            a.bar(x + (i - 1) * w, vals, w * 0.92, color=cc, label=rule)
            if key == 'Se':
                for xi, s_, y in zip(x + (i - 1) * w, [s for s in 'AB' for _ in years], [y for _ in 'AB' for y in years]):
                    if RES['%d|%s|%s' % (y, s_, rule)]['valid'] < 0.9:
                        a.plot(xi, RES['%d|%s|%s' % (y, s_, rule)][key] + 0.05, 'v', color='k', ms=3.5)
        a.axhline(0.9 if key == 'premise' else 1.0, color='k', lw=0.8, ls=':')
        a.axvline(len(years) - 0.5, color='k', lw=0.6)
        a.set_xticks(x); a.set_xticklabels(['%s %d' % ('A' if i < len(years) else 'B', y)
                                            for i, y in enumerate(years * 2)], rotation=35, ha='right', fontsize=7.5)
        for xi in (len(years) - 1, 2 * len(years) - 1):
            a.get_xticklabels()[xi].set_fontweight('bold')
        a.set_ylim(0, 1.1 if key == 'premise' else 1.45); a.set_ylabel(lab)
        a.set_title('(%s) %s by year; A below rated | B rated; bold = unseen 2020%s'
                    % ('ef'[k], lab, '' if key == 'premise' else '; ▼ valid < 90%'), fontsize=8.5)
        if k == 0:
            a.legend(fontsize=7.5, ncol=3, loc='lower left', bbox_to_anchor=(0, 1.08), handlelength=1.2)
    fig.suptitle('Freezing the allowance at the spec-sheet cap: confirmed on Kelmarsh 2020', fontsize=11, y=0.93)
    fig.savefig(OUT / 'fig_saturating.png', bbox_inches='tight')
    print('-> saturating/fig_saturating.png')


if __name__ == '__main__':
    main()
