"""Figures for the wind / PV results report. Reads wind_pv_report/{data.npz,summary.json}
(built and gated by wind_pv_data.py) and writes wind_pv_report/fig*.png.

Colour follows the system everywhere: wind slot 1 (blue), solar slot 2 (orange),
validated against the white page with the dataviz validator.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'wind_pv_report'
D = np.load(OUT / 'data.npz')
S = json.loads((OUT / 'summary.json').read_text())

WIND, PV = '#2a78d6', '#eb6834'
INK, INK2, MUTED, GRID, AXIS = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7'
BAND = '#f0efec'
W_IN = 6.4                                    # text width of the LETTER page, inches

plt.rcParams.update({
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial', 'DejaVu Sans'],
    'font.size': 8, 'axes.titlesize': 8.5, 'axes.titleweight': 'bold',
    'axes.titlelocation': 'left', 'axes.labelsize': 8, 'axes.labelcolor': INK2,
    'axes.edgecolor': AXIS, 'axes.linewidth': 0.6, 'axes.spines.top': False,
    'axes.spines.right': False, 'axes.grid': True, 'grid.color': GRID,
    'grid.linewidth': 0.5, 'grid.linestyle': '-', 'xtick.color': MUTED,
    'ytick.color': MUTED, 'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
    'xtick.major.size': 0, 'ytick.major.size': 0, 'xtick.minor.size': 0,
    'ytick.minor.size': 0, 'legend.frameon': False, 'legend.fontsize': 7.5,
    'savefig.dpi': 300, 'figure.dpi': 100, 'lines.solid_capstyle': 'round'})


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches='tight', pad_inches=0.04, facecolor='white')
    plt.close(fig)
    print('->', OUT / name)


def band_stats(x_key, y, groups):
    """Median and IQR of y within each group, positioned at the group's median x."""
    xs, med, lo, hi = [], [], [], []
    for g in groups:
        m = x_key == g
        xs.append(g); med.append(np.median(y[m]))
        lo.append(np.percentile(y[m], 25)); hi.append(np.percentile(y[m], 75))
    return map(np.array, (xs, med, lo, hi))


# --------------------------------------------------------------- Figure 1
def fig_laws():
    """Each law against its theory exponent, relative to the LAWCAL ceiling bin."""
    ws, ps = D['wind_shape'], D['pv_shape']
    panels = [
        ('a  Wind: power', ws[:, 0], ws[:, 1], 3.0, 8.25, WIND, 'Wind speed (m/s)',
         {'TRAIN': (4.5, 6.5), 'LAWCAL': (6.5, 8.5), 'A': (8.5, 10.5), 'B': (11.5, 14.5)}),
        ('b  Wind: rotor speed', ws[:, 0], ws[:, 2], 1.0, 8.25, WIND, 'Wind speed (m/s)',
         {'TRAIN': (4.5, 6.5), 'LAWCAL': (6.5, 8.5), 'A': (8.5, 10.5), 'B': (11.5, 14.5)}),
        ('c  Solar: DC current', ps[:, 0], ps[:, 1], 1.0, 525.0, PV, 'Irradiance (W/m²)',
         {'TRAIN': (150, 350), 'LAWCAL': (350, 550), 'A': (550, 800), 'B': (900, 1100)})]
    fig, axes = plt.subplots(1, 3, figsize=(W_IN, 2.35))
    for ax, (title, x, y, q, xtop, col, xl, bands) in zip(axes, panels):
        for k, (a, b) in bands.items():
            shade = '#e9e8e3' if k in ('A', 'B') else BAND
            ax.axvspan(a, b, color=shade, lw=0, zorder=0)
        xs, med, lo, hi = band_stats(x, y, np.unique(x))
        grid = np.geomspace(xs.min(), xs.max(), 50)
        ax.plot(grid, q * np.log(grid / xtop), color=INK, lw=0.9, ls=(0, (4, 3)), zorder=2)
        ax.fill_between(xs, lo, hi, color=col, alpha=0.14, lw=0, zorder=1)
        ax.plot(xs, med, color=col, lw=2, zorder=3)
        ax.set_xscale('log')
        ax.set_title(title, color=INK)
        ax.set_xlabel(xl)
        ax.grid(axis='x', visible=False)
        ylo, yhi = ax.get_ylim()
        for k, (a, b) in bands.items():
            lab = {'TRAIN': 'train', 'LAWCAL': 'law\ncal.', 'A': 'A', 'B': 'B'}[k]
            ax.text(np.sqrt(a * b), yhi, lab, ha='center', va='top', fontsize=6.5,
                    color=INK2, linespacing=0.95)
        ax.set_ylim(ylo, yhi + 0.06 * (yhi - ylo))
    axes[0].set_ylabel('ln(value / value at ceiling bin)')
    axes[0].set_xticks([5, 7, 10, 14]); axes[0].set_xticklabels(['5', '7', '10', '14'])
    axes[1].set_xticks([5, 7, 10, 14]); axes[1].set_xticklabels(['5', '7', '10', '14'])
    axes[2].set_xticks([200, 400, 700, 1000]); axes[2].set_xticklabels(['200', '400', '700', '1000'])
    axes[2].axvline(823, color=INK2, lw=0.6)
    axes[2].text(800, axes[2].get_ylim()[0] + 0.08, 'spec-sheet\nclipping\nonset', fontsize=6.3,
                 color=INK2, ha='right', va='bottom')
    for ax in axes:
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    from matplotlib.lines import Line2D
    fig.legend([Line2D([], [], color=WIND, lw=2), Line2D([], [], color=PV, lw=2),
                Line2D([], [], color=INK, lw=0.9, ls=(0, (4, 3)))],
               ['Wind, median over turbine-months (band: IQR)',
                'Solar, median over combiner-months (band: IQR)', 'Theory exponent from the ceiling bin'],
               loc='lower center', ncol=3, bbox_to_anchor=(0.5, -0.07), fontsize=6.8,
               handlelength=1.8, columnspacing=1.2)
    fig.tight_layout(w_pad=1.0)
    save(fig, 'fig1_laws.png')


# --------------------------------------------------------------- Figure 2
def fig_growth():
    wg, pg = D['wind_growth'], D['pv_growth']
    fig, axes = plt.subplots(1, 2, figsize=(W_IN, 2.5))
    for g, col, lab in ((wg, WIND, 'Wind (bins 8.75-14.25 m/s)'),
                        (pg, PV, 'Solar (bins 575-1075 W/m²)')):
        d, z, b = g[:, 0], g[:, 1], g[:, 2]
        bins = np.unique(b)
        dx = np.array([np.median(d[b == k]) for k in bins])
        for ax, y in ((axes[0], z), (axes[1], z / d)):
            _, med, lo, hi = band_stats(b, y, bins)
            # The PV bands skip 800-900 W/m2; do not draw a line across the gap.
            seg = np.split(np.arange(len(bins)), np.where(np.diff(bins) > 1.5 * np.min(np.diff(bins)))[0] + 1)
            for i, s in enumerate(seg):
                ax.fill_between(dx[s], lo[s], hi[s], color=col, alpha=0.14, lw=0)
                ax.plot(dx[s], med[s], color=col, lw=2, label=lab if i == 0 else None)
                ax.plot(dx[s], med[s], 'o', ms=3.6, color=col, mec='white', mew=0.8)
    axes[0].set_title('a  Law residual vs extrapolation distance', color=INK)
    axes[0].set_xlabel('δ = ln(x / x at ceiling)')
    axes[0].set_ylabel('‖ζ‖, log units')
    axes[0].set_xlim(0, 0.9); axes[0].set_ylim(0, None)
    axes[1].set_title('b  Residual per unit distance, ‖ζ‖ / δ', color=INK)
    axes[1].set_xlabel('δ = ln(x / x at ceiling)')
    axes[1].set_ylabel('‖ζ‖ / δ')
    axes[1].set_xlim(0, 0.75); axes[1].set_ylim(0, None)
    # Direct labels on panel b, at the right end of each series.
    for g, col, txt in ((wg, WIND, 'wind: rises\n(super-linear)'), (pg, PV, 'solar: falls\n(sub-linear)')):
        d, z, b = g[:, 0], g[:, 1], g[:, 2]
        k = np.unique(b)[-1]
        axes[1].annotate(txt, xy=(np.median(d[b == k]), np.median((z / d)[b == k])),
                         xytext=(6, 0), textcoords='offset points', fontsize=6.8,
                         color=INK2, va='center')
    axes[1].set_xlim(0, 0.9)
    axes[0].legend(loc='upper left', fontsize=6.8, handlelength=1.6)
    fig.tight_layout(w_pad=2.0)
    save(fig, 'fig2_growth.png')


# --------------------------------------------------------------- Figure 3
WNAMES = {'C': 'C  theory distance', 'P': "P  paper Eq. 5", 'E1': "E1  long-hop κ'",
          'E2': 'E2  E1 + curvature', 'E3': 'E3  fleet conformal'}
PNAMES = {'C': 'C  theory distance', 'P': 'P  paper Eq. 5', 'E1': "E1  long-hop κ'",
          'S': 'S  spec sheet', 'E3_prev': 'E3  previous year', 'E3_loyo': 'E3  other years'}


def coverage_panel(ax, items, col, title):
    """items: (label, coverage, (lo, hi), abstain share)."""
    ys = np.arange(len(items))[::-1]
    ax.axvline(0.90, color=INK2, lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.text(0.90, len(items) - 0.45, '0.90 ', ha='right', va='bottom', fontsize=6.2, color=INK2)
    for y, (lab, v, (lo, hi), ab) in zip(ys, items):
        ax.plot([lo, hi], [y, y], color=col, lw=1.2, alpha=0.55, zorder=2)
        ax.plot(v, y, 'o', ms=5.6, color=col, mec='white', mew=1.2, zorder=3)
        note = '%.3f' % v + ('  (abstains %d%%)' % round(100 * ab) if ab > 0.005 else '')
        ax.text(1.07, y, note, va='center', ha='left', fontsize=6.6, color=INK2,
                transform=ax.get_yaxis_transform())
    ax.set_yticks(ys); ax.set_yticklabels([i[0] for i in items])
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.6, len(items) - 0.1)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xticklabels(['0', '.5', '1'])
    ax.grid(axis='y', visible=False)
    ax.set_title(title, color=INK)


def fig_coverage():
    fig, axes = plt.subplots(2, 2, figsize=(W_IN, 3.9))
    for ax, g, t in ((axes[0, 0], '2017A', 'a  Wind 2017, below rated (8.5-10.5 m/s)'),
                     (axes[0, 1], '2017B', 'b  Wind 2017, rated region (11.5-14.5 m/s)')):
        items = []
        for r in WNAMES:
            v = S['wind'][g][r]
            if r == 'E3':
                items.append((WNAMES[r], v['premise_committed'], v['premise_committed_ci'], v['abstain']))
            else:
                items.append((WNAMES[r], v['premise'], v['premise_ci'], 0.0))
        coverage_panel(ax, items, WIND, t)
    for ax, sc, t in ((axes[1, 0], 'A', 'c  Solar, below clipping (550-800 W/m²)'),
                      (axes[1, 1], 'B', 'd  Solar, above spec clipping (900-1100 W/m²)')):
        items = []
        for r in PNAMES:
            v = S['pv_label'][sc][r]
            items.append((PNAMES[r], v['premise_committed'], v['premise_committed_ci'], v['abstain']))
        coverage_panel(ax, items, PV, t)
    for ax in axes[1]:
        ax.set_xlabel('Share of test bins where β ≥ ‖ζ‖ (premise held)')
    fig.tight_layout(w_pad=6.5, h_pad=1.6)
    save(fig, 'fig3_coverage.png')


# --------------------------------------------------------------- Figure 4
def fig_theorem():
    fig, axes = plt.subplots(1, 2, figsize=(W_IN, 2.75))
    spec = (('wind', WIND, 'a  Wind 2016-17, five allowance rules', (-1.0, 0.5), (-1.6, 1.4)),
            ('pv', PV, 'b  Solar 2018-19, six allowance rules', (-0.5, 1.5), (-1.6, 0.6)))
    for ax, (sysn, col, title, xl, yl) in zip(axes, spec):
        b, z, s, e = (D['%s_%s' % (sysn, k)] for k in ('beta', 'zeta', 'S', 'e'))
        fin = np.isfinite(b)
        x = np.clip((b - z)[fin], *xl); y = np.clip((s - e)[fin], *yl)
        # Square bins with an edge exactly at 0 on both axes, so no cell straddles a
        # quadrant boundary. Premise held is beta >= zeta; failure is S > e.
        n = 40
        xe = np.unique(np.r_[np.linspace(xl[0], 0, int(n * -xl[0] / (xl[1] - xl[0])) + 1),
                             np.linspace(0, xl[1], int(n * xl[1] / (xl[1] - xl[0])) + 1)])
        ye = np.unique(np.r_[np.linspace(yl[0], 0, int(n * -yl[0] / (yl[1] - yl[0])) + 1),
                             np.linspace(0, yl[1], int(n * yl[1] / (yl[1] - yl[0])) + 1)])
        xb = np.where(np.abs((b - z)[fin]) <= 1e-10, 0.0, x)    # beta == zeta counts as held
        H, _, _ = np.histogram2d(xb, y, bins=[xe, ye])
        cmap = LinearSegmentedColormap.from_list('c', ['#ffffff', col], N=256)
        cmap.set_bad('white', 0)
        ax.add_patch(plt.Rectangle((0, 0), xl[1], yl[1], color='#fbe3e3', lw=0, zorder=0))
        Hm = np.ma.masked_where(H.T == 0, np.log10(np.maximum(H.T, 1)) + 0.4)
        ax.pcolormesh(xe, ye, Hm, cmap=cmap, vmin=0, shading='flat', zorder=2, rasterized=True)
        ax.axhline(0, color=INK2, lw=0.6, zorder=3); ax.axvline(0, color=INK2, lw=0.6, zorder=3)
        T = S[sysn + '_theorem']
        held = int(np.sum((b - z)[fin] >= -1e-10))
        bad = int(np.sum(((b - z)[fin] >= -1e-10) & ((s - e)[fin] > 1e-9)))
        assert bad == T['fails_with_premise'] == 0 and held == T['premise_held'] - (~fin).sum()
        ax.text(xl[1] * 0.97, yl[1] * 0.93, 'premise held,\nbound failed:\n%d of %s' % (bad, f'{held:,}'),
                ha='right', va='top', fontsize=6.8, color='#9b2c2c', fontweight='bold', zorder=4)
        ax.set_xlim(*xl); ax.set_ylim(*yl)
        ax.set_title(title, color=INK)
        ax.set_xlabel('β − ‖ζ‖   (> 0: premise held)')
        ax.grid(False)
    axes[0].set_ylabel('S − e   (> 0: bound failed)')
    fig.tight_layout(w_pad=2.0)
    save(fig, 'fig4_theorem.png')


# --------------------------------------------------------------- Figure 5
def price_panel(ax, res, names, col, title):
    """x = median S/e; filled dot = valid on >= 90% of rows; validity printed at right."""
    ys = np.arange(len(names))[::-1]
    ax.axvline(1.0, color=INK2, lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.text(1.0, len(names) - 0.45, ' S = e', ha='left', va='bottom', fontsize=6.2, color=INK2)
    for y, r in zip(ys, names):
        v = res[r]
        ok = v['validity'] >= 0.90
        ax.plot(v['median_S_over_e'], y, 'o', ms=5.6, mew=1.4, zorder=3,
                color=col, mfc=col if ok else 'white', mec=col)
        ax.text(1.07, y, 'valid %.3f' % v['validity'], va='center', ha='left', fontsize=6.6,
                color=INK2, transform=ax.get_yaxis_transform())
    ax.set_yticks(ys); ax.set_yticklabels([names[r] for r in names])
    ax.set_xlim(-0.08, 1.65); ax.set_ylim(-0.6, len(names) - 0.1)
    ax.set_xticks([0, 0.5, 1.0, 1.5]); ax.set_xticklabels(['0', '.5', '1', '1.5'])
    ax.grid(axis='y', visible=False)
    ax.set_title(title, color=INK)


def fig_price():
    fig, axes = plt.subplots(2, 2, figsize=(W_IN, 3.9))
    price_panel(axes[0, 0], S['wind']['2017A'], WNAMES, WIND, 'a  Wind 2017, below rated')
    price_panel(axes[0, 1], S['wind']['2017B'], WNAMES, WIND, 'b  Wind 2017, rated region')
    price_panel(axes[1, 0], S['pv_pooled']['A'], PNAMES, PV, 'c  Solar 2018-19, below clipping')
    price_panel(axes[1, 1], S['pv_pooled']['B'], PNAMES, PV, 'd  Solar 2018-19, above spec clipping')
    for ax in axes[1]:
        ax.set_xlabel('Median S / e   (share of the true error the certificate claims)')
    from matplotlib.lines import Line2D
    fig.legend([Line2D([], [], ls='', marker='o', ms=5.6, color=INK2),
                Line2D([], [], ls='', marker='o', ms=5.6, mfc='white', mec=INK2, mew=1.4)],
               ['bound valid on at least 90% of rows', 'bound valid on fewer than 90% of rows'],
               loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.045), fontsize=6.8)
    fig.tight_layout(w_pad=6.5, h_pad=1.6)
    save(fig, 'fig5_price.png')


if __name__ == '__main__':
    fig_laws(); fig_growth(); fig_coverage(); fig_theorem(); fig_price()
