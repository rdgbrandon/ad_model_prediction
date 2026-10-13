"""Figures for the law-allowance report: the worked derivation and the learned rules.
Reads learned/derivation.json, learned/dev.json and learned/confirm.json."""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'learned'
INK, INK2, MUTED, GRID, AXIS = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
W_IN = 6.4
plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'DejaVu Sans'], 'font.size': 8,
    'axes.titlesize': 8.5, 'axes.titleweight': 'bold', 'axes.titlelocation': 'left',
    'axes.labelsize': 8, 'axes.labelcolor': INK2, 'axes.edgecolor': AXIS, 'axes.linewidth': 0.6,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.5, 'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.labelcolor': INK2,
    'ytick.labelcolor': INK2, 'xtick.major.size': 0, 'ytick.major.size': 0, 'legend.frameon': False,
    'legend.fontsize': 7, 'savefig.dpi': 300})


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches='tight', pad_inches=0.04, facecolor='white')
    plt.close(fig)
    print('->', OUT / name)


def fig_derivation():
    """beta(delta) for each rule against what it learns from and what it must cover."""
    D = json.loads((OUT / 'derivation.json').read_text())
    fig, axes = plt.subplots(1, 2, figsize=(W_IN, 2.9))
    for ax, key, title in ((axes[0], 'wind', 'a  Wind unit %s (2017)'), (axes[1], 'pv', 'b  Solar unit %s')):
        U = D[key]
        dmax = max(t['delta'] for t in U['tests']) * 1.12
        dd = np.linspace(0, dmax, 50)
        # what the calibration-only rates learn from
        hx = [h['delta'] for h in U['hops_E1']]; hy = [h['zeta'] for h in U['hops_E1']]
        ax.plot(hx, hy, 'o', ms=4.5, mfc='white', mec=MUTED, mew=1.0, zorder=3)
        # the formula lines
        lines = ((U['kappa_C'], 'C', (0, (1, 1.5))), (2 * U['kappa_P'], 'P', (0, (4, 2))),
                 (2 * U['kappa_E1'], 'E1', '-'))
        top = max(max(t['beta']['E3'], t['beta']['F0'], t['zeta_norm']) for t in U['tests'])
        labels = {}
        for rate, lab, ls in lines:
            ax.plot(dd, rate * dd, color=INK2, lw=1.1, ls=ls, zorder=2)
            # merge labels whose line ends nearly coincide
            near = [k for k in labels if abs(k - rate * dmax) < 0.05 * top]
            if near:
                labels[near[0]] = labels[near[0]] + ', ' + lab
            else:
                labels[rate * dmax] = lab
        for y, lab in labels.items():
            ax.text(dmax, y, ' ' + lab, va='center', ha='left', fontsize=6.8, color=INK2)
        # fleet allowances at the test bins
        for t in U['tests']:
            b = t['beta']
            ax.plot([t['delta']] * 2, [0, t['zeta_norm']], color=GRID, lw=0.8, zorder=1)
            ax.plot(t['delta'], b['F0'], marker='_', ms=14, mew=2.2, color=BLUE, zorder=4)
            ax.plot(t['delta'], b['E3'], marker='_', ms=14, mew=2.2, color=ORANGE, zorder=4)
            ax.plot(t['delta'], t['zeta_norm'], 'o', ms=6, color=INK, mec='white', mew=1.2, zorder=5)
        ax.set_xlim(0, dmax * 1.13); ax.set_ylim(0, None)
        ax.set_title(title % U['unit'], color=INK)
        ax.set_xlabel('Extrapolation distance δ')
    axes[0].set_ylabel('Law residual ‖ζ‖ and allowance β (log units)')
    from matplotlib.lines import Line2D
    fig.legend([Line2D([], [], ls='', marker='o', ms=4.5, mfc='white', mec=MUTED),
                Line2D([], [], ls='', marker='o', ms=6, color=INK),
                Line2D([], [], color=INK2, lw=1.1),
                Line2D([], [], ls='', marker='_', ms=12, mew=2.2, color=BLUE),
                Line2D([], [], ls='', marker='_', ms=12, mew=2.2, color=ORANGE)],
               ['calibration hops (what E1 learns from)', 'test-bin residual (must be covered)',
                'own-data rules C, P, E1', 'F0: fleet rate × δ', 'E3: fleet per-bin quantile'],
               loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.14), fontsize=6.6, handlelength=1.6)
    fig.tight_layout(w_pad=2.5)
    save(fig, 'figL1_derivation.png')


ROWS = [('C', 'C  theory distance', 'own'), ('P', 'P  paper Eq. 5', 'own'), ('E1', "E1  long-hop κ'", 'own'),
        ('Z', 'Z  monotone saturation', 'own'), ('S', 'S  spec sheet', 'own'),
        ('A-NN', 'A-NN  own-data MLP', 'alearn'), ('A-KAN', 'A-KAN  own-data KAN', 'alearn'),
        ('E3', 'E3  fleet per-bin quantile', 'fleet'), ('F0', 'F0  fleet rate × δ', 'fleet'),
        ('F-lin', 'F-lin  ridge scale', 'fleet'), ('F-GBT', 'F-GBT  boosted-tree scale', 'fleet'),
        ('F-NN-ens', 'F-NN  MLP scale (3 seeds)', 'fleet'), ('F-KAN-ens', 'F-KAN  KAN scale (3 seeds)', 'fleet')]
FAM = {'own': INK2, 'alearn': AQUA, 'fleet': BLUE}


def rows_panel(ax, res, title, with_se):
    rows = [r for r in ROWS if r[0] in res]
    ys = np.arange(len(rows))[::-1]
    ax.axvline(0.90, color=INK2, lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.text(0.90, len(rows) - 0.45, '0.90 ', ha='right', va='bottom', fontsize=6, color=INK2)
    prev = None
    for y, (key, lab, fam) in zip(ys, rows):
        if prev is not None and fam != prev:
            ax.axhline(y + 0.5, color=GRID, lw=0.8)
        prev = fam
        o = res[key]
        v = o['committed'] if o['committed'] is not None else o['premise']
        lo, hi = o['committed_ci'] if o['committed_ci'] else o['premise_ci']
        ax.plot([lo, hi], [y, y], color=FAM[fam], lw=1.2, alpha=0.55, zorder=2)
        ax.plot(v, y, 'o', ms=5.0, color=FAM[fam], mec='white', mew=1.0, zorder=3)
        tx = ax.get_yaxis_transform()
        ax.text(1.06, y, '--' if o['tightness'] is None else '%.2f' % o['tightness'],
                va='center', ha='left', fontsize=6.3, color=INK2, transform=tx)
        if with_se and 'median_S_over_e' in o:
            ax.text(1.36, y, '%.2f' % o['median_S_over_e'], va='center', ha='left', fontsize=6.3,
                    color=INK2, transform=tx)
        if o['abstain'] > 0.005:
            ax.text(1.62, y, '%d%%' % round(100 * o['abstain']), va='center', ha='left', fontsize=6.3,
                    color=INK2, transform=tx)
    top = len(rows) - 0.45
    tx = ax.get_yaxis_transform()
    ax.text(1.06, top, 'β/‖ζ‖', ha='left', va='bottom', fontsize=6.2, color=INK2, fontweight='bold', transform=tx)
    if with_se and any('median_S_over_e' in res[r[0]] for r in rows):
        ax.text(1.36, top, 'S/e', ha='left', va='bottom', fontsize=6.2, color=INK2, fontweight='bold', transform=tx)
    if any(res[r[0]]['abstain'] > 0.005 for r in rows):
        ax.text(1.62, top, 'abst.', ha='left', va='bottom', fontsize=6.2, color=INK2, fontweight='bold', transform=tx)
    ax.set_yticks(ys); ax.set_yticklabels([r[0].replace('-ens', '') for r in rows], fontsize=6.8)
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.6, len(rows) + 0.2)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0]); ax.set_xticklabels(['0', '.25', '.5', '.75', '1'])
    ax.grid(axis='y', visible=False)
    ax.set_title(title, color=INK, pad=10)


def fig_results(mode, name, panels):
    """panels: list of (pool index, scenario, title). Axes placed explicitly so the
    side columns of numbers do not squeeze the plot."""
    R = json.loads((OUT / ('%s.json' % mode)).read_text())['pools']
    nrow = (len(panels) + 1) // 2
    H = 2.75
    fig = plt.figure(figsize=(W_IN, H * nrow + 0.35))
    from matplotlib.lines import Line2D
    for k, (pi, sc, title) in enumerate(panels):
        r, c = divmod(k, 2)
        x0 = 0.065 + 0.5 * c
        y0 = 1 - (r + 1) * H / (H * nrow + 0.35) + 0.035
        ax = fig.add_axes([x0, y0, 0.215, H / (H * nrow + 0.35) - 0.09])
        rows_panel(ax, R[pi]['results'][sc], title, with_se=True)
        if r == nrow - 1:
            ax.set_xlabel('Premise coverage, committed bins')
    fig.legend([Line2D([], [], ls='', marker='o', ms=5, color=c) for c in (INK2, AQUA, BLUE)],
               ['own data, formula (C, P, E1, Z, S)', 'own data, learned (A-NN, A-KAN)',
                'fleet-calibrated (E3, F0, F-lin, F-GBT, F-NN, F-KAN)'],
               loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.01), fontsize=6.5, handlelength=1)
    save(fig, name)


def fig_partial():
    """What the fleet scale models learned on wind 2016-17: sigma against delta and
    against rotor speed at the ceiling, other features at their median."""
    import pickle
    import learned_allowance as L
    rows = []
    for y in (2016, 2017):
        rows += pickle.loads((OUT / ('table_wind_%d.pkl' % y)).read_bytes())[1]
    X = np.stack([r['x'] for r in rows]); z = np.array([r['zeta'] for r in rows])
    med = np.median(X, 0)
    models = [('F-lin', 'ridge', BLUE), ('F-GBT', 'boosted trees', ORANGE), ('F-NN', 'MLP', AQUA),
              ('F-KAN', 'KAN', '#4a3aa7')]
    fits = {k: L.fit_scale(k, 0, X, z) for k, _, _ in models}
    fig, axes = plt.subplots(1, 2, figsize=(W_IN, 2.6))
    # (a) against delta: u moves with delta (u = u_ceiling + delta)
    d = np.linspace(X[:, 0].min(), X[:, 0].max(), 120)
    G = np.tile(med, (len(d), 1)); G[:, 0] = d; G[:, 1] = med[1] - med[0] + d
    ax = axes[0]
    ax.plot(X[:, 0], z, 'o', ms=2.2, color=GRID, mec='none', zorder=1)
    for k, lab, col in models:
        y = fits[k](G)
        ax.plot(d, y, color=col, lw=2, zorder=3, label=lab)
    ax.set_xlim(0, d[-1] * 1.05); ax.set_ylim(0, None)
    ax.set_title('a  Learned scale σ vs extrapolation distance', color=INK)
    ax.set_xlabel('δ'); ax.set_ylabel('σ (log units); grey: training ‖ζ‖')
    # (b) against rotor speed at the ceiling, at the median delta of the rated band
    dB = np.median([r['delta'] for r in rows if r['band'] == 'B'])
    w = np.linspace(np.percentile(X[:, 5], 2), np.percentile(X[:, 5], 98), 120)
    G = np.tile(med, (len(w), 1)); G[:, 0] = dB; G[:, 1] = med[1] - med[0] + dB; G[:, 5] = w
    ax = axes[1]
    for k, lab, col in models:
        y = fits[k](G)
        ax.plot(np.exp(w), y, color=col, lw=2)
    ax.set_xlim(np.exp(w[0]), np.exp(w[-1])); ax.set_ylim(0, 1.2)
    ax.set_title('b  σ vs rotor speed at the ceiling bin (δ = %.2f)' % dB, color=INK)
    ax.set_xlabel('Rotor speed at 8.25 m/s (rpm)')
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, ['%s scale model' % x for x in l], loc='lower center', ncol=4,
               bbox_to_anchor=(0.5, -0.06), fontsize=6.8, handlelength=1.8)
    fig.tight_layout(w_pad=2.0)
    save(fig, 'figL4_partial.png')


if __name__ == '__main__':
    import sys
    fig_derivation()
    fig_partial()
    if (OUT / 'dev.json').exists():
        fig_results('dev', 'figL2_dev.png', [(0, 'A', 'a  Wind 2016 → 2017, below rated'),
                                              (0, 'B', 'b  Wind 2016 → 2017, rated region'),
                                              (1, 'A', 'c  Solar 2017 → 2018, below clipping'),
                                              (2, 'A', 'd  Solar 2017-18 → 2019, below clipping')])
    if (OUT / 'confirm.json').exists():
        fig_results('confirm', 'figL3_confirm.png', [(0, 'A', 'a  Wind 2016-17 → 2018, below rated'),
                                                      (0, 'B', 'b  Wind 2016-17 → 2018, rated region'),
                                                      (2, 'A', 'c  Solar 2017-19 → 2023, below clipping'),
                                                      (2, 'B', 'd  Solar 2017-19 → 2023, above clipping')])
