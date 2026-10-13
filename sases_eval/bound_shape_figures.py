"""Figure for BOUND_SHAPE_PROTOCOL.md: the wind law with and without the spec-sheet break,
and premise coverage / median S/e for rules L, A, K-L, K-A on every system.
Reads bound_shape/results.json and the 2019 wind units. Writes bound_shape/fig_bound_shape.png.
"""
import json
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

HERE = Path(__file__).resolve().parent
OUT = HERE / 'bound_shape'
RES = json.loads((OUT / 'results.json').read_text())
AA.YEARS[2019] = HERE / 'wind' / '2019'
RC = {'C': '#9a9a9a', 'L': '#2a78d6', 'A': '#62c4b8', 'K-L': '#e0201b', 'K-A': '#f39c12'}


def curves(fig, gs):
    units = AA.units_of(2019)
    hl = [u for u in ('T1-01', 'T3-05', 'T5-09') if u in units]
    col = dict(zip(hl, ['#e0201b', '#0b7a3a', '#2a3b8f']))
    for j, (name, ylab, a_th) in enumerate((('power', 'Power (kW)', 3), ('rotor speed', 'Rotor speed (rpm)', 1))):
        ax = fig.add_subplot(gs[0, 2 * j:2 * j + 2])
        n_out = {'L': 0, 'K-L': 0}
        for u, (t, m, c) in units.items():
            ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names],
                      color=col.get(u, LB.GREY), lw=1.4 if u in col else 0.7, zorder=3 if u in col else 1)
        for u in hl:
            c = units[u][2]; q, top = AA.ceiling_line(c)
            R = rates(c, c.band('LAWCAL'), q, top, e1_hops(c))
            ns = [n for n in c.names if c.lp[n] > c.lp[top]]
            x = np.array([c.TP[n] for n in ns]); d = np.array([c.lp[n] - c.lp[top] for n in ns])
            line = c.TM[top][j] + q[j] * d; brk = np.minimum(line, WIND_CAP[j]); b = 2 * R['k'] * d
            ax.loglog(x, np.exp(line), ls='--', color=col[u], lw=0.9)
            ax.fill_between(x, np.exp(brk - b), np.exp(brk + b), color=col[u], alpha=0.12, lw=0)
            ax.loglog(x, np.exp(brk), ls='-.', color=col[u], lw=1.2)
            lab = np.array([c.TM[n][j] for n in ns])
            out = np.abs(lab - brk) > b
            ax.plot(x[out], np.exp(lab[out]), 'X', ms=7, color=LB.OUTC, mec='k', mew=0.4, zorder=5)
        ax.axhline(np.exp(WIND_CAP[j]), color='k', lw=0.7, ls=':')
        ax.text(4.8, np.exp(WIND_CAP[j]) * 1.06, 'spec: %s' % ('2,050 kW rated' if j == 0 else '15 rpm max'),
                fontsize=7.5)
        for lo, hi, lab in ((6.5, 8.5, 'law cal.'), (8.5, 10.5, 'A'), (11.5, 14.5, 'B')):
            ax.axvspan(lo, hi, color='#f2f2f2', zorder=0)
            ax.text(np.sqrt(lo * hi), 0.97, lab, transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=7.5)
        LB.slope_line(ax, 5.0, 9.0, (1.3 if j == 0 else 1.12) * np.exp(units[hl[0]][2].TM[units[hl[0]][2].names[0]][j]) * (5 / 4.75) ** a_th,
                      a_th, str(a_th))
        ax.set_xticks([5, 7, 10, 14]); ax.set_xticklabels(['5', '7', '10', '14'])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlabel('Wind speed (m/s)'); ax.set_ylabel(ylab)
        ax.set_title('(%s) Wind %s, 2019 (unseen year)' % ('ab'[j], name), fontsize=9)
        if j == 0:
            ax.legend([Line2D([], [], color='k', ls='--'), Line2D([], [], color='k', ls='-.'),
                       Patch(color='k', alpha=0.12), Line2D([], [], ls='', marker='X', color=LB.OUTC, mec='k', ms=7)],
                      ['straight law (L)', 'law with spec-sheet break (K)', 'allowance around K',
                       'outside the K allowance'], fontsize=7, loc='lower right')


def bars(fig, gs):
    groups = [('Capillary 146', 'capillary|canonical_146'), ('Capillary 192', 'capillary|canonical_192')]
    groups += [('Wind %d %s' % (y, s), 'wind|%d%s' % (y, s)) for y in (2016, 2017, 2018, 2019) for s in 'AB']
    groups += [('Solar %d %s' % (y, s), 'solar|%d%s' % (y, s)) for y in (2018, 2019) for s in 'AB']
    for k, (key, lab) in enumerate((('premise', 'Premise held (share of rows)'), ('Se', 'Median S / e'))):
        ax = fig.add_subplot(gs[1 + k, :])
        x = np.arange(len(groups)); w = 0.16
        for i, rule in enumerate(['L', 'A', 'K-L', 'K-A']):
            vals = [RES.get('%s|%s' % (g, rule), {}).get(key, np.nan) for _, g in groups]
            valid = [RES.get('%s|%s' % (g, rule), {}).get('valid', np.nan) for _, g in groups]
            bars_ = ax.bar(x + (i - 1.5) * w, vals, w * 0.92, color=RC[rule], label=rule)
            if key == 'Se':
                for xi, v, vv in zip(x + (i - 1.5) * w, vals, valid):
                    if np.isfinite(vv) and vv < 0.9:
                        ax.plot(xi, v + 0.04, 'v', color='k', ms=3.5)
        ax.axhline(0.9 if key == 'premise' else 1.0, color='k', lw=0.8, ls=':')
        ax.axvline(1.5, color='k', lw=0.6); ax.axvline(9.5, color='k', lw=0.6); ax.axvline(7.5, color='#888', lw=0.5, ls='--')
        ax.set_xticks(x); ax.set_xticklabels([g[0] for g in groups], rotation=30, ha='right', fontsize=7.5)
        ax.set_ylabel(lab); ax.set_xlim(-0.6, len(groups) - 0.4)
        if k == 0:
            ax.set_ylim(0, 1.08)
            ax.legend(ncol=4, fontsize=7.5, loc='upper left', bbox_to_anchor=(0.0, 1.16),
                      title=None, handlelength=1.2)
            ax.text(8.5, 1.02, '2019 = unseen', ha='center', fontsize=7)
            ax.set_title('(c) L straight-line, A offset + slope, K-L / K-A law with spec-sheet break '
                         '(capillary has no break: L, A only)', fontsize=8.5, pad=22)
        else:
            ax.set_ylim(0, 1.5)
            ax.set_title('(d) Median S / e   (▼ = bound valid on fewer than 90% of rows; '
                         'above the dotted line the median row is not a bound)', fontsize=8.5)


if __name__ == '__main__':
    fig = plt.figure(figsize=(11.5, 12))
    gs = fig.add_gridspec(3, 4, height_ratios=[1.25, 0.8, 0.8], hspace=0.6, wspace=0.34)
    curves(fig, gs); bars(fig, gs)
    fig.suptitle('Shape of the law allowance: a spec-sheet break fixes wind; offset + slope does not help',
                 fontsize=11, y=0.93)
    fig.savefig(OUT / 'fig_bound_shape.png', bbox_inches='tight')
    print('-> bound_shape/fig_bound_shape.png')
