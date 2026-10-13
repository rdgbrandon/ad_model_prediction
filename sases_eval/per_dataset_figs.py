"""Per-dataset ranking and ablation figures for the organised report.
  multi/fig_<name>_R.png   ranking quality against the number of surrogates (9 to 100)
  multi/fig_<name>_X.png   ablation of the three terms, beyond the cap
Reads ranking/results.json and ablation_multi/results.json.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import law_bound_plots as LB        # reference style

HERE = Path(__file__).resolve().parent
RK = json.loads((HERE / 'ranking' / 'results.json').read_text())
AB = json.loads((HERE / 'ablation_multi' / 'results.json').read_text())
BAND = {'capillary': 'canonical_192'}
N = [9, 25, 50, 100]
GOLD, EDGE = '#f2c14e', '#7a5a00'
VARS = ['D', 'D − b', 'D − β', 'D − b − β']
VCOL = ['#9a9a9a', '#f39c12', '#62c4b8', GOLD]


def ranking(name):
    band = BAND.get(name, 'B')
    get = lambda n, k: RK['%s|%s|%d' % (name, band, n)][k]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.1))
    for lab, j, cc in (('certificate S', 0, EDGE), ('raw defect D', 2, '#9a9a9a'), ('calibration maximum', 3, '#e0201b')):
        axes[0].plot(N, [get(n, 'pair')[j] for n in N], 'o-', color=cc, lw=1.8, ms=4, label=lab)
    for ax, key, title in ((axes[1], 'worst', 'finds the worst model'), (axes[2], 'best', 'does not blame the best model')):
        for j, (lab, cc) in enumerate((('certificate S', EDGE), ('calibration maximum', '#e0201b'))):
            ax.plot(N, [get(n, key)[j] for n in N], 'o-', color=cc, lw=1.8, ms=4, label=lab)
        ax.set_ylim(-0.03, 1.05); ax.set_title(title, fontsize=9)
    axes[0].set_title('pairs of models ordered correctly', fontsize=9)
    lo = min(min(get(n, 'pair')) for n in N)
    axes[0].set_ylim(min(0.8, lo - 0.02), 1.005)
    axes[0].legend(fontsize=7, loc='lower left')
    for ax in axes:
        ax.set_xscale('log'); ax.set_xticks(N); ax.set_xticklabels([str(n) for n in N])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax.set_xlabel('number of surrogates ranked')
    fig.tight_layout()
    fig.savefig(HERE / 'multi' / ('fig_%s_R.png' % name), bbox_inches='tight'); plt.close(fig)


def ablation(name):
    band = BAND.get(name, 'B')
    v = AB['%s|%s' % (name, band)]; m = v['means']
    fig, (ax, a2) = plt.subplots(1, 2, figsize=(11, 3.3), gridspec_kw=dict(width_ratios=[1.1, 1.4]))
    steps = [(m['D'], 0, '#9a9a9a'), (-m['b'], m['D'], '#f39c12'), (-m['beta'], m['D'] - m['b'], '#62c4b8')]
    for k, (h, base, cc) in enumerate(steps):
        ax.bar(k, h, bottom=base, color=cc, width=0.7)
    ax.bar(3, m['raw'], facecolor='none', edgecolor='k', linewidth=1.1, width=0.7, ls='--')
    ax.bar(4, m['S'], color=GOLD, width=0.7, edgecolor='k', linewidth=1.6, zorder=3)
    ax.bar(5, m['e'], color='#e0201b', width=0.7)
    ax.axhline(m['S'], color='k', lw=1.0, ls='--')
    ax.set_xticks(range(6)); ax.set_xticklabels(['D', '− b', '− β', '= sum', 'S final', 'e'], fontsize=8)
    ax.set_ylabel('mean, log units'); ax.set_ylim(0, 1.1 * max(m['D'], m['e']))
    ax.set_title('(a) the three terms add up to the certificate', fontsize=9)
    x = np.arange(len(VARS)); w = 0.38
    a2.bar(x - w / 2, [v[k]['valid'] for k in VARS], w * 0.92, color=VCOL, edgecolor=['none'] * 3 + ['k'],
           linewidth=1.3, label='valid (S ≤ e)')
    a2.bar(x + w / 2, [min(v[k]['Se'], 1.6) for k in VARS], w * 0.92, color=VCOL, alpha=0.45,
           edgecolor=['none'] * 3 + ['k'], linewidth=1.3, hatch='//', label='median S / e')
    a2.axhline(1, color='k', lw=0.6, ls=':')
    for xi, k in zip(x, VARS):
        a2.text(xi - w / 2, v[k]['valid'] + 0.03, '%.2f' % v[k]['valid'], ha='center', fontsize=7)
        a2.text(xi + w / 2, min(v[k]['Se'], 1.6) + 0.03, '%.2f' % v[k]['Se'], ha='center', fontsize=7)
    a2.set_xticks(x); a2.set_xticklabels(VARS, fontsize=8); a2.set_ylim(0, 1.75)
    a2.set_title('(b) which terms make it a bound: solid = valid, hatched = median S/e', fontsize=9)
    fig.tight_layout()
    fig.savefig(HERE / 'multi' / ('fig_%s_X.png' % name), bbox_inches='tight'); plt.close(fig)


if __name__ == '__main__':
    for nm in ('capillary', 'kelmarsh', 'pv9068', 'penmanshiel', 'lahauteborne', 'hilloftowie', 'pv2107'):
        ranking(nm); ablation(nm)
    print('per-dataset ranking and ablation figures written')
