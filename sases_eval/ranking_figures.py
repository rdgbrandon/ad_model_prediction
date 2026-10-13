"""Ranking quality against the number of surrogates (n = 9, 25, 50, 100), every dataset.
Reads ranking/results.json (ranking_audit.py report). Writes ranking/fig_ranking.png.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import law_bound_plots as LB        # reference style

HERE = Path(__file__).resolve().parent
RES = json.loads((HERE / 'ranking' / 'results.json').read_text())
SETS = [('capillary', 'canonical_192', 'Capillary (192 mW ceiling)'), ('kelmarsh', 'B', 'Kelmarsh wind 2020'),
        ('penmanshiel', 'B', 'Penmanshiel wind 2017'), ('lahauteborne', 'B', 'La Haute Borne wind'),
        ('hilloftowie', 'B', 'Hill of Towie wind 2019'), ('pv9068', 'B', 'PVDAQ 9068 solar'),
        ('pv2107', 'B', 'PVDAQ 2107 solar')]
N = [9, 25, 50, 100]
SC = [('S', 0, '#2a3b8f', 'certificate S'), ('Sc', 1, '#62c4b8', 'measured-anchor S'),
      ('D', 2, '#9a9a9a', 'raw defect D'), ('cal', 3, '#e0201b', 'calibration maximum')]

fig, axes = plt.subplots(3, 7, figsize=(17, 8), sharex=True)
for k, (name, band, title) in enumerate(SETS):
    get = lambda n, key: RES.get('%s|%s|%d' % (name, band, n), {}).get(key)
    ax = axes[0, k]
    for lab, j, cc, txt in SC:
        ax.plot(N, [get(n, 'pair')[j] for n in N], 'o-', color=cc, lw=1.6, ms=4, label=txt)
    ax.set_ylim(0.8, 1.005); ax.set_title(title, fontsize=8.5)
    for row, key in ((1, 'worst'), (2, 'best')):
        ax = axes[row, k]
        for j, (cc, txt) in enumerate((('#2a3b8f', 'certificate S'), ('#e0201b', 'calibration maximum'))):
            ax.plot(N, [get(n, key)[j] for n in N], 'o-', color=cc, lw=1.6, ms=4, label=txt)
        ax.set_ylim(-0.03, 1.03)
for ax in axes[-1]:
    ax.set_xscale('log'); ax.set_xticks(N); ax.set_xticklabels([str(n) for n in N])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax.set_xlabel('surrogates ranked (n)')
axes[0, 0].set_ylabel('pairs ordered correctly'); axes[1, 0].set_ylabel('picks the worst model')
axes[2, 0].set_ylabel('best model not wrongly flagged')
axes[0, 0].legend(fontsize=6.5, loc='lower left'); axes[1, 0].legend(fontsize=6.5, loc='lower left')
fig.suptitle('Ranking 9 to 100 surrogates per test bin (beyond the cap; capillary: 192 mW ceiling)', fontsize=11)
fig.tight_layout()
fig.savefig(HERE / 'ranking' / 'fig_ranking.png', bbox_inches='tight')
print('-> ranking/fig_ranking.png')
