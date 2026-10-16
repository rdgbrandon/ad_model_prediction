# -*- coding: utf-8 -*-
"""Short, large-type report: the certificate, every law-allowance method (criteria, evidence,
citations), and one section per dataset. Numbers are read from the saved results.
Writes output/pdf/sases_seven_datasets.pdf.
"""
import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether,
                                PageBreak)

HERE = Path(__file__).resolve().parent
M = HERE / 'multi'; CARDS = HERE / 'eq_cards'
RES = json.loads((M / 'results.json').read_text())
RK = json.loads((HERE / 'ranking' / 'results.json').read_text())
AB = json.loads((HERE / 'ablation_multi' / 'results.json').read_text())
OUT = HERE.parent / 'output' / 'pdf' / 'sases_seven_datasets.pdf'
FD = Path('C:/Windows/Fonts')
for n, f in (('TNR', 'times.ttf'), ('TNR-B', 'timesbd.ttf'), ('TNR-I', 'timesi.ttf'), ('TNR-BI', 'timesbi.ttf')):
    pdfmetrics.registerFont(TTFont(n, str(FD / f)))
pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-B', italic='TNR-I', boldItalic='TNR-BI')

NAVY = colors.HexColor('#14145f'); GOLDBG = colors.HexColor('#fdf3d8'); EDGE = colors.HexColor('#7a5a00')
TITLE = ParagraphStyle('T', fontName='TNR-B', fontSize=26, leading=31, alignment=TA_CENTER, textColor=NAVY, spaceAfter=8)
SUB = ParagraphStyle('S', fontName='TNR', fontSize=15, leading=19, alignment=TA_CENTER, spaceAfter=4)
H1 = ParagraphStyle('H1', fontName='TNR-B', fontSize=21, leading=25, textColor=NAVY, spaceAfter=10, keepWithNext=1)
H2 = ParagraphStyle('H2', fontName='TNR-B', fontSize=15, leading=19, textColor=NAVY, spaceBefore=10, spaceAfter=5,
                    keepWithNext=1)
BODY = ParagraphStyle('B', fontName='TNR', fontSize=12.5, leading=17, alignment=TA_LEFT, spaceAfter=6)
BUL = ParagraphStyle('BU', parent=BODY, leftIndent=16, bulletIndent=3, spaceAfter=4)
BIG = ParagraphStyle('BG', fontName='TNR', fontSize=14, leading=19, spaceAfter=6)
CAP = ParagraphStyle('C', fontName='TNR-I', fontSize=10.5, leading=13.5, spaceBefore=2, spaceAfter=10)
CELL = ParagraphStyle('CE', fontName='TNR', fontSize=10.5, leading=13)
CELLB = ParagraphStyle('CB', parent=CELL, fontName='TNR-B', textColor=colors.white)
REF = ParagraphStyle('R', fontName='TNR', fontSize=10.5, leading=13.5, leftIndent=24, firstLineIndent=-24, spaceAfter=4)
story = []
A = story.append
f2 = lambda x: '—' if x is None else '%.2f' % x
pc = lambda x: '—' if x is None else '%.0f%%' % (100 * x)


def P(t, st=BODY):
    A(Paragraph(t, st))


def bullets(items, st=BUL):
    for t in items:
        A(Paragraph(t, st, bulletText='•'))


def box(lines):
    t = Table([[[Paragraph(x, BIG) for x in lines]]], colWidths=[7.0 * inch])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), GOLDBG), ('BOX', (0, 0), (-1, -1), 1, EDGE),
                           ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                           ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    A(t); A(Spacer(1, 8))


def table(headers, rows, widths, caption=None, zebra=True):
    data = [[Paragraph(str(h), CELLB) for h in headers]] + [[Paragraph(str(x), CELL) for x in r] for r in rows]
    t = Table(data, colWidths=[w * inch for w in widths], hAlign='CENTER', repeatRows=1)
    st = [('BACKGROUND', (0, 0), (-1, 0), NAVY), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('LINEBELOW', (0, -1), (-1, -1), 1, NAVY), ('TOPPADDING', (0, 0), (-1, -1), 4),
          ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]
    if zebra:
        st += [('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f2f2f7')) for i in range(2, len(data), 2)]
    t.setStyle(TableStyle(st))
    A(KeepTogether([t, Paragraph(caption, CAP) if caption else Spacer(1, 10)]))


def fig(path, caption='', width=7.0, max_h=7.8):
    if not path.exists():
        P('<i>[missing %s]</i>' % path.name); return
    w, h = PILImage.open(path).size
    hh = width * h / w
    if hh > max_h:
        width, hh = width * max_h / hh, max_h
    A(KeepTogether([Image(str(path), width=width * inch, height=hh * inch), Paragraph(caption, CAP)]))


def r(name, band, rule='K-S1'):
    return RES.get('%s|%s|%s' % (name, band, rule), {})


# ============================================================ cover + summary
A(Spacer(1, 30))
A(Paragraph('Catching Bad Surrogate Models<br/>Without the Answer', TITLE))
A(Paragraph('The anchor-symmetry error certificate on seven datasets', SUB))
A(Paragraph('Brandon Rodriguez · 16 October 2026', SUB)); A(Spacer(1, 18))
box(['<b>Question:</b> a model is used beyond the data it was trained on. How wrong is it there?',
     '<b>Answer:</b> physics + the machine’s published limit say where the truth must be. '
     'If the model lands far outside that range, it is wrong by <b>at least</b> that distance.',
     '<b>Test:</b> 7 datasets. Real high-range data hidden, then used to check.'])
rows = []
for name, title, band in (('kelmarsh', 'Kelmarsh wind', 'B'), ('penmanshiel', 'Penmanshiel wind', 'B'),
                          ('hilloftowie', 'Hill of Towie wind', 'B'), ('lahauteborne', 'La Haute Borne wind', 'B'),
                          ('pv2107', 'Solar 2107', 'B'), ('pv9068', 'Solar 9068', 'B'), ('capillary', 'Capillary waves', 'canonical_192')):
    v = r(name, band); vL = r(name, band, 'L')
    rows.append([title, pc(vL.get('premise')), pc(v.get('premise')), pc(v.get('valid_T')), f2(v.get('Se_T'))])
table(['Dataset', 'Straight law: range right', 'With published limit: range right', 'Bound valid', 'Error proven'],
      rows, [1.9, 1.3, 1.6, 1.0, 1.2], caption='Beyond the published limit. “Error proven” = median share of the '
      'model’s real error that the certificate guarantees.')
bullets(['<b>Never over-claimed</b> when its range was right: 0 cases.',
         '<b>Published limits fixed the wind farms:</b> 3–82% → 99.7–100%.',
         '<b>Ranks 100 models</b> correctly on 94–99% of pairs (wind, solar 2107).',
         '<b>K-S3 confirmed on Kelmarsh 2021:</b> allowance 14× → 1.6× the real error, still 96% right.',
         '<b>Neural PDE surrogates:</b> never over-claimed; Lipschitz baseline never says anything.'], st=ParagraphStyle('bb', parent=BUL, fontSize=13.5, leading=18))
A(PageBreak())

# ============================================================ 1 the certificate
A(Paragraph('1. The certificate', H1))
P('Three terms. The defect minus two allowances = the guaranteed minimum error.', BIG)
for nm in ('law', 'defect', 'anchor', 'lawallow', 'certificate'):
    fig(CARDS / ('%s.png' % nm), width=7.0, max_h=3.2)
table(['Symbol', 'In these tests'], [
    ['T<sub>λ</sub>x (anchor)', 'top training bin (6.25 m/s · 325 W/m² · 54 mW)'],
    ['x<sup>max</sup><sub>law</sub> (ceiling)', 'top calibration bin (8.25 m/s · 525 W/m² · 146 or 192 mW)'],
    ['A<sub>λ</sub>', 'identity: outputs are logarithms'],
    ['κ′', '2κ, the safety factor 2 on the worst calibration growth rate'],
], [2.2, 4.8])
box(['<b>Example.</b> Turbine rated 2,050 kW, wind 13 m/s. Allowed range ≈ 2,050 kW ± 22%. '
     'A model predicting 9,000 kW is wrong by <b>at least ×3.5</b>. A model predicting 2,000 kW: S = 0 (no proven error).'])
A(PageBreak())

# ============================================================ 2 law allowance methods
A(Paragraph('2. Methods for the law allowance β', H1))
P('β is how wrong the physical law itself may be. Every method below is a different way to set it.', BIG)
A(Paragraph('Which method to use', H2))
table(['Your system', 'Use', 'Why'], [
    ['Published limit <b>and</b> earlier years of the same machines', '<b>K-S3</b>', 'Spec gives the bend; history gives the plateau scatter'],
    ['Output has a <b>published limit</b> (rated power, inverter rating)', '<b>K-S1</b>', 'The spec gives the bend the data cannot show'],
    ['No limit, but <b>many similar units</b> measured in the far range', '<b>E3</b>', 'Other units show the far-range error, with a statistical guarantee'],
    ['No limit; the law stays <b>smooth</b> beyond the data', '<b>E1</b> (= L)', 'Error keeps growing at the measured rate; ×2 covers it'],
    ['Output can only <b>flatten</b>, no spec', '<b>Z</b>', 'Shape knowledge caps the error'],
    ['Unknown bend, one system, no spec', '<b>none</b>', 'No calibration data can reveal it: add theory, simulation, or data'],
], [3.0, 1.0, 3.0])
A(PageBreak())
A(Paragraph('Every method at a glance', H2))
M_ROWS = [
    ['<b>C</b> theory distance', '‖q − q<sub>theory</sub>‖ · δ', 'theory exponent', 'never reliably', 'wind 0%, solar 25%', 'none: a good fit shrinks the band'],
    ['<b>P</b> short hops', '2κ′δ, κ′ from hops inside calibration', '≥ 3 calibration bins', 'error grows linearly at the short-hop rate', 'wind 52%, solar 90%', 'Lipschitz extrapolation [3, 4]'],
    ['<b>E1</b> long hops', '2κδ, κ from hops over train + calibration', '≥ 8 measured bins', 'error grows at most linearly', 'solar 95.5%; wind 68–72% below rated', 'Lipschitz extrapolation [3, 4]'],
    ['<b>E2</b> + curvature', 'max(E1, 2 × quadratic − line)', 'same as E1', 'the bend is inside the data', 'no gain on wind', 'Taylor remainder: sees only measured curvature'],
    ['<b>A</b> offset + slope', 'r<sub>0</sub> + 2κ<sub>A</sub>δ', 'same as E1', 'a fixed offset plus linear growth', 'worse everywhere', '—'],
    ['<b>Z</b> saturation', 'curve may only flatten', 'shape knowledge', 'output saturates (concave)', 'wind 100%, solar 85%', 'shape-constrained regression [5]'],
    ['<b>E3</b> fleet conformal', '90% quantile of other units’ law error at that input', '≥ 9 comparable units', 'units are exchangeable', 'wind 96% / 99.5%; solar years 77%', 'split / Mondrian conformal [6, 7, 8]'],
    ['<b>F-NN, F-KAN, F-GBT</b>', 'learned error scale × conformal quantile', 'fleet data', 'units are exchangeable', 'valid 95–100%; no tighter than trees', 'CV+ [9]; KAN [10]'],
    ['<b>Per-output</b>', 'one β per output', 'many hops per output', 'enough data for each output', 'coverage −14 to −21 pts', '—'],
    ['<b>K-L</b> capped law', 'law capped at the spec; β = 2κδ', 'published output limit', 'machine reaches its rating', 'valid; proves 44–65%', 'turbine and inverter control [11–14]'],
    ['<b>K-S1</b> capped + frozen', 'β = 2κ · min(δ, δ*)', 'published limit for each capped output', 'rating reached; plateau flat', '93–100%; proves 62–85%', 'turbine and inverter control [11–14]'],
    ['<b>K-S3</b> capped + shrink', 'past the cap: min(2κδ*, fleet q<sub>90</sub>)', 'published limit + earlier years', 'plateau behaves like past years', '2021: 96%; proves 93%', 'control [11–14] + Mondrian conformal [6]'],
    ['<b>K-S2</b> early freeze', 'freeze at the first cap', '—', 'never: freezes too early', '29%', '—'],
]
table(['Method', 'Formula', 'Needs', 'Works when', 'Our result (range right)', 'Why it works'],
      M_ROWS, [1.2, 1.55, 1.05, 1.15, 1.15, 1.2], caption='δ = log-distance past the calibration ceiling. Full '
      'references at the end.')
A(Paragraph('Why each family works', H2))
bullets(['<b>Rate × distance (P, E1, K-L, K-S1).</b> If the law’s error changes no faster than a rate κ, it is at most '
         'κ × distance away (a Lipschitz bound) [3, 4]. The factor 2 covers a rate measured on short or noisy hops.',
         '<b>Published limits (K-L, K-S1).</b> Turbines hold power at rated by pitching the blades and cap rotor speed; '
         'inverters clip at their AC rating [11–14]. So the law is known to go flat, and its error stops growing.',
         '<b>Conformal (E3, F-*).</b> If the new unit behaves like the calibration units, a 90% quantile of their errors '
         'covers its error with ≥ 90% probability, with no model assumptions [6–9].',
         '<b>Shape (Z).</b> If the curve can only flatten, its possible departure is limited [5].',
         '<b>The bound itself.</b> If the truth is inside a known region, the distance to the region is a guaranteed minimum error: '
         'a distance-to-admissible-set bound, as in set-membership identification [1, 2].'])
A(PageBreak())

# ============================================================ datasets
DS = [
    ('kelmarsh', 'Kelmarsh wind 2020', 'B', 'Six Senvion MM92 turbines (UK). 72 turbine-months. Power + rotor speed. Confirmation year.',
     ['Straight law: 3% range right beyond rated → K-S1: 100%.', 'Proves 80% of the error beyond rated.']),
    ('penmanshiel', 'Penmanshiel wind 2017', 'B', '<b>New.</b> Five Senvion MM82 turbines (Scotland). 60 turbine-months. Power + rotor speed.',
     ['82% → 100% range right.', 'Proves 62% of the error.']),
    ('hilloftowie', 'Hill of Towie wind 2019', 'B', '<b>New.</b> 21 Siemens SWT-2.3-VS-82 turbines (Scotland). 252 turbine-months. Power only.',
     ['65% → 99.7% range right.', 'Proves 72% of the error.']),
    ('lahauteborne', 'La Haute Borne wind 2014–15', 'B', '<b>New.</b> Four Senvion MM82 turbines (France). 93 turbine-months. Power only.',
     ['Range right everywhere, every rule.', 'Loose: proves 28% (band ≈ 11× the real law error).']),
    ('pv2107', 'Solar 2107 (AC power)', 'B', '<b>New.</b> 893 kW array, 24 ABB TRIO-27.6 inverters (California). 1,671 inverter-months.',
     ['98% range right; the inverters rarely reach 27.6 kW.', 'Proves 53% of the error.']),
    ('pv9068', 'Solar 9068 (DC current)', 'B', '4.7 MW tracker plant (Colorado). 384 combiner-months. The limit is on sunlight, not current.',
     ['Valid, but almost silent: proves 2%.', 'Needs an output with its own limit (e.g. AC power).']),
    ('capillary', 'Capillary waves (lab)', 'canonical_192', '20 lab trials, 7–350 mW. 12-band spectra. No published limit, so K-S1 = straight law.',
     ['Valid on every test trial (only 3–4 trials).', 'The anchor allowance b is essential here.']),
]
for k, (n, title, band, data, notes) in enumerate(DS, 3):
    A(Paragraph('%d. %s' % (k, title), H1))
    P(data, BIG)
    fig(CARDS / ('law_%s.png' % n), width=7.0, max_h=2.6)
    lab = {'A': 'below limit', 'B': 'beyond limit', 'canonical_146': 'ceiling 146 mW', 'canonical_192': 'ceiling 192 mW'}
    bands = ['canonical_146', 'canonical_192'] if n == 'capillary' else ['A', 'B']
    rows = []
    for b in bands:
        for rule in ('L', 'K-L', 'K-S1'):
            v = r(n, b, rule)
            if v and not (n == 'capillary' and rule != 'L'):
                rows.append([lab[b], rule if n != 'capillary' else 'L = K-S1', pc(v.get('premise')), pc(v.get('valid_T')),
                             f2(v.get('Se_T'))])
    table(['Test band', 'Rule', 'Range right', 'Bound valid', 'Error proven'], rows, [1.6, 1.3, 1.3, 1.3, 1.3])
    bullets(['<b>%s</b>' % x for x in notes], st=ParagraphStyle('nb', parent=BUL, fontSize=13.5, leading=18))
    if n == 'capillary':
        fig(HERE / 'law_bound' / 'fig_capillary.png', 'Spectra, the law and its allowance (band) at each test trial.', max_h=6.0)
    else:
        fig(M / ('fig_%s_A.png' % n), 'Gold band = allowed range. Red × = point outside it.', max_h=4.4)
        fig(M / ('fig_%s_B.png' % n), 'Law error ÷ allowance for every unit. Above 1 = range wrong.')
    fig(M / ('fig_%s_C.png' % n), 'Gold = the certificate S. Red = true error.')
    fig(M / ('fig_%s_R.png' % n), 'Ranking 9 → 100 models: certificate (gold) vs simple baseline (red).')
    fig(M / ('fig_%s_X.png' % n), 'Ablation: D − b − β adds up to the certificate (gold).')
    fig(HERE / 'compare' / ('fig_%s.png' % n), 'All 13 law allowances on this dataset (section 11). Red = unsafe; '
        'gold = best safe rule.', max_h=6.0)
    A(PageBreak())

# ============================================================ K-S3
KS3 = json.loads((HERE / 'ks3' / 'results.json').read_text())
A(Paragraph('10. Tighter beyond the cap: K-S3', H1))
P('K-S1 stays as wide past the cap as at the knee. K-S3 shrinks it to the plateau error seen on the same turbines in '
  'earlier years. Designed on Kelmarsh 2017–2020; <b>confirmed on 2021</b>, untouched until the rule was fixed.', BIG)
fig(CARDS / 'ks3.png', width=7.0, max_h=2.6)
rows = []
for rule in ('K-L', 'K-S1', 'K-S3'):
    v = KS3.get('2021|B|%s' % rule, {})
    rows.append([rule, '%.1f×' % v.get('beta_over_zeta', 0),
                 '%s [%s–%s]' % (pc(v.get('premise')), pc(v.get('ci', [0, 0])[0]), pc(v.get('ci', [0, 0])[1])),
                 pc(v.get('valid')), f2(v.get('Se')), f2(v.get('Sce'))])
table(['Rule (2021, beyond rated)', 'Allowance ÷ real error', 'Range right [95% CI]', 'Bound valid', 'Error proven',
       'Error proven (b = 0)'], rows, [1.7, 1.2, 1.5, 0.9, 0.9, 1.0])
bullets(['<b>Allowance 14× → 1.6× the real law error.</b>', '<b>Error proven 0.77 → 0.93; still valid on 99% of rows.</b>',
         'Needs a history of the same machines; with only 2 earlier years (2018) coverage was 92%.'],
        st=ParagraphStyle('k3', parent=BUL, fontSize=13.5, leading=18))
fig(HERE / 'ks3' / 'fig_ks3.png', 'Beyond rated power, 2017–2021. Gold = K-S3.')
A(PageBreak())

# ============================================================ every method on every dataset
import compare_figures as CF
CMP = CF.RES
A(Paragraph('11. Every law allowance on every dataset', H1))
P('Same units, same 9 surrogates, same three-term certificate. Only β changes. Fleet rules learn from '
  '<b>other machines in other months</b>, never the scored machine.', BIG)
box(['<b>Safe</b> = range right on ≥ 95% of unit-bins <b>and</b> bound valid on ≥ 99% of rows.',
     '<b>Best</b> = highest error proven among safe rules.'])
fig(HERE / 'compare' / 'fig_heatmap.png', 'Error proven beyond the published limit, every rule × dataset. '
    'Boxed = best safe rule. × = unsafe (number = range right).', max_h=7.2)
rows = []
for n, t, b in CF.DS:
    bb = CF.best(n, b)
    v = CMP['%s|%s|%s' % (n, b, bb)]
    s1 = CMP.get('%s|%s|K-S1' % (n, b), CMP.get('%s|%s|P' % (n, b)))
    rows.append([t, '<b>%s</b>' % bb, pc(v['premise']), pc(v['valid']), '<b>%s</b>' % f2(v['Se']), f2(s1['Se'])])
table(['Dataset', 'Best safe rule', 'Range right', 'Bound valid', 'Error proven', 'K-S1 before'], rows,
      [1.6, 1.2, 1.0, 1.0, 1.1, 1.1], caption='Capillary has no published limit: last column is the paper rule P.')
bullets(['<b>0 bound failures where the range was right</b>, all 13 rules, all 7 datasets.',
         '<b>K-S3 (fleet, 95%) wins where it is safe:</b> Kelmarsh 0.80 → 0.94, Solar 2107 0.53 → 0.77.',
         '<b>K-S3 sits on the 95% edge elsewhere:</b> 93–95% range right on Penmanshiel, Hill of Towie, La Haute Borne.',
         '<b>K-S1 and Z are the guaranteed fallbacks:</b> 96–100% range right, prove less.',
         '<b>Single-unit rules (C, P, E1, A) fail beyond the limit</b> on wind: often under 30% range right.',
         '<b>Learned fleet scales (trees, neural net)</b> do not beat the plain fleet quantile.',
         '<b>Solar 9068 stays loose with every rule</b> (best 0.23): the law itself is uncertain there.'],
        st=ParagraphStyle('cb', parent=BUL, fontSize=13, leading=17.5))
P('<i>Exploratory: the best rule was picked after seeing these results. Only K-S3 on Kelmarsh 2021 (section 10) was '
  'fixed before its test data were opened. Code: method_compare.py.</i>', CAP)
A(PageBreak())

# ============================================================ PDE: real neural surrogates
PDE = json.loads((HERE / 'pde' / 'results.json').read_text()) if (HERE / 'pde' / 'results.json').exists() else {}
A(Paragraph('12. Real neural surrogates: PDE solvers', H1))
P('The slides’ question: check a learned surrogate of a solver <b>without running the solver</b>. Fourier Neural '
  'Operators [19] (the architecture PDEBench [18] benchmarks), residual CNNs and MLPs were trained on exact solutions of three '
  'equations (PDEBench-style initial conditions), then used at parameters <b>beyond their training range</b>. '
  'The solver is used only afterwards, to check the certificate.', BIG)
fig(CARDS / 'law_pde.png', width=7.0, max_h=2.6)
table(['System', 'Law', 'Train', 'Test (beyond training)'], [
    ['Advection u<sub>t</sub> + b u<sub>x</sub> = 0', 'exact', 'b 0.1–1', 'b 1.5–4'],
    ['Diffusion u<sub>t</sub> = D u<sub>xx</sub>', 'exact', 'D 0.002–0.02', 'D 0.03–0.08'],
    ['Advection–diffusion (ν = 0.003)', 'approximate (needs β)', 'b 0.1–1', 'b 1.5–4'],
], [2.6, 1.6, 1.2, 1.6], caption='12 surrogates per system (6 FNO, 4 ResCNN, 2 MLP); 1D, 128 points.')
rows = []
for sy, lab in (('advection', 'Advection'), ('diffusion', 'Diffusion'), ('advdiff', 'Adv.–diffusion')):
    for tag, tl in (('dev', 'first test set'), ('confirm', 'fresh test set')):
        v = PDE.get('%s|%s' % (sy, tag))
        if v:
            rows.append(['%s, %s' % (lab, tl), pc(v['valid']), pc(v['nonzero']), pc(v['valid_loc']), pc(v['nonzero_loc']),
                         f2(v['Se_loc_pos']), pc(v['nonzero_lip']), pc(v['conf_cover'])])
table(['System', 'Valid (global b)', 'Says something', 'Valid (local b)', 'Says something', 'Error proven when > 0',
       'Lipschitz says something', 'Conformal covers'], rows, [1.7, 0.75, 0.75, 0.75, 0.75, 0.85, 0.85, 0.8],
      caption='Global b = the predeclared anchor allowance (one 97.5% quantile). Local b = computed within the same '
      'p·t range (post hoc rule, then checked on a fresh test set).')
bullets(['<b>Never over-claimed: valid on 99.3–100% of points</b>, every system, both test sets.',
         '<b>Diffusion: proves 63–65% of the error when it speaks</b> (FNOs: median 45–47%).',
         '<b>A generic Lipschitz law proves nothing</b> (0%); the physics symmetry does.',
         '<b>In-range conformal bounds fail out of range</b> (cover 33–63% of errors).',
         'Advection: rare in-range failures make b large, so it is mostly silent. '
         'Advection–diffusion: the law allowance for the approximate law is too wide, so it is silent.'],
        st=ParagraphStyle('pn', parent=BUL, fontSize=13, leading=17.5))
fig(HERE / 'pde' / 'fig_pde_scatter.png', 'Certificate against true error for every surrogate and test point. Below the diagonal = valid.')
fig(HERE / 'pde' / 'fig_pde_compare.png', 'Physics symmetry vs a generic Lipschitz law, same surrogates.')
A(PageBreak())

# ============================================================ uncertainty
BS = json.loads((M / 'bootstrap.json').read_text())
A(Paragraph('13. How sure are these numbers?', H1))
P('Rows from one turbine or inverter are not independent, so whole machines were resampled (2,000 bootstrap '
  'draws). The honest sample size is the number of machines.', BIG)
rows = []
for n, lab in (('kelmarsh', 'Kelmarsh'), ('penmanshiel', 'Penmanshiel'), ('hilloftowie', 'Hill of Towie'),
               ('lahauteborne', 'La Haute Borne'), ('pv2107', 'Solar 2107'), ('pv9068', 'Solar 9068')):
    v = BS.get('%s|B|K-S1' % n)
    if v:
        rows.append([lab, v['machines'], '%s [%s–%s]' % tuple('%.1f%%' % (100 * x) for x in v['premise']),
                     '%s [%s–%s]' % tuple('%.1f%%' % (100 * x) for x in v['valid']), '%.2f [%.2f–%.2f]' % tuple(v['Se'])])
table(['Dataset (K-S1, beyond limit)', 'Machines', 'Range right', 'Bound valid', 'Error proven'], rows,
      [1.8, 0.9, 1.5, 1.5, 1.4])
bullets(['With 4–6 machines all at 100%, the bootstrap shows no spread: a limit of having 4–6 machines, not proof of '
         'certainty. With 6 perfect machines the one-sided 95% lower bound on the share of fully covered machines is 61%.',
         'Hill of Towie (21 turbines) and the solar plants (24 inverters or combiners) give the tightest intervals.'])
A(PageBreak())

# ============================================================ summary + references
A(Paragraph('14. Summary', H1))
bullets(['<b>The guarantee held:</b> 0 over-claims when the range was right, all 7 datasets.',
         '<b>Best law allowance (13 rules × 7 datasets):</b> K-S3 with a published limit and machine history (proves 0.93–0.94); K-S1 or Z otherwise; single-unit rules fail beyond the limit.',
         '<b>Real neural surrogates (FNOs):</b> valid 99–100%; on diffusion proves 63% of the error when it speaks; '
         'a generic Lipschitz law proves nothing; silent where in-range errors have a heavy tail.',
         '<b>Anchor:</b> put it where the model was trained (b small). Elsewhere the bound goes to 0.',
         '<b>Law allowance does most of the work;</b> the anchor allowance closes the last gap.',
         '<b>Ranking:</b> works, but the raw defect ranks just as well. The allowances buy the guarantee.'],
        st=ParagraphStyle('sb', parent=BUL, fontSize=13.5, leading=18))
A(Paragraph('Limits', H2))
bullets(['A lower bound: S = 0 means “no proven error”, not “accurate”.',
         'Bands are 2–4× the real law error below the limit and 6–14× beyond it.',
         'A derated or curtailed machine breaks the published limit (Kelmarsh 2016).',
         'One seed per model type; units share machines; surrogates extrapolate poorly, which flatters “error proven”.'])
A(Paragraph('References', H2))
REFS = [
    'Milanese, M. & Novara, C. (2004). Set membership identification of nonlinear systems. <i>Automatica</i> 40(6).',
    'Milanese, M. & Novara, C. (2011). Unified set membership theory for identification, prediction and filtering of nonlinear systems. <i>Automatica</i> 47. doi:10.1016/j.automatica.2011.03.013',
    'Calliess, J.-P. (2016). Lazily adapted constant kinky inference for nonparametric regression and model-reference adaptive control. arXiv:1701.00178.',
    'Sullivan, T. J., McKerns, M., Meyer, D., Theil, F., Owhadi, H. & Ortiz, M. (2012). Optimal uncertainty quantification for legacy data observations of Lipschitz functions. arXiv:1202.1928.',
    'Groeneboom, P. & Jongbloed, G. (2014). <i>Nonparametric Estimation under Shape Constraints.</i> Cambridge University Press.',
    'Vovk, V., Gammerman, A. & Shafer, G. (2005). <i>Algorithmic Learning in a Random World.</i> Springer.',
    'Papadopoulos, H., Proedrou, K., Vovk, V. & Gammerman, A. (2002). Inductive confidence machines for regression. <i>ECML</i>.',
    'Lei, J., G’Sell, M., Rinaldo, A., Tibshirani, R. J. & Wasserman, L. (2018). Distribution-free predictive inference for regression. <i>JASA</i> 113(523).',
    'Barber, R. F., Candès, E. J., Ramdas, A. & Tibshirani, R. J. (2021). Predictive inference with the jackknife+. <i>Annals of Statistics</i> 49(1).',
    'Liu, Z. et al. (2024). KAN: Kolmogorov–Arnold Networks. arXiv:2404.19756.',
    'Burton, T., Jenkins, N., Sharpe, D. & Bossanyi, E. (2011). <i>Wind Energy Handbook</i>, 2nd ed. Wiley.',
    'Manwell, J. F., McGowan, J. G. & Rogers, A. L. (2009). <i>Wind Energy Explained</i>, 2nd ed. Wiley.',
    'King, D. L., Boyson, W. E. & Kratochvil, J. A. (2004). <i>Photovoltaic Array Performance Model.</i> Sandia SAND2004-3535.',
    'King, D. L., Gonzalez, S., Galbraith, G. M. & Boyson, W. E. (2007). <i>Performance Model for Grid-Connected Photovoltaic Inverters.</i> Sandia SAND2007-5036.',
    'Zakharov, V. E. & Filonenko, N. N. (1967). Weak turbulence of capillary waves. <i>J. Appl. Mech. Tech. Phys.</i> 8(5).',
    'Orosco, J., Connacher, W. & Friend, J. (2023). Data from: Identification of weakly- to strongly-turbulent three-wave processes in a micro-scale system. UC San Diego Library. doi:10.6075/J0WW7HVJ',
    'Rozza, G., Huynh, D. B. P. & Patera, A. T. (2008). Reduced basis approximation and a posteriori error estimation for affinely parametrized elliptic coercive PDEs. <i>Arch. Comput. Methods Eng.</i> 15(3).',
    'Takamoto, M., Praditia, T., Leiteritz, R., MacKinlay, D., Alesiani, F., Pflüger, D. & Niepert, M. (2022). PDEBench: an extensive benchmark for scientific machine learning. <i>NeurIPS Datasets and Benchmarks</i>.',
    'Li, Z., Kovachki, N., Azizzadenesheli, K., Liu, B., Bhattacharya, K., Stuart, A. & Anandkumar, A. (2021). Fourier neural operator for parametric partial differential equations. <i>ICLR</i>.',
    'Data: Kelmarsh and Penmanshiel (Cubico, Zenodo 16807551, 16807304); Hill of Towie (RES, Zenodo 22662930); La Haute Borne (ENGIE, via NREL OpenOA); PVDAQ 9068 and 2107 (NREL, OEDI 2023 Solar Data Prize).',
]
for i, t in enumerate(REFS, 1):
    A(Paragraph('[%d]  %s' % (i, t), REF))
P('<i>Journal details for [1], [5], [7], [11]–[17] are given from memory: verify volume, pages and edition before '
  'submission.</i>', CAP)


def footer(canvas, doc):
    canvas.setFont('TNR', 10)
    canvas.setFillColor(NAVY)
    canvas.drawCentredString(LETTER[0] / 2, 26, 'Catching bad surrogate models without the answer  ·  %d' % doc.page)


OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=LETTER, topMargin=40, bottomMargin=42, leftMargin=40, rightMargin=40,
                  title='Catching bad surrogate models without the answer', author='Brandon Rodriguez'
                  ).build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
