"""Figures for the per-output allowance test (perband_audit.py, PERBAND_PROTOCOL.md).

  figP1_dumbbell.png   premise coverage and median S/e, sphere vs per-output
  figP2_scatter.png    per-output S against sphere S, every row
  figP3_bands.png      capillary: the law residual per band vs each allowance
Reads perband/*.pkl only (plus the capillary corpus for figure 3). Writes perband/.
"""
import pickle
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'perband'
SPH, PB = '#2a78d6', '#eb6834'
plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['DejaVu Serif'], 'font.size': 8.5,
    'axes.linewidth': 0.8, 'xtick.direction': 'in', 'ytick.direction': 'in',
    'xtick.top': True, 'ytick.right': True, 'legend.frameon': False, 'savefig.dpi': 220,
    'mathtext.fontset': 'dejavuserif'})

CAP = pickle.load(open(OUT / 'capillary_rows.pkl', 'rb'))
WIND = {y: pickle.load(open(OUT / ('wind_rows_%d.pkl' % y), 'rb')) for y in (2016, 2017, 2018, 2019)}
DEV = WIND[2016] + WIND[2017] + WIND[2018]


def stats(rows):
    S_s = np.array([r['S_sph'] for r in rows]); S_p = np.array([r['S_pb'] for r in rows])
    e = np.array([r['e'] for r in rows])
    return dict(prem=(np.mean([r['prem_sph'] for r in rows]), np.mean([r['prem_pb'] for r in rows])),
                valid=(np.mean(S_s <= e + 1e-9), np.mean(S_p <= e + 1e-9)),
                se=(np.median(S_s / e), np.median(S_p / e)), n=len(rows))


def groups():
    out = []
    for cfg, lab in (('canonical_146', '146 mW'), ('canonical_192', '192 mW')):
        for rule in ('C', 'P'):
            out.append(('Capillary (7 representations)', 'ceiling %s, rule %s' % (lab, rule),
                        [r for r in CAP if r['config'] == cfg and r['rule'] == rule]))
    for title, rows in (('Wind 2016-18 (development)', DEV), ('Wind 2019 (confirmation, unseen)', WIND[2019])):
        for scen, sl in (('A', 'below rated'), ('B', 'rated')):
            for rule in ('C', 'P', 'E1', 'E3'):
                out.append((title, '%s, rule %s' % (sl, rule),
                            [r for r in rows if r['scen'] == scen and r['rule'] == rule]))
    return out


def fig_dumbbell(pdf):
    G = groups()
    titles = list(dict.fromkeys(g[0] for g in G))
    sizes = [sum(g[0] == t for g in G) for t in titles]
    fig, axes = plt.subplots(len(titles), 2, figsize=(10, 9.4), gridspec_kw=dict(height_ratios=sizes))
    for i, t in enumerate(titles):
        rows = [g for g in G if g[0] == t]
        ys = np.arange(len(rows))[::-1]
        for j, (key, xl) in enumerate((('prem', 'Premise held (share of rows)'), ('se', 'Median S / e'))):
            ax = axes[i, j]
            for y, (_, lab, rr) in zip(ys, rows):
                s = stats(rr)
                a, b = s[key]
                ax.plot([a, b], [y, y], color='#9a9a9a', lw=1.2, zorder=1)
                ax.plot(a, y, 'o', ms=7, color=SPH, mec='white', mew=1, zorder=3)
                ax.plot(b, y, 'o', ms=7, color=PB, mec='white', mew=1, zorder=3)
                if j == 1:
                    ax.text(1.02, y, 'valid %.2f → %.2f' % s['valid'], transform=ax.get_yaxis_transform(),
                            va='center', fontsize=7.2, color='#444444')
            ax.set_yticks(ys); ax.set_yticklabels([g[1] for g in rows] if j == 0 else [])
            ax.set_ylim(-0.7, len(rows) - 0.3)
            if key == 'prem':
                ax.set_xlim(-0.03, 1.03); ax.axvline(0.9, color='k', lw=0.7, ls=':')
            else:
                ax.set_xlim(-0.05, 1.7); ax.axvline(1.0, color='k', lw=0.7, ls=':')
            if i == len(titles) - 1:
                ax.set_xlabel(xl)
            ax.grid(axis='x', color='#e6e6e6', lw=0.5)
        axes[i, 0].set_title(t, loc='left', fontsize=9.5, fontweight='bold', pad=6)
    fig.legend([Line2D([], [], ls='', marker='o', ms=7, color=SPH), Line2D([], [], ls='', marker='o', ms=7, color=PB)],
               ['sphere allowance (current): S = max(D − b − β, 0)',
                'per-output allowance: S_j = max(D_j − b_j − β_j, 0), S = ‖S_j‖'],
               loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.01), fontsize=8.5)
    fig.suptitle('Per-output allowance: the premise breaks more often and S barely moves', fontsize=11, y=0.995)
    fig.tight_layout(rect=(0, 0.03, 0.93, 0.98), h_pad=2.4, w_pad=2.0)
    fig.savefig(OUT / 'figP1_dumbbell.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


def fig_scatter(pdf):
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.7))
    for ax, (title, rows) in zip(axes, (('Capillary, rules C and P', CAP),
                                        ('Wind 2016-18, rules C, P, E1, E3', DEV),
                                        ('Wind 2019 (confirmation)', WIND[2019]))):
        rows = [r for r in rows if not (r['abst_sph'] or r['abst_pb'])]
        S_s = np.array([r['S_sph'] for r in rows]); S_p = np.array([r['S_pb'] for r in rows])
        e = np.array([r['e'] for r in rows]); held = np.array([r['prem_pb'] for r in rows])
        x, y = S_s / e, S_p / e
        ax.scatter(x[~held], y[~held], s=4, color=PB, alpha=0.35, lw=0, label='per-output premise failed')
        ax.scatter(x[held], y[held], s=4, color=SPH, alpha=0.35, lw=0, label='per-output premise held')
        lim = max(1.8, np.percentile(np.r_[x, y], 99.5))
        ax.plot([0, lim], [0, lim], color='k', lw=0.9)
        ax.axhline(1, color='k', lw=0.6, ls=':'); ax.axvline(1, color='k', lw=0.6, ls=':')
        ax.set_xlim(0, lim); ax.set_ylim(0, lim)
        pos = S_s > 1e-12
        ax.text(0.04, 0.96, 'median per-output / sphere = %.2f\nper-output larger on %.0f%% of rows\n'
                'premise held (per-output): %.0f%%'
                % (np.median(S_p[pos] / S_s[pos]), 100 * np.mean(S_p > S_s + 1e-12), 100 * held.mean()),
                transform=ax.transAxes, va='top', fontsize=7.2)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel('Sphere S / e')
    axes[0].set_ylabel('Per-output S / e')
    axes[2].legend(loc='lower right', fontsize=7, markerscale=3)
    fig.suptitle('Row by row: the per-output certificate sits on the diagonal (no gain); '
                 'dotted lines mark S = e', fontsize=10, y=1.02)
    fig.tight_layout(w_pad=1.5)
    fig.savefig(OUT / 'figP2_scatter.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


def fig_bands(pdf):
    import multimodel_audit as M
    from perband_audit import hop_kappas, p_hops
    c = M.Corpus('ctr12')
    d0 = np.load(HERE / 'spec.npz'); fc = d0['fcent']
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9), sharey=True)
    for ax, (cfg, hi) in zip(axes, M.CONFIGS):
        lawcal = [n for n in c.names if M.LAWCAL_LO <= c.TP[n] <= hi]
        q = c.slopes(lawcal); top = max(lawcal, key=lambda n: c.TP[n])
        kP, kPv = hop_kappas(c, p_hops(c, lawcal))
        t = max(c.names, key=lambda n: c.TP[n])                     # 350 mW, the longest hop
        d = c.lp[t] - c.lp[top]
        z = np.abs(c.TM[t] - (c.TM[top] + q * d))
        ax.bar(np.arange(12), z, color='#bdbdbd', width=0.7, label='|ζ_j|  law residual (what must be covered)')
        ax.step(np.arange(13) - 0.5, np.r_[2 * kPv * d, 2 * kPv[-1] * d], where='post', color=PB, lw=1.8,
                label='β_j  per-output rule P')
        ax.step(np.arange(13) - 0.5, np.r_[np.abs(q - .5) * d, np.abs(q[-1] - .5) * d], where='post',
                color=PB, lw=1.2, ls='--', label='β_j  per-output rule C')
        ax.axhline(2 * kP * d, color=SPH, lw=1.8, label='β  sphere rule P (one radius, every band)')
        ax.axhline(np.linalg.norm(q - .5) * d, color=SPH, lw=1.2, ls='--', label='β  sphere rule C')
        miss = (z > 2 * kPv * d) | (z > np.abs(q - .5) * d)
        for j in np.where(z > 2 * kPv * d)[0]:
            ax.plot(j, z[j] + 0.25, 'v', color=PB, ms=6)
        ax.set_xticks(np.arange(12)); ax.set_xticklabels(['%.1f' % (f / 1e3) for f in fc], fontsize=7)
        ax.set_xlabel('Band centre (kHz)')
        ax.set_title('Ceiling %g mW → %g mW test (ctr12): ‖ζ‖ = %.1f, sphere β_P = %.1f'
                     % (c.TP[top], c.TP[t], np.linalg.norm(z), 2 * kP * d), fontsize=8.5)
    axes[0].set_ylabel('ln units')
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=3, fontsize=7.5, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle('Why per-band fails on capillary: β_j comes from one or two calibration hops, '
                 'and misses bands where the residual sits (▼ = band not covered by per-output P)',
                 fontsize=9.5, y=1.03)
    fig.tight_layout(w_pad=1.2)
    fig.savefig(OUT / 'figP3_bands.png', bbox_inches='tight'); pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    with PdfPages(OUT / 'perband_figures.pdf') as pdf:
        fig_dumbbell(pdf); fig_scatter(pdf); fig_bands(pdf)
    print('-> perband/figP1_dumbbell.png, figP2_scatter.png, figP3_bands.png, perband_figures.pdf')
