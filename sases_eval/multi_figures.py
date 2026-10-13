"""Figures for MULTI_DATASET_PROTOCOL.md, one set per dataset, in the reference style.

  A  curves: every unit, the straight law, the capped law, the K-S1 allowance, points outside it
  B  every unit's law error / allowance for L, K-L, K-S1 (above 1: the law is not bounded)
  C  the total bound as three terms per surrogate (D, b, beta -> S) beside the true error e,
     and premise / validity / S/e for each rule
Writes multi/fig_<name>_{A,B,C}.png. Reads multi/<name>_rows.pkl and the unit records.
"""
import json
import pickle
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

import law_bound_plots as LB                     # reference style, palette, slope line, ratio panel
import multi_audit as MA

HERE = Path(__file__).resolve().parent
OUT = MA.OUT
RES = json.loads((OUT / 'results.json').read_text())
RULE_C = {'L': '#9a9a9a', 'K-L': '#e0201b', 'K-S1': '#2a3b8f'}
FAM = [m for m, _ in MA.MODELS]


def bands_of(meta):
    return MA.WIND_BANDS if meta['kind'] == 'wind' else MA.PV_BANDS


def fig_A(name, units, parts):
    meta = MA.DATASETS[name]
    outs = meta['outputs']; m = len(outs)
    fig, axes = plt.subplots(1, m, figsize=(6.2 * m, 5.0), squeeze=False)
    keys = sorted(units)
    hl = keys[:: max(1, len(keys) // 4)][:4]
    col = dict(zip(hl, LB.palette(len(hl))))
    for j, ax in enumerate(axes[0]):
        for u in keys:
            c = units[u]
            if u not in col:
                ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names], color=LB.GREY, lw=0.6)
        for u in hl:
            c = units[u]; q, top, k, line, capped, ds = parts[u]; cc = col[u]
            ax.loglog([c.TP[n] for n in c.names], [np.exp(c.TM[n][j]) for n in c.names], color=cc, lw=1.5, zorder=3)
            ns = [n for n in c.names if c.lp[n] > c.lp[top]]
            if not ns:
                continue
            x = np.array([c.TP[n] for n in ns]); d = np.array([c.lp[n] - c.lp[top] for n in ns])
            ln_ = np.array([line(dd)[j] for dd in d]); cp_ = np.array([capped(dd)[j] for dd in d])
            beta = 2 * k * np.minimum(d, ds)
            ax.loglog(np.r_[c.TP[top], x], np.exp(np.r_[c.TM[top][j], ln_]), ls='--', color=cc, lw=0.8)
            ax.loglog(np.r_[c.TP[top], x], np.exp(np.r_[c.TM[top][j], cp_]), ls='-.', color=cc, lw=1.2)
            ax.fill_between(x, np.exp(cp_ - beta), np.exp(cp_ + beta), color='#f2c14e', alpha=0.30, lw=0, zorder=2)
            ax.loglog(x, np.exp(cp_ + beta), color='#7a5a00', lw=1.3, zorder=4)
            ax.loglog(x, np.exp(cp_ - beta), color='#7a5a00', lw=1.3, zorder=4)
            lab = np.array([c.TM[n] for n in ns]); cen = np.array([capped(dd) for dd in d])
            out = np.linalg.norm(lab - cen, axis=1) > beta
            ax.plot(x[out], np.exp(lab[out, j]), 'X', ms=7, color=LB.OUTC, mec='k', mew=0.4, zorder=5)
        if meta['caps']:
            ax.axhline(meta['caps'][j], color='k', lw=0.7, ls=':')
            ax.text(0.02, meta['caps'][j] * 1.04, 'published cap %g' % meta['caps'][j],
                    transform=ax.get_yaxis_transform(), fontsize=7.5)
        if meta.get('x_cap'):
            ax.axvline(meta['x_cap'], color='k', lw=0.7, ls=':')
            ax.text(meta['x_cap'] * 1.01, 0.03, 'spec clipping %g' % meta['x_cap'],
                    transform=ax.get_xaxis_transform(), fontsize=7.5)
        for key, (lo, hi) in bands_of(meta).items():
            if key == 'TRAIN':
                continue
            ax.axvspan(lo, hi, color='#f2f2f2', zorder=0)
            ax.text(np.sqrt(lo * hi), 0.97, {'LAWCAL': 'law cal.', 'A': 'A', 'B': 'B'}[key],
                    transform=ax.get_xaxis_transform(), ha='center', va='top', fontsize=7.5)
        a_th = meta['q_th'][j]
        c0 = units[hl[0]]
        x0 = c0.TP[c0.names[0]]
        LB.slope_line(ax, x0 * 1.05, x0 * (1.9 if meta['kind'] == 'wind' else 2.6),
                      0.75 * np.exp(c0.TM[c0.names[0]][j]) * 1.05 ** a_th, a_th, '%g' % a_th)
        ax.set_xlabel(meta['x']); ax.set_ylabel(outs[j])
        ax.set_title('(%s) %s: %s' % ('ab'[j], meta['title'], outs[j].split(' (')[0].lower()), fontsize=9)
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if meta['kind'] == 'wind':
            ax.set_xticks([5, 7, 10, 14]); ax.set_xticklabels(['5', '7', '10', '14'])
        else:
            ax.set_xticks([200, 300, 500, 700, 1000]); ax.set_xticklabels(['200', '300', '500', '700', '1000'])
    axes[0, 0].legend([Line2D([], [], color=col[u], lw=2) for u in hl] +
                      [Line2D([], [], color=LB.GREY, lw=2), Line2D([], [], color='k', ls='--'),
                       Line2D([], [], color='k', ls='-.'), Patch(facecolor='#f2c14e', edgecolor='#7a5a00', alpha=0.6),
                       Line2D([], [], ls='', marker='X', color=LB.OUTC, mec='k', ms=7)],
                      [u.split('-', 1)[1] for u in hl] + ['other units', 'straight law', 'law with published cap',
                                                          'final bound (K-S1 range)', 'outside the bound'],
                      fontsize=6.8, loc='lower right', ncol=2, title='unit', title_fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT / ('fig_%s_A.png' % name), bbox_inches='tight'); plt.close(fig)


def fig_B(name, units, parts):
    meta = MA.DATASETS[name]
    lo_b = bands_of(meta)
    test = lambda x: ((x >= lo_b['A'][0]) & (x < lo_b['A'][1])) | ((x >= lo_b['B'][0]) & (x < lo_b['B'][1]))
    rules = ['L', 'K-L', 'K-S1']
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, rule in zip(axes, rules):
        curves = []
        for u, c in units.items():
            q, top, k, line, capped, ds = parts[u]
            ns = [n for n in c.names if c.lp[n] > c.lp[top]]
            if not ns:
                continue
            d = np.array([c.lp[n] - c.lp[top] for n in ns])
            cen = np.array([(line if rule == 'L' else capped)(dd) for dd in d])
            beta = 2 * k * (d if rule != 'K-S1' else np.minimum(d, ds))
            z = np.linalg.norm(np.array([c.TM[n] for n in ns]) - cen, axis=1)
            curves.append((np.array([c.TP[n] for n in ns]), z / beta))
        LB.ratio_panel(ax, curves, rule, test, meta['x'])
        for key in ('A', 'B'):
            ax.axvspan(*lo_b[key], color='#f2f2f2', zorder=0)
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        if meta['kind'] == 'wind':
            ax.set_xticks([9, 11, 14]); ax.set_xticklabels(['9', '11', '14'])
        else:
            ax.set_xticks([600, 800, 1000]); ax.set_xticklabels(['600', '800', '1000'])
    axes[0].set_ylabel('law error / allowance\n(> 1: not bounded)')
    fig.suptitle('%s: every unit, test bands shaded' % meta['title'], fontsize=10, y=1.03)
    fig.tight_layout()
    fig.savefig(OUT / ('fig_%s_B.png' % name), bbox_inches='tight'); plt.close(fig)


def fig_C(name):
    meta = MA.DATASETS[name]
    R = pickle.load(open(OUT / ('%s_rows.pkl' % name), 'rb'))
    if name == 'capillary':
        R = [r for r in R if r['dataset'] == 'ctr12']
        fams = list(dict.fromkeys(r['model'] for r in R))
        scen_list = sorted({r['scen'] for r in R})
    else:
        fams = FAM
        scen_list = [s for s in ('A', 'B') if any(r['scen'] == s for r in R)]
    show = scen_list[-1]                         # B where it exists (beyond the cap), else the last
    fig = plt.figure(figsize=(13, 4.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.7, 1, 1], wspace=0.32)
    ax = fig.add_subplot(gs[0])
    rs = [r for r in R if r['rule'] == 'K-S1' and r['scen'] == show]
    x = np.arange(len(fams)); w = 0.16
    cols = [('DT', '#7f7f7f', 'D  original defect'), ('bT', '#f39c12', 'b  anchor allowance'),
            ('betaT', '#62c4b8', 'β  law allowance'), ('ST', '#f2c14e', 'S = D − b − β  (final certificate)'),
            ('e', '#e0201b', 'e  true error')]
    for i, (key, cc, lab) in enumerate(cols):
        vals = [np.median([r[key] for r in rs if r['model'] == f]) if any(r['model'] == f for r in rs) else np.nan
                for f in fams]
        ax.bar(x + (i - 2) * w, vals, w * 0.92, color=cc, label=lab,
               edgecolor='k' if key == 'ST' else 'none', linewidth=1.3 if key == 'ST' else 0, zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([f.split('#')[0] if name != 'capillary' else f for f in fams],
                                         rotation=35, ha='right', fontsize=7)
    ax.set_ylabel('median, log units'); ax.legend(fontsize=6.8, ncol=5, loc='upper center', bbox_to_anchor=(0.5, -0.27), handlelength=1.0, columnspacing=0.8)
    ax.set_title('(a) Total bound, K-S1, %s, anchor at the top training bin' % show, fontsize=9)
    ax.set_yscale('symlog', linthresh=0.1); ax.set_ylim(0, None)
    for k, (key, lab) in enumerate((('premise', 'premise held'), ('Se_T', 'median S / e, total bound'))):
        a = fig.add_subplot(gs[1 + k])
        xs = np.arange(len(scen_list)); w2 = 0.26
        for i, rule in enumerate(['L', 'K-L', 'K-S1']):
            vals = [RES.get('%s|%s|%s' % (name, s, rule), {}).get(key, np.nan) for s in scen_list]
            a.bar(xs + (i - 1) * w2, vals, w2 * 0.92, color=RULE_C[rule], label=rule)
            if key == 'Se_T':
                for xi, s in zip(xs + (i - 1) * w2, scen_list):
                    vv = RES.get('%s|%s|%s' % (name, s, rule), {}).get('valid_T', 1)
                    if vv < 0.9:
                        a.plot(xi, RES['%s|%s|%s' % (name, s, rule)][key] + 0.04, 'v', color='k', ms=3.5)
        a.axhline(0.9 if key == 'premise' else 1.0, color='k', lw=0.7, ls=':')
        a.set_xticks(xs); a.set_xticklabels([s.replace('canonical_', 'ceiling ') for s in scen_list], fontsize=7.5)
        a.set_ylim(0, 1.1 if key == 'premise' else 1.4)
        a.set_title('(%s) %s%s' % ('bc'[k], lab, '' if key == 'premise' else '\n(▼ valid < 90%)'), fontsize=9)
        if k == 0:
            a.legend(fontsize=7, ncol=3, loc='lower left', bbox_to_anchor=(0, -0.22), handlelength=1.0)
    fig.suptitle('%s: the certificate S = max(D − b − β, 0)' % meta['title'], fontsize=10, y=1.02)
    fig.savefig(OUT / ('fig_%s_C.png' % name), bbox_inches='tight'); plt.close(fig)


def main(names):
    for name in names:
        if name != 'capillary':
            units = MA.load_units(name)
            parts = {u: MA.law_parts(name, c) for u, c in units.items()}
            fig_A(name, units, parts); fig_B(name, units, parts)
        fig_C(name)
        print('figures', name, flush=True)


if __name__ == '__main__':
    main(sys.argv[1:])
