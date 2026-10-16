"""Figures for method_compare.py. Reads compare/results.json.
  compare/fig_heatmap.png          error proven (S/e) for every rule x dataset; crossed out where range < 95% right
  compare/fig_<name>.png           per dataset: range right and error proven for every rule
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from method_compare import RULES, NAMES

HERE = Path(__file__).resolve().parent
OUT = HERE / 'compare'
RES = json.loads((OUT / 'results.json').read_text())
DS = [('kelmarsh', 'Kelmarsh', 'B'), ('penmanshiel', 'Penmanshiel', 'B'), ('hilloftowie', 'Hill of Towie', 'B'),
      ('lahauteborne', 'La Haute Borne', 'B'), ('pv2107', 'Solar 2107', 'B'), ('pv9068', 'Solar 9068', 'B'),
      ('capillary', 'Capillary', 'canonical_192')]
OK = 0.95                         # range must be right on at least this share of unit-bins
VOK = 0.99                        # and the bound valid on at least this share of rows
GOLD, EDGE, RED, GREY = '#f2c14e', '#7a5a00', '#d62728', '#9a9a9a'
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'DejaVu Serif'], 'font.size': 10})


def safe(v):
    return v['premise'] >= OK and v['valid'] >= VOK and v['abstain'] < 0.5


def best(name, band):
    """Rule with the highest error proven among safe rules (range right >= 95%, bound valid >= 99%)."""
    cand = [(RES[k]['Se'], r) for r in RULES for k in ['%s|%s|%s' % (name, band, r)]
            if k in RES and safe(RES[k])]
    return max(cand)[1] if cand else None


# ------------------------------------------------------------------ heatmap
rules = [r for r in RULES if any('%s|%s|%s' % (n, b, r) in RES for n, _, b in DS)]
M = np.full((len(rules), len(DS)), np.nan); P = np.full_like(M, np.nan); SF = np.zeros(M.shape, bool)
for j, (n, _, b) in enumerate(DS):
    for i, r in enumerate(rules):
        v = RES.get('%s|%s|%s' % (n, b, r))
        if v and v['abstain'] < 0.5:
            M[i, j], P[i, j], SF[i, j] = v['Se'], v['premise'], safe(v)
fig, ax = plt.subplots(figsize=(10.5, 0.48 * len(rules) + 1.6))
show = np.where(SF, M, np.nan)
ax.imshow(np.zeros_like(M), cmap='Greys', vmin=0, vmax=1, aspect='auto')
im = ax.imshow(show, cmap='YlOrBr', vmin=0, vmax=1, aspect='auto')
for i in range(len(rules)):
    for j, (n, _, b) in enumerate(DS):
        if np.isnan(M[i, j]):
            ax.text(j, i, 'n/a', ha='center', va='center', fontsize=8, color=GREY)
        elif not SF[i, j]:
            ax.text(j, i, '× %.1f%%' % (100 * P[i, j]), ha='center', va='center', fontsize=8, color=RED)
        else:
            ax.text(j, i, '%.2f' % M[i, j], ha='center', va='center', fontsize=9.5,
                    fontweight='bold' if rules[i] == best(n, b) else 'normal')
    ax.text(len(DS) - 0.4, i, NAMES[rules[i]], va='center', fontsize=8, color='#333333')
for j, (n, _, b) in enumerate(DS):
    bb = best(n, b)
    if bb:
        i = rules.index(bb)
        ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec='k', lw=2.2))
ax.set_xticks(range(len(DS))); ax.set_xticklabels([t for _, t, _ in DS])
ax.set_yticks(range(len(rules))); ax.set_yticklabels(rules)
ax.set_xlim(-0.5, len(DS) + 1.6)
ax.set_title('Error proven (median S/e) beyond the published limit. Boxed = best safe rule.\n'
             '× = unsafe: range right < 95% or bound valid < 99% (number shown = range right)', fontsize=9.5)
fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01, label='error proven')
fig.tight_layout(); fig.savefig(OUT / 'fig_heatmap.png', dpi=170, bbox_inches='tight'); plt.close(fig)

# ------------------------------------------------------------------ one figure per dataset
for n, t, b in DS:
    rr = [r for r in RULES if '%s|%s|%s' % (n, b, r) in RES and RES['%s|%s|%s' % (n, b, r)]['abstain'] < 0.5]
    if not rr:
        continue
    V = [RES['%s|%s|%s' % (n, b, r)] for r in rr]
    bb = best(n, b)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 0.36 * len(rr) + 1.3), sharey=True)
    y = np.arange(len(rr))[::-1]
    prem = [v['premise'] for v in V]; se = [v['Se'] for v in V]
    axes[0].barh(y, prem, color=[GREY if safe(v) else RED for v in V], height=0.7)
    axes[0].axvline(OK, color='k', lw=0.8, ls='--'); axes[0].set_xlim(0, 1.02)
    axes[0].set_title('range right (law error inside the allowance)', fontsize=9.5)
    for yi, p in zip(y, prem):
        axes[0].text(min(p, 0.98) - 0.01, yi, '%.1f%%' % (100 * p), va='center', ha='right', fontsize=8, color='white')
    cols = [GOLD if r == bb else ('#f6e3ad' if safe(v) else '#f3c6c6') for r, v in zip(rr, V)]
    axes[1].barh(y, se, color=cols, edgecolor=[EDGE if r == bb else 'none' for r in rr], lw=1.6, height=0.7)
    axes[1].set_xlim(0, max(1.05, max(se) + 0.12)); axes[1].set_title('error proven (median S/e); gold = best safe rule', fontsize=9.5)
    for yi, s in zip(y, se):
        axes[1].text(s + 0.01, yi, '%.2f' % s, va='center', fontsize=8)
    axes[0].set_yticks(y); axes[0].set_yticklabels(['%s  %s' % (r, NAMES[r]) for r in rr], fontsize=8.5)
    fig.suptitle('%s: every law allowance, same surrogates, same certificate' % t, fontsize=10.5)
    fig.tight_layout(); fig.savefig(OUT / ('fig_%s.png' % n), dpi=170, bbox_inches='tight'); plt.close(fig)
print('-> compare/fig_heatmap.png and per-dataset figures')
