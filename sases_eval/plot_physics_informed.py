"""Figure: certificate and true error as the surrogate is trained toward a law.

Small multiples, one panel per law. Two series in the same unit (error norm) on
one axis: the measured error and the certificate. Band = range over the three
seeds of the per-seed mean. Palette: reference categorical slots 1 and 2,
validated (scripts/validate_palette.js, light mode: all checks pass).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / 'physics_informed/results.json').read_text())
R = D['rows']

SURFACE, INK, INK2, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#e4e3df'
SERIES = {'e': ('#2a78d6', 'true error e'), 'S': ('#eb6834', 'certificate S')}
WEIGHTS = D['weights']
XT = ['0', '$10^{-2}$', '$10^{-1}$', '1', '10', '$10^{2}$', '$10^{3}$']
TITLES = {'certificate law': 'Trained toward the law\nthe certificate checks',
          'training law': 'Trained toward the law\nseen in training',
          'KZ theory': 'Trained toward the textbook\nKZ exponent (0.5)'}


def series(ds, arm, key):
    """Per-seed mean over splits and trials; returns mean and seed range."""
    per_seed = np.array([[np.mean([r[key] for r in R if r['dataset'] == ds and r['arm'] == arm
                                   and r['w'] == w and r['seed'] == s])
                          for w in WEIGHTS] for s in D['seeds']])
    return per_seed.mean(0), per_seed.min(0), per_seed.max(0)


def figure(ds, out):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.edgecolor': GRID, 'axes.labelcolor': INK2,
                         'xtick.color': INK2, 'ytick.color': INK2, 'text.color': INK})
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9), sharey=True, facecolor=SURFACE)
    x = np.arange(len(WEIGHTS))
    for ax, arm in zip(axes, D['arms']):
        ax.set_facecolor(SURFACE)
        for key in ('e', 'S'):
            col, lab = SERIES[key]
            m, lo, hi = series(ds, arm, key)
            ax.fill_between(x, lo, hi, color=col, alpha=.15, linewidth=0)
            ax.plot(x, m, color=col, lw=2, marker='o', ms=6, label=lab,
                    markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
        ax.set_title(TITLES[arm], fontsize=10.5, color=INK, loc='left')
        ax.set_xticks(x); ax.set_xticklabels(XT)
        ax.set_xlabel('physics penalty weight w')
        ax.grid(axis='y', color=GRID, lw=.8); ax.set_axisbelow(True)
        for s in ('top', 'right'):
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0)
    axes[0].set_ylabel('error norm (mean over splits and test trials)')
    # Direct labels on the first panel, at the right end, in ink - not series color.
    for key in ('e', 'S'):
        m, _, _ = series(ds, D['arms'][0], key)
        axes[0].annotate(SERIES[key][1], (x[-1], m[-1]), xytext=(6, 0),
                         textcoords='offset points', va='center', fontsize=9, color=INK2)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper right', frameon=False,
               ncol=2, fontsize=9.5, bbox_to_anchor=(0.995, 1.0))
    fig.suptitle('Physics-informed surrogates (%s): certificate S against the true error e'
                 % ds, x=0.01, ha='left', fontsize=12, color=INK, fontweight='bold')
    fig.text(0.01, -0.02, 'Bands: range over three seeds. Two calibration splits, '
             'three or four test trials each. Bound held on every row.',
             fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=200, facecolor=SURFACE, bbox_inches='tight')
    plt.close(fig)
    print('wrote', out)


if __name__ == '__main__':
    for ds in D['datasets']:
        figure(ds, HERE / 'physics_informed' / ('pinn_sweep_%s.png' % ds))
