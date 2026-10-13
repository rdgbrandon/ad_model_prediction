"""Figures for PDE_PROTOCOL.md. Reads pde/<system>.json and pde/results.json.
  pde/fig_pde_scatter.png   certificate S against the true error e, every surrogate and test point
  pde/fig_pde_compare.png   symmetry certificate vs Lipschitz certificate vs conformal, per system
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import law_bound_plots as LB          # reference style

HERE = Path(__file__).resolve().parent
OUT = HERE / 'pde'
RES = json.loads((OUT / 'results.json').read_text())
SYSTEMS = [s for s in ('advection', 'diffusion', 'advdiff') if (OUT / ('%s.json' % s)).exists()]
TITLE = {'advection': 'Advection (exact law)', 'diffusion': 'Diffusion (exact law)',
         'advdiff': 'Advection-diffusion (approximate law)'}
FAM = {'fno': '#2a3b8f', 'rescnn': '#0b7a3a', 'mlp': '#9a9a9a'}

fig, axes = plt.subplots(1, len(SYSTEMS), figsize=(4.6 * len(SYSTEMS), 4.2), squeeze=False)
for ax, s in zip(axes[0], SYSTEMS):
    R = [r for r in json.load(open(OUT / ('%s.json' % s)))['rows'] if r.get('set') == 'confirm']
    e = np.array([r['e'] for r in R]); S = np.array([r['S_loc'] for r in R])
    fam = [r['model'].split('_')[0] for r in R]
    lim = (max(1e-4, np.percentile(e, 1) * 0.5), e.max() * 1.5)
    for f, cc in FAM.items():
        m = np.array([x == f for x in fam])
        pos = m & (S > 0)
        ax.scatter(e[pos], S[pos], s=6, color=cc, alpha=0.5, lw=0, label=f.upper() if f != 'rescnn' else 'ResCNN')
        ax.scatter(e[m & (S <= 0)], np.full((m & (S <= 0)).sum(), lim[0] * 1.15), s=4, color=cc, alpha=0.15, lw=0, marker='|')
    ax.plot(lim, lim, color='k', lw=1)
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlim(*lim); ax.set_ylim(lim[0], lim[1])
    v = RES[s + '|confirm']
    ax.set_title('%s\nvalid %.1f%%, certificate > 0 on %.0f%%' % (TITLE[s], 100 * v['valid_loc'], 100 * v['nonzero_loc']), fontsize=9)
    ax.set_xlabel('true error e (RMS)')
axes[0, 0].set_ylabel('certificate S (ticks at bottom: S = 0)')
axes[0, 0].legend(fontsize=7.5, loc='upper left', markerscale=3)
fig.suptitle('Neural PDE surrogates beyond their training range: every point below the diagonal is a valid bound',
             fontsize=10.5, y=1.03)
fig.tight_layout()
fig.savefig(OUT / 'fig_pde_scatter.png', bbox_inches='tight'); plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
x = np.arange(len(SYSTEMS)); w = 0.36
for ax, (k1, k2, title) in zip(axes, (('valid_loc', 'valid_lip', 'valid (S ≤ e)'),
                                      ('nonzero_loc', 'nonzero_lip', 'certificate > 0 (informative)'),
                                      ('rho_loc', 'rho_lip', 'rank correlation with e (12 surrogates)'))):
    ax.bar(x - w / 2, [RES[s + '|confirm'][k1] for s in SYSTEMS], w * 0.92, color='#f2c14e', edgecolor='k', label='symmetry certificate')
    ax.bar(x + w / 2, [np.nan_to_num(RES[s + '|confirm'][k2]) for s in SYSTEMS], w * 0.92, color='#9a9a9a', label='Lipschitz certificate')
    ax.set_xticks(x); ax.set_xticklabels([TITLE[s].split(' (')[0] for s in SYSTEMS], fontsize=8.5)
    ax.set_title(title, fontsize=9.5); ax.set_ylim(min(0, min(RES[s + '|confirm'][k2] for s in SYSTEMS) - 0.05), 1.05)
for xi, s in zip(x, SYSTEMS):
    axes[0].text(xi, 0.04, 'conformal\ncovers %.0f%%' % (100 * RES[s + '|confirm']['conf_cover']), ha='center', fontsize=7)
axes[1].legend(fontsize=7.5, loc='upper right')
axes[2].text(0.5, 0.92, 'Lipschitz: never > 0', transform=axes[2].transAxes, ha='center', fontsize=8)
fig.suptitle('Physics symmetry vs a generic Lipschitz law, same surrogates and test points', fontsize=10.5, y=1.03)
fig.tight_layout()
fig.savefig(OUT / 'fig_pde_compare.png', bbox_inches='tight'); plt.close(fig)
print('-> pde/fig_pde_scatter.png, fig_pde_compare.png')
