# -*- coding: utf-8 -*-
"""Visual summary: landscape pages, a title, big result tiles, one graph, a tiny footnote.
No paragraphs. Numbers read from the saved results. Writes output/pdf/sases_visual_summary.pdf.
"""
import json
import sys
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

HERE = Path(__file__).resolve().parent
M, CARDS = HERE / 'multi', HERE / 'eq_cards'
RES = json.loads((M / 'results.json').read_text())
RK = json.loads((HERE / 'ranking' / 'results.json').read_text())
AB = json.loads((HERE / 'ablation_multi' / 'results.json').read_text())
KS3 = json.loads((HERE / 'ks3' / 'results.json').read_text())
PDE = json.loads((HERE / 'pde' / 'results.json').read_text())
BS = json.loads((M / 'bootstrap.json').read_text())
SUMMARY = '--summary' in sys.argv            # short deck: headline slides only
OUT = HERE.parent / 'output' / 'pdf' / ('sases_summary.pdf' if SUMMARY else 'sases_visual_summary.pdf')
FD = Path('C:/Windows/Fonts')
for n, f in (('TNR', 'times.ttf'), ('TNR-B', 'timesbd.ttf'), ('TNR-I', 'timesi.ttf'), ('TNR-BI', 'timesbi.ttf')):
    pdfmetrics.registerFont(TTFont(n, str(FD / f)))
pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-B', italic='TNR-I', boldItalic='TNR-BI')

PAGE = landscape(LETTER)
W = PAGE[0] / inch - 0.9                     # usable width, inches
NAVY = colors.HexColor('#14145f'); GOLD = colors.HexColor('#f2c14e'); GOLDBG = colors.HexColor('#fdf3d8')
TITLE = ParagraphStyle('T', fontName='TNR-B', fontSize=30, leading=35, alignment=TA_CENTER, textColor=NAVY)
SUB = ParagraphStyle('S', fontName='TNR', fontSize=17, leading=21, alignment=TA_CENTER, textColor=colors.HexColor('#333333'))
H = ParagraphStyle('H', fontName='TNR-B', fontSize=24, leading=28, textColor=NAVY, spaceAfter=6)
NUM = ParagraphStyle('N', fontName='TNR-B', fontSize=26, leading=29, alignment=TA_CENTER, textColor=NAVY)
LAB = ParagraphStyle('L', fontName='TNR', fontSize=11, leading=13, alignment=TA_CENTER, textColor=colors.HexColor('#333333'))
FOOT = ParagraphStyle('F', fontName='TNR-I', fontSize=7.5, leading=9, textColor=colors.HexColor('#555555'), spaceBefore=3)
CELL = ParagraphStyle('C', fontName='TNR', fontSize=12, leading=15)
CELLB = ParagraphStyle('CB', parent=CELL, fontName='TNR-B', textColor=colors.white)
story = []
A = story.append
pc = lambda x: '—' if x is None else '%.0f%%' % (100 * x)
f2 = lambda x: '—' if x is None else '%.2f' % x


def r(name, band, rule='K-S1'):
    return RES.get('%s|%s|%s' % (name, band, rule), {})


def title(t):
    A(Paragraph(t, H))


def foot(t):
    A(Paragraph(t, FOOT))


def tiles(items, gold=None):
    """Big numbers with a small label underneath; gold marks the headline tile."""
    cells = [[Paragraph(v, NUM), Paragraph(l, LAB)] for v, l in items]
    t = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[W / len(items) * inch] * len(items))
    st = [('BOX', (i, 0), (i, 1), 0.8, NAVY) for i in range(len(items))]
    st += [('BACKGROUND', (i, 0), (i, 1), GOLDBG if i == gold else colors.HexColor('#f2f2f7')) for i in range(len(items))]
    st += [('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]
    t.setStyle(TableStyle(st)); A(t); A(Spacer(1, 8))


def table(headers, rows, widths):
    data = [[Paragraph(h, CELLB) for h in headers]] + [[Paragraph(str(x), CELL) for x in row] for row in rows]
    t = Table(data, colWidths=[w * inch for w in widths], hAlign='CENTER')
    st = [('BACKGROUND', (0, 0), (-1, 0), NAVY), ('LINEBELOW', (0, -1), (-1, -1), 1, NAVY),
          ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]
    st += [('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f2f2f7')) for i in range(2, len(data), 2)]
    t.setStyle(TableStyle(st)); A(t)


def fig(path, max_h, width=W):
    if not Path(path).exists():
        return
    w, h = PILImage.open(path).size
    hh = width * h / w
    if hh > max_h:
        width, hh = width * max_h / hh, max_h
    A(Image(str(path), width=width * inch, height=hh * inch))


def page():
    A(PageBreak())


# ---------------------------------------------------------------- cover
A(Spacer(1, 60))
A(Paragraph('Catching Bad Surrogate Models Without the Answer', TITLE)); A(Spacer(1, 10))
A(Paragraph('The anchor-symmetry error certificate · 8 datasets' + (' · summary' if SUMMARY else ''), SUB))
A(Paragraph('Brandon Rodriguez · 16 October 2026', SUB)); A(Spacer(1, 40))
tiles([('0', 'over-claims when the<br/>allowed range was right'), ('8', 'datasets<br/>(lab, 4 wind, 2 solar, PDE)'),
       ('3% → 100%', 'wind beyond rated:<br/>range right, with published limit'), ('93%', 'error proven<br/>(K-S3, unseen 2021)')], gold=3)
foot('Every rule was fixed before its confirmation data were opened. Raw data from Zenodo, OEDI and OpenOA; code at github.com/rdgbrandon/ad_model_prediction.')
page()

# ---------------------------------------------------------------- the certificate
title('The certificate: three terms')
fig(CARDS / 'certificate.png', 3.5)
fig(CARDS / ('lawallow.png' if SUMMARY else 'defect.png'), 3.0)
foot('S(x) = [D − b − β]<sub>+</sub>. If the allowances hold, the model’s true error is at least S.')
page()
if not SUMMARY:
    title('The two allowances')
    fig(CARDS / 'anchor.png', 2.9)
    fig(CARDS / 'lawallow.png', 3.5)
    foot('b: the model’s error where it was trained (measured). β: how wrong the law may be; grows with distance, frozen at the published limit.')
    page()
    title('The law: physics + the published limit')
    fig(CARDS / 'law.png', 3.2)
    fig(CARDS / 'ks3.png', 3.1)
    foot('K-S3 shrinks the allowance past the limit to the error seen on the same machines in earlier years.')
    page()

# ---------------------------------------------------------------- datasets + headline results
title('The datasets')
table(['Dataset', 'Machines', 'Units tested', 'Predicts', 'Published limit'], [
    ['Capillary waves (lab)', '1 apparatus', '20 trials', '12-band spectrum', 'none'],
    ['Kelmarsh wind', '6 turbines', '72 turbine-months / yr', 'power, rotor speed', '2,050 kW · 15 rpm'],
    ['Penmanshiel wind', '5 turbines', '60', 'power, rotor speed', '2,050 kW · 17.1 rpm'],
    ['La Haute Borne wind', '4 turbines', '93', 'power', '2,050 kW'],
    ['Hill of Towie wind', '21 turbines', '252', 'power', '2,300 kW'],
    ['Solar PVDAQ 9068', '24 combiners', '384', 'DC current', 'on sunlight only'],
    ['Solar PVDAQ 2107', '24 inverters', '1,671', 'AC power', '27.6 kW'],
    ['Neural PDE surrogates', '36 networks', '1,200 test points', 'PDE solution', 'exact symmetry'],
], [2.4, 1.4, 1.9, 1.8, 2.2])
foot('High range hidden in every dataset: models trained low, certificate computed without the hidden data, hidden data used only to check.')
page()
title('Results at a glance (beyond the published limit)')
rows = []
for name, lab, band in (('kelmarsh', 'Kelmarsh wind', 'B'), ('penmanshiel', 'Penmanshiel wind', 'B'),
                        ('hilloftowie', 'Hill of Towie wind', 'B'), ('lahauteborne', 'La Haute Borne wind', 'B'),
                        ('pv2107', 'Solar 2107', 'B'), ('pv9068', 'Solar 9068', 'B'), ('capillary', 'Capillary waves', 'canonical_192')):
    v, vL = r(name, band), r(name, band, 'L')
    rows.append([lab, pc(vL.get('premise')), pc(v.get('premise')), pc(v.get('valid_T')), f2(v.get('Se_T'))])
table(['Dataset', 'Straight law: range right', 'With limit: range right', 'Bound valid', 'Error proven'], rows,
      [2.6, 2.0, 2.0, 1.5, 1.5])
foot('Range right = the law’s true error was inside the allowance. Error proven = median share of the true error the certificate guarantees.')
page()

# ---------------------------------------------------------------- one block per dataset
DS = [('kelmarsh', 'Kelmarsh wind 2020', 'B'), ('penmanshiel', 'Penmanshiel wind 2017', 'B'),
      ('hilloftowie', 'Hill of Towie wind 2019', 'B'), ('lahauteborne', 'La Haute Borne wind 2014–15', 'B'),
      ('pv2107', 'Solar 2107 (AC power)', 'B'), ('pv9068', 'Solar 9068 (DC current)', 'B'),
      ('capillary', 'Capillary waves (lab)', 'canonical_192')]
if SUMMARY:
    title('What the allowed range looks like (Kelmarsh wind)')
    fig(M / 'fig_kelmarsh_A.png', 5.6)
    foot('Gold band = allowed range from physics + the published limit. Red × = measured point outside it. One slide per dataset in the full deck.')
    page()
    title('Only the full three-term sum is a bound')
    fig(HERE / 'ablation_multi' / 'fig_ablation_metrics.png', 5.6)
    foot('D alone is valid on 26–68% of rows; D − β on 94–100%; the full certificate D − b − β on 98–100%.')
    page()
for n, t, band in ([] if SUMMARY else DS):
    v, vL = r(n, band), r(n, band, 'L')
    rk = RK.get('%s|%s|100' % (n, band), {}); ab = AB.get('%s|%s' % (n, band), {})
    title(t)
    fig(CARDS / ('law_%s.png' % n), 1.6)
    tiles([(pc(vL.get('premise')), 'range right<br/>straight law'), (pc(v.get('premise')), 'range right<br/>with limit'),
           (pc(v.get('valid_T')), 'bound valid'), (f2(v.get('Se_T')), 'error proven'),
           (pc(rk['pair'][0]) if rk else '—', 'pairs ranked right<br/>(100 models)')], gold=3)
    if n == 'capillary':
        fig(HERE / 'law_bound' / 'fig_capillary.png', 4.05)
    else:
        fig(M / ('fig_%s_A.png' % n), 3.4)
    foot('Gold band = allowed range. Red × = point outside it. Beyond the published limit.')
    page()
    title(t + ': the certificate')
    if n != 'capillary':
        fig(M / ('fig_%s_B.png' % n), 2.1)
    fig(M / ('fig_%s_C.png' % n), 3.4 if n != 'capillary' else 4.8)
    foot('Top: law error ÷ allowance for every unit (above 1 = range wrong). Bottom: D, b, β and the certificate S (gold) per surrogate; red = true error.')
    page()
    title(t + ': ranking and ablation')
    fig(M / ('fig_%s_R.png' % n), 2.4)
    if ab:
        tiles([(pc(ab['D']['valid']), 'valid: D alone'), (pc(ab['D \u2212 b']['valid']), 'valid: D − b'),
               (pc(ab['D \u2212 \u03b2']['valid']), 'valid: D − β'), (pc(ab['D \u2212 b \u2212 \u03b2']['valid']), 'valid: full certificate')], gold=3)
    fig(M / ('fig_%s_X.png' % n), 2.2)
    foot('Ranking: certificate (gold) vs simple baseline (red), 9 → 100 models. Ablation: only the full sum is a reliable bound.')
    page()

# ---------------------------------------------------------------- K-S3
k1, k3 = KS3.get('2021|B|K-S1', {}), KS3.get('2021|B|K-S3', {})
title('Tighter past the limit: K-S3 (Kelmarsh 2021, unseen)')
tiles([('%.1f× → %.1f×' % (k1.get('beta_over_zeta', 0), k3.get('beta_over_zeta', 0)), 'allowance ÷ real law error'),
       (pc(k3.get('premise')), 'range right'), (pc(k3.get('valid')), 'bound valid'),
       ('%s → %s' % (f2(k1.get('Se')), f2(k3.get('Se'))), 'error proven')], gold=3)
fig(HERE / 'ks3' / 'fig_ks3.png', 3.7)
foot('Rule fixed on 2017–2020; 2021 downloaded afterwards. Gold = K-S3.')
page()

# ---------------------------------------------------------------- every method on every dataset
CMP_F = HERE / 'compare' / 'results.json'
if CMP_F.exists():
    import compare_figures as CF
    CMP = CF.RES
    title('Every law allowance on every dataset')
    fig(HERE / 'compare' / 'fig_heatmap.png', 6.3)
    foot('Same units, 9 surrogates, same three-term certificate; only β changes. Fleet rules use other machines in other '
         'months. Boxed = best rule with range right ≥ 95%.')
    page()
    rows = []
    for n, t, b in CF.DS:
        bb = CF.best(n, b)
        if not bb:
            continue
        v, s1 = CMP['%s|%s|%s' % (n, b, bb)], CMP.get('%s|%s|K-S1' % (n, b), CMP.get('%s|%s|P' % (n, b)))
        rows.append([t, '<b>%s</b>' % bb, pc(v['premise']), pc(v['valid']), '<b>%s</b>' % f2(v['Se']), f2(s1['Se'])])
    title('All methods: the takeaway')
    tiles([('0', 'bound failures where<br/>the range was right'), ('13', 'law allowances<br/>× 7 datasets'),
           ('K-S3', 'best when fleet history<br/>exists (0.94, 0.77)'), ('K-S1 / Z', 'best guaranteed<br/>rules otherwise')], gold=2)
    fig(HERE / 'compare' / 'fig_kelmarsh.png', 4.6)
    foot('Single-unit rules (C, P, E1, A) are unsafe beyond the limit. Fleet rules prove the most but sit at 87–97% range right.')
    page()
    title('Winner per dataset')
    table(['Dataset', 'Best safe rule', 'Range right', 'Bound valid', 'Error proven', 'K-S1 (before)'], rows,
          [2.4, 1.7, 1.5, 1.5, 1.6, 1.6])
    foot('Safe = range right ≥ 95% and bound valid ≥ 99%. Picked after seeing results (exploratory). '
         'Capillary has no published limit: last column is the paper rule P.')
    page()
    for n, t, b in ([] if SUMMARY else CF.DS):
        p = HERE / 'compare' / ('fig_%s.png' % n)
        if not p.exists():
            continue
        title('%s: all methods' % t)
        fig(p, 6.3)
        foot('Left: range right (red = unsafe). Right: error proven; gold = best safe rule.')
        page()

# ---------------------------------------------------------------- PDE
d, a = PDE.get('diffusion|confirm', {}), PDE.get('advection|confirm', {})
title('Real neural surrogates: PDE solvers')
fig(CARDS / 'law_pde.png', 1.7)
tiles([('99–100%', 'bound valid<br/>(all systems)'), (pc(d.get('Se_loc_pos')), 'error proven when it speaks<br/>(diffusion)'),
       ('0%', 'Lipschitz bound<br/>says something'), (pc(d.get('conf_cover')) + '–' + pc(a.get('conf_cover')), 'conformal covers<br/>out of range')], gold=1)
fig(HERE / 'pde' / 'fig_pde_scatter.png', 3.0)
foot('36 networks (FNO, CNN, MLP) trained in range, tested beyond it; fresh test set. Below the diagonal = valid.')
page()
if SUMMARY:
    story_mark = len(story)
title('PDE: physics symmetry vs generic Lipschitz')
fig(HERE / 'pde' / 'fig_pde_compare.png', 3.3)
table(['System', 'Valid', 'Says something', 'Error proven when > 0'], [
    [s, pc(PDE['%s|confirm' % k]['valid_loc']), pc(PDE['%s|confirm' % k]['nonzero_loc']), f2(PDE['%s|confirm' % k]['Se_loc_pos'])]
    for s, k in (('Advection', 'advection'), ('Diffusion', 'diffusion'), ('Advection–diffusion', 'advdiff'))], [3.0, 1.5, 2.0, 2.5])
foot('Localized anchor allowance (post hoc, confirmed on a fresh test set). Advection and adv.–diffusion mostly silent.')
page()

# ---------------------------------------------------------------- uncertainty + methods + verdict
title('How sure? (machines resampled)')
rows = []
for n, lab in (('kelmarsh', 'Kelmarsh'), ('penmanshiel', 'Penmanshiel'), ('hilloftowie', 'Hill of Towie'),
               ('lahauteborne', 'La Haute Borne'), ('pv2107', 'Solar 2107'), ('pv9068', 'Solar 9068')):
    v = BS.get('%s|B|K-S1' % n)
    if v:
        rows.append([lab, v['machines'], '%.1f%% [%.1f–%.1f]' % tuple(100 * x for x in v['premise']),
                     '%.1f%% [%.1f–%.1f]' % tuple(100 * x for x in v['valid']), '%.2f [%.2f–%.2f]' % tuple(v['Se'])])
table(['Dataset', 'Machines', 'Range right [95%]', 'Bound valid [95%]', 'Error proven [95%]'], rows, [2.2, 1.2, 2.3, 2.3, 2.0])
foot('Cluster bootstrap, 2,000 draws. With 4–6 machines all perfect, intervals cannot show spread: the sample is the machines.')
page()
if SUMMARY:
    del story[story_mark:]                      # summary: drop the PDE comparison and bootstrap slides
title('Which law allowance to use')
table(['Your system', 'Use', 'Result'], [
    ['Published limit + machine history', '<b>K-S3</b>', '96–99.7% right, proves 0.92–0.94 (Kelmarsh)'],
    ['Published limit + a fleet, no history', '<b>K-S3 at 95%</b>', '93–97% right, proves 0.77–0.94'],
    ['Published output limit only', '<b>K-S1</b>', '99.7–100% right, proves 0.28–0.80'],
    ['Output can only flatten, no limit', '<b>Z</b>', '96–100% right, proves 0.23–0.68'],
    ['Exact symmetry (PDE)', '<b>β = 0</b>', '99–100% valid'],
    ['Unknown bend, one system', '<b>none</b>', 'add theory, simulation or data'],
], [3.4, 2.4, 3.8])
foot('Unsafe beyond the limit: theory distance (C), short hops (P), long hops (E1), offset + slope (A). Learned fleet scales add nothing over E3/K-S3.')
page()
title('Is it publishable?')
table(['Venue', 'Ready?', 'Needs'], [
    ['Workshop (ML for physical sciences, UQ)', '<b>Yes, now</b>', '—'],
    ['Applied journal (data-centric engineering, wind energy)', '<b>Close</b>', 'one realistic wind ML model; per-site results'],
    ['Top ML conference', '<b>Not yet</b>', 'fix silent PDE cases; numeric comparison to set-membership bounds'],
], [4.2, 1.6, 3.8])
A(Spacer(1, 12))
tiles([('Strong', 'rigour: rules fixed first,<br/>unseen confirmation'), ('Modest', 'novelty: distance-to-set<br/>bound, applied'),
       ('Practical', 'win: published limits<br/>make it reliable')], gold=2)
foot('Main references: Milanese & Novara 2004 (set membership); Calliess 2016 (Lipschitz); Vovk et al. 2005 (conformal); Li et al. 2021 (FNO); Takamoto et al. 2022 (PDEBench).')


def decorate(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY); canvas.rect(0, PAGE[1] - 10, PAGE[0], 10, stroke=0, fill=1)
    canvas.setFillColor(GOLD); canvas.rect(0, 0, PAGE[0], 5, stroke=0, fill=1)
    canvas.setFont('TNR', 8.5); canvas.setFillColor(NAVY)
    canvas.drawRightString(PAGE[0] - 30, 14, '%d' % doc.page)
    canvas.restoreState()


OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=PAGE, topMargin=26, bottomMargin=24, leftMargin=32, rightMargin=32,
                  title='Catching bad surrogate models without the answer: visual summary',
                  author='Brandon Rodriguez').build(story, onFirstPage=decorate, onLaterPages=decorate)
print(OUT)
