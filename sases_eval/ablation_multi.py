"""Ablation of the three terms of the certificate on the seven datasets.

S = max(D - b - beta, 0), anchor at the top training bin, rule K-S1 (multi/*_rows.pkl):
  D        original defect alone
  D - b    anchor allowance only
  D - beta law allowance only (beta includes the measured anchor residual r_T)
  D - b - beta   the full certificate
For each: validity (S <= e), validity where the premise held, median S/e, silent share,
within-bin rank correlation with e. Waterfall: mean D - mean b - mean beta = mean(D - b - beta)
exactly, shown beside mean e. Exploratory (not predeclared). Writes ablation_multi/.
"""
import json
import pickle
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

import law_bound_plots as LB          # reference style

HERE = Path(__file__).resolve().parent
OUT = HERE / 'ablation_multi'
SETS = [('capillary', 'canonical_192', 'Capillary (192 mW)'), ('kelmarsh', 'B', 'Kelmarsh 2020'),
        ('penmanshiel', 'B', 'Penmanshiel 2017'), ('lahauteborne', 'B', 'La Haute Borne'),
        ('hilloftowie', 'B', 'Hill of Towie 2019'), ('pv9068', 'B', 'PVDAQ 9068'), ('pv2107', 'B', 'PVDAQ 2107')]
VARS = [('D', '#9a9a9a'), ('D − b', '#f39c12'), ('D − β', '#62c4b8'), ('D − b − β', '#2a3b8f')]


def variants(r):
    D, b, beta = r['DT'], r['bT'], r['betaT']
    return [D, max(D - b, 0.0), max(D - beta, 0.0), max(D - b - beta, 0.0)]


def main():
    OUT.mkdir(exist_ok=True)
    res = {}
    for name, band, title in SETS:
        R = pickle.load(open(HERE / 'multi' / ('%s_rows.pkl' % name), 'rb'))
        if name == 'capillary':
            R = [r for r in R if r['dataset'] == 'ctr12']
        for b_ in sorted({r['scen'] for r in R}):
            rs = [r for r in R if r['scen'] == b_ and r['rule'] == 'K-S1']
            V = np.array([variants(r) for r in rs]); e = np.array([r['e'] for r in rs])
            p = np.array([r['prem'] for r in rs])
            assert np.allclose(V[:, 3], [r['ST'] for r in rs])
            groups = {}
            for i, r in enumerate(rs):
                groups.setdefault((r['unit'], r['bin']), []).append(i)
            out = {}
            for j, (lab, _) in enumerate(VARS):
                val = V[:, j] <= e + 1e-9
                rho = [spearmanr(V[ix, j], e[ix]).correlation for ix in groups.values()
                       if len(ix) > 2 and np.ptp(V[ix, j]) > 1e-12 and np.ptp(e[ix]) > 1e-12]
                out[lab] = dict(valid=float(val.mean()), valid_prem=float(val[p].mean()) if p.any() else None,
                                Se=float(np.median(V[:, j] / e)), silent=float(np.mean(V[:, j] <= 0.01)),
                                rho=float(np.mean(rho)) if rho else None)
            out['means'] = dict(D=float(np.mean([r['DT'] for r in rs])), b=float(np.mean([r['bT'] for r in rs])),
                                beta=float(np.mean([r['betaT'] for r in rs])),
                                beta_growth=float(np.mean([r['beta'] for r in rs])),
                                rT=float(np.mean([r['rT'] for r in rs])),
                                raw=float(np.mean([r['DT'] - r['bT'] - r['betaT'] for r in rs])),
                                S=float(np.mean(V[:, 3])), e=float(e.mean()), rows=len(rs), premise=float(p.mean()))
            res['%s|%s' % (name, b_)] = out
    (OUT / 'results.json').write_text(json.dumps(res, indent=1))

    # ---- waterfall: the terms add up
    fig, axes = plt.subplots(1, 7, figsize=(17, 3.8))
    for ax, (name, band, title) in zip(axes, SETS):
        m = res['%s|%s' % (name, band)]['means']
        steps = [('D', m['D'], 0, '#9a9a9a'), ('− b', -m['b'], m['D'], '#f39c12'),
                 ('− β', -m['beta'], m['D'] - m['b'], '#62c4b8')]
        for k, (lab, h, base, cc) in enumerate(steps):
            ax.bar(k, h, bottom=base, color=cc, width=0.7)
        ax.bar(3, m['raw'], facecolor='none', edgecolor='k', linewidth=1.1, width=0.7, ls='--')
        ax.bar(4, m['S'], color='#f2c14e', width=0.7, edgecolor='k', linewidth=1.6, zorder=3)
        ax.bar(5, m['e'], color='#e0201b', width=0.7)
        ax.axhline(0, color='k', lw=0.6)
        ax.axhline(m['S'], color='k', lw=1.0, ls='--', zorder=4)
        ax.text(-0.45, m['S'], ' certificate %.2f' % m['S'], va='bottom', fontsize=7, fontweight='bold')
        ax.set_xticks(range(6)); ax.set_xticklabels(['D', '− b', '− β', '= sum', 'S final', 'e'], fontsize=7)
        ax.set_title(title, fontsize=8.5); ax.tick_params(axis='y', labelsize=7)
        ax.set_ylim(0, 1.1 * max(m['D'], m['e']))
    axes[0].set_ylabel('mean, log units')
    fig.suptitle('The three terms add up: mean D − mean b − mean β = mean (D − b − β); dashed outline = D − b − β before clipping; gold = the final certificate (clipped at 0); red = mean true error (beyond the cap)', fontsize=10, y=1.03)
    fig.tight_layout()
    fig.savefig(OUT / 'fig_ablation_waterfall.png', bbox_inches='tight'); plt.close(fig)

    # ---- metrics by variant
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.9))
    x = np.arange(len(SETS)); w = 0.2
    for ax, (key, lab) in zip(axes, (('valid', 'valid: S ≤ e'), ('Se', 'median S / e'), ('rho', 'rank ρ with e'))):
        for j, (v, cc) in enumerate(VARS):
            vals = [res['%s|%s' % (n, b)][v][key] for n, b, _ in SETS]
            ax.bar(x + (j - 1.5) * w, [np.nan if q is None else q for q in vals], w * 0.92, color=cc, label=v)
        ax.axhline(1.0 if key != 'rho' else 1.0, color='k', lw=0.6, ls=':')
        if key == 'valid':
            ax.axhline(0.9, color='k', lw=0.6, ls='--')
        ax.set_xticks(x); ax.set_xticklabels([t for _, _, t in SETS], rotation=30, ha='right', fontsize=7.5)
        ax.set_title(lab, fontsize=9); ax.set_ylim(0, 1.6 if key == 'Se' else 1.05)
    axes[0].legend(fontsize=7.5, ncol=2, loc='lower left')
    fig.suptitle('Ablation beyond the cap: which terms make it a bound', fontsize=10, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / 'fig_ablation_metrics.png', bbox_inches='tight'); plt.close(fig)

    for k, v in res.items():
        print(k, '| premise %.3f |' % v['means']['premise'],
              ' '.join('%s: valid %.3f Se %.2f rho %s' % (lab, v[lab]['valid'], v[lab]['Se'],
                                                          '%.2f' % v[lab]['rho'] if v[lab]['rho'] is not None else '-')
                       for lab, _ in VARS))


if __name__ == '__main__':
    main()
