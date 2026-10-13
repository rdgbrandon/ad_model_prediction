"""Figure for KS3_PROTOCOL.md: allowance size, coverage and S/e beyond the cap, K-L vs K-S1 vs K-S3,
2017-2021 (2021 = confirmation). Writes ks3/fig_ks3.png.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import law_bound_plots as LB          # reference style

HERE = Path(__file__).resolve().parent
RES = json.loads((HERE / 'ks3' / 'results.json').read_text())
YEARS = [y for y in range(2017, 2022) if '%d|B|K-S3' % y in RES]
RC = {'K-L': '#e0201b', 'K-S1': '#2a3b8f', 'K-S3': '#f2c14e'}

fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
x = np.arange(len(YEARS)); w = 0.27
for ax, key, title, ylim in ((axes[0], 'beta_over_zeta', 'allowance ÷ real law error (median)', None),
                             (axes[1], 'premise', 'range right (premise held)', (0, 1.05)),
                             (axes[2], 'Sce', 'error proven, median S/e (b = 0 form)', (0, 1.1))):
    for i, rule in enumerate(('K-L', 'K-S1', 'K-S3')):
        vals = [RES['%d|B|%s' % (y, rule)][key] for y in YEARS]
        ax.bar(x + (i - 1) * w, vals, w * 0.92, color=RC[rule], label=rule,
               edgecolor='k' if rule == 'K-S3' else 'none', linewidth=1.2)
        if key == 'premise':
            for xi, y in zip(x + (i - 1) * w, YEARS):
                lo, hi = RES['%d|B|%s' % (y, rule)]['ci']
                ax.plot([xi, xi], [lo, hi], color='k', lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([('%d\n(unseen)' % y) if y == 2021 else str(y) for y in YEARS])
    ax.set_title(title, fontsize=9.5)
    if ylim:
        ax.set_ylim(*ylim)
    if key == 'beta_over_zeta':
        ax.set_yscale('log'); ax.axhline(1, color='k', lw=0.7, ls=':')
    if key == 'premise':
        ax.axhline(0.9, color='k', lw=0.7, ls=':')
axes[0].legend(fontsize=8, loc='lower left')
fig.suptitle('Kelmarsh, beyond rated power: shrinking the allowance after the cap (K-S3)', fontsize=10.5, y=1.02)
fig.tight_layout()
fig.savefig(HERE / 'ks3' / 'fig_ks3.png', bbox_inches='tight')
print('-> ks3/fig_ks3.png')
