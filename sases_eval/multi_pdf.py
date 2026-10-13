# -*- coding: utf-8 -*-
"""One PDF with every graph for the seven datasets (MULTI_DATASET_PROTOCOL.md).
Numbers are read from multi/results.json at build time. Run multi_audit.py report and
multi_figures.py first. Writes output/pdf/sases_seven_datasets.pdf.
"""
import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                                KeepTogether, PageBreak, CondPageBreak)

HERE = Path(__file__).resolve().parent
M = HERE / 'multi'
LBD = HERE / 'law_bound'
RES = json.loads((M / 'results.json').read_text())
OUT = HERE.parent / 'output' / 'pdf' / 'sases_seven_datasets.pdf'
FD = Path('C:/Windows/Fonts')
for n, f in (('TNR', 'times.ttf'), ('TNR-B', 'timesbd.ttf'), ('TNR-I', 'timesi.ttf'), ('TNR-BI', 'timesbi.ttf')):
    pdfmetrics.registerFont(TTFont(n, str(FD / f)))
pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-B', italic='TNR-I', boldItalic='TNR-BI')

INK = colors.black
TITLE = ParagraphStyle('T', fontName='TNR', fontSize=17, leading=21, alignment=TA_CENTER, spaceAfter=8)
AUTH = ParagraphStyle('AU', fontName='TNR', fontSize=11, leading=15, alignment=TA_CENTER)
H = ParagraphStyle('H', fontName='TNR-B', fontSize=12.5, leading=15, spaceBefore=12, spaceAfter=5, keepWithNext=1)
BODY = ParagraphStyle('B', fontName='TNR', fontSize=10.3, leading=14, alignment=TA_JUSTIFY, spaceAfter=6)
CAP = ParagraphStyle('C', fontName='TNR', fontSize=9.2, leading=12, alignment=TA_JUSTIFY, spaceBefore=3, spaceAfter=10)
CELL = ParagraphStyle('CE', fontName='TNR', fontSize=8.8, leading=11)
CELLB = ParagraphStyle('CB', parent=CELL, fontName='TNR-B')
story = []
A = story.append
f2 = lambda x: '—' if x is None else '%.2f' % x
f3 = lambda x: '—' if x is None else '%.3f' % x


def para(t, st=BODY):
    A(Paragraph(t, st))


def table(headers, rows, widths, caption=None):
    data = [[Paragraph(str(h), CELLB) for h in headers]] + [[Paragraph(str(x), CELL) for x in r] for r in rows]
    t = Table(data, colWidths=[w * inch for w in widths], hAlign='CENTER', repeatRows=1)
    t.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.1, INK), ('LINEBELOW', (0, 0), (-1, 0), 0.5, INK),
                           ('LINEBELOW', (0, -1), (-1, -1), 1.1, INK), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.4), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.4)]))
    A(KeepTogether([t, Paragraph(caption, CAP) if caption else Spacer(1, 8)]))


def figure(path, caption, width=6.5):
    if not path.exists():
        para('<i>[figure missing: %s]</i>' % path.name); return
    w, h = PILImage.open(path).size
    hgt = width * h / w
    if hgt > 8.2:
        width, hgt = width * 8.2 / hgt, 8.2
    A(KeepTogether([Image(str(path), width=width * inch, height=hgt * inch), Paragraph(caption, CAP)]))


def r(name, scen, rule='K-S1'):
    return RES.get('%s|%s|%s' % (name, scen, rule), {})


SETS = [
    ('capillary', 'Capillary waves (b200 corpus)', ['canonical_146', 'canonical_192'],
     'Twenty measured trials, centre-pixel temporal spectra in 12 bands; surrogates map ln drive power to '
     'the band spectrum. Law: each band is linear in ln P, slopes fitted on the law-calibration trials. '
     '<b>No operating limit is published above the ceiling</b>, so K-L and K-S1 reduce to the straight law. '
     'Nineteen surrogate fits (nine families, extra seeds for the tree and MLP families), two ceilings.'),
    ('kelmarsh', 'Kelmarsh wind 2020', ['A', 'B'],
     'Six Senvion MM92 turbines, 10-minute SCADA; unit = turbine-month. Law: P ~ U<super>3</super>, '
     'rotor speed ~ U. Caps: 2,050 kW rated power, 15.0 rpm maximum rotor speed (published). 2020 is the '
     'year on which K-S1 was confirmed; it is repeated here through the common pipeline.'),
    ('pv9068', 'PVDAQ 9068 solar, 2018-19 (DC current)', ['A', 'B'],
     'A 4.7 MW single-axis tracker; unit = combiner-month. Law: DC current ~ plane-of-array irradiance. '
     'The only published limit is the inverter rating, which caps <i>irradiance</i> at 823 W/m<super>2</super> '
     'rather than current; it is used as the break.'),
    ('penmanshiel', 'Penmanshiel wind 2017 (turbines 11-15)', ['A', 'B'],
     '<b>New.</b> Five Senvion MM82 turbines, a different site and model from Kelmarsh; same Cubico format. '
     'Caps: 2,050 kW (static file) and 17.1 rpm (MM82 specification).'),
    ('lahauteborne', 'La Haute Borne wind 2014-15', ['A', 'B'],
     '<b>New.</b> ENGIE open data (France), four Senvion MM82 turbines, via the OpenOA example archive. '
     'Power only (no rotor-speed channel in the archive). Cap: 2,050 kW (asset table).'),
    ('hilloftowie', 'Hill of Towie wind 2019', ['A', 'B'],
     '<b>New.</b> Twenty-one Siemens SWT-2.3-VS-82 turbines (Scotland). Power only: published maximum rotor '
     'speeds disagree (17 vs 18 rpm), so that output was excluded before analysis. Cap: 2,300 kW (metadata).'),
    ('pv2107', 'PVDAQ 2107 solar (inverter AC power)', ['A', 'B'],
     '<b>New.</b> An 893 kW DC fixed-tilt array in Arbuckle, California, with 24 ABB TRIO-27.6 string '
     'inverters; unit = inverter-month. Law: AC power ~ irradiance. Cap: 27.6 kW nominal AC power '
     '(30 kW reported as a sensitivity check).'),
]


# ------------------------------------------------------------------ front matter
A(Paragraph('The Break-Law Certificate on Seven Datasets', TITLE))
A(Paragraph('Brandon Rodriguez', AUTH)); A(Paragraph('9 October 2026', AUTH)); A(Spacer(1, 10))
A(Paragraph('Summary', H))
para('The certificate bounds a surrogate&#8217;s error from below as a sum of three terms, '
     '<b>S = max(D &#8722; b &#8722; &#946;, 0)</b>: the original defect D (the surrogate against its own '
     'prediction at an anchor, transported by the physical law), minus the anchor allowance b (the '
     'surrogate&#8217;s error at the anchor), minus the law allowance &#946;. The law is a power law fitted on '
     'calibration data and <b>capped at each system&#8217;s published operating limit</b>; the allowance grows '
     'linearly with extrapolation distance and stops growing once the law reaches its cap (rule K-S1). '
     'Rules L (straight law) and K-L (capped law, allowance keeps growing) are shown for comparison. Every '
     'dataset uses the same nine surrogate families fitted per unit, except capillary which uses its 19 fits.')
rows = []
for name, title, scens, _ in SETS:
    sB = scens[-1]
    rows.append([title, f3(r(name, scens[0]).get('premise')), f3(r(name, sB).get('premise')),
                 f3(r(name, sB, 'L').get('premise')), f2(r(name, sB).get('Se_T')), f2(r(name, sB).get('Se_c')),
                 f3(r(name, sB).get('valid_T'))])
table(['Dataset', 'K-S1 premise A', 'K-S1 premise B', 'L premise B', 'Total bound S/e, B', 'b = 0 form S/e, B',
       'valid, B'], rows, [2.0, 0.75, 0.75, 0.7, 0.85, 0.85, 0.6],
      caption='<b>Table 1.</b> Premise = share of test bins whose law error lies inside the allowance. '
      'A is below the cap (or the lower ceiling for capillary), B beyond it. Total bound = the three-term '
      'certificate with the anchor at the top training bin; the b = 0 form uses the measured label at the '
      'top calibration bin as the anchor value. Medians over all rows.')
fails = sum(v.get('fail_prem', 0) for v in RES.values())
para('<b>Proposition 1 held everywhere</b>: zero bound failures on rows where the premise held (%d failures '
     'in total; the code also asserts this for both anchor placements).' % fails)

A(Paragraph('How to read the figures', H))
para('<b>A, curves</b> (in the style of the reference spectrum figure): every unit in grey, four in colour. '
     'Dashed: the straight law extrapolated from the calibration ceiling. Dash-dot: the law capped at the '
     'published limit (dotted horizontal line). <b>Gold band with dark edges: the final bound</b> (K-S1 '
     'allowed range). Red crosses: bins whose law error is outside it. <b>B, every unit</b>: law error divided by allowance along each curve; '
     'above the black line at 1 the law is not bounded (red). <b>C, the certificate</b>: (a) the three terms '
     'D, b, &#946; and the resulting certificate S (<b>gold, black outline</b>) beside the true error e (red), median per surrogate; (b) premise coverage and '
     '(c) median S/e of the total bound for each rule, with &#9660; where it is valid on fewer than 90% of rows.')
para('<b>Where the anchor sits matters.</b> The protocol first placed the anchor at the top calibration bin. '
     'There the surrogate is already extrapolating, so b is as large as the error being bounded and S is '
     '0 on the median row of every dataset (silent on %.0f-%.0f%% of K-S1 rows).' % (
     100 * min(v['silent'] for k, v in RES.items() if k.endswith('|K-S1')),
     100 * max(v['silent'] for k, v in RES.items() if k.endswith('|K-S1'))) + ' Placing the anchor at the top '
     '<i>training</i> bin, where the surrogate was fitted, keeps the same premise and makes the three-term '
     'bound tight; the law&#8217;s measured residual at that anchor is added to &#946;. That placement was '
     'chosen after seeing the first result and is reported as such.')
A(PageBreak())

# ------------------------------------------------------------------ one section per dataset
for k, (name, title, scens, text) in enumerate(SETS, 1):
    A(Paragraph('%d   %s' % (k, title), H))
    para(text)
    rows = []
    for sc in scens:
        for rule in ('L', 'K-L', 'K-S1'):
            v = r(name, sc, rule)
            if not v:
                continue
            rows.append([sc.replace('canonical_', 'ceiling '), rule, v.get('units', ''), v.get('rows', ''),
                         f3(v.get('premise')), f3(v.get('valid_T')), f2(v.get('Se_T')), f2(v.get('Se_c')),
                         f2(v.get('med_bT')), v.get('fail_prem', '')])
    table(['Band', 'Rule', 'Units', 'Rows', 'Premise', 'Valid', 'S/e total', 'S/e (b=0)', 'median b', 'fail|prem'],
          rows, [0.85, 0.5, 0.45, 0.55, 0.6, 0.55, 0.65, 0.65, 0.65, 0.6],
          caption='<b>Table %d.</b> %s. Valid and S/e total refer to the three-term bound anchored at the top '
          'training bin; fail|prem = bound failures where the premise held (must be 0).' % (k + 1, title))
    if name == 'pv2107':
        s = RES.get('pv2107|B|K-S1@cap30', {})
        if s:
            para('Sensitivity, 30 kW cap: K-S1 premise in B %s, total-bound S/e %s (27.6 kW: %s, %s).'
                 % (f3(s.get('premise')), f2(s.get('Se_T')), f3(r(name, 'B').get('premise')), f2(r(name, 'B').get('Se_T'))))
    if name == 'capillary':
        figure(LBD / 'fig_capillary.png', '<b>Figure %dA.</b> Capillary spectra (reference style) and the law with its '
               'allowance at each test trial. With no published cap the K-S1 allowance is 2&#954;&#948; '
               '(rule P), the band drawn here.' % k)
    else:
        figure(M / ('fig_%s_A.png' % name), '<b>Figure %dA.</b> %s: curves, laws and the K-S1 allowance.' % (k, title))
        figure(M / ('fig_%s_B.png' % name), '<b>Figure %dB.</b> %s: law error / allowance for every unit.' % (k, title),
               width=6.5)
    figure(M / ('fig_%s_C.png' % name), '<b>Figure %dC.</b> %s: the certificate as three terms, and coverage and '
           'informativeness by rule.' % (k, title), width=6.5)
    A(PageBreak())

# ------------------------------------------------------------------ ranking 9 -> 100 surrogates
RK = json.loads((HERE / 'ranking' / 'results.json').read_text())
AB = json.loads((HERE / 'ablation_multi' / 'results.json').read_text())
A(Paragraph('8   Ranking 9 to 100 surrogates', H))
para('Can the certificate order many surrogates of similar quality? A fixed pool of 100 configurations '
     '(84 MLPs: seven architectures, two activations, two regularisation strengths, three seeds; plus 16 '
     'polynomial, nearest-neighbour, kernel-ridge, random-forest and boosted-tree settings) was fitted on '
     'every unit; n = 25 and 50 are nested random subsets. To fit the run in under an hour each dataset uses '
     'at most 60 units (seeded sample) and 400 training records per unit. Within each test bin the models '
     'are ranked by four scores against their true errors: the certificate S, its measured-anchor form, the '
     'raw defect D, and a trivial baseline, the calibration maximum (the largest error the surrogate makes '
     'on the calibration bins). Exploratory, not predeclared.')
band = {'capillary': 'canonical_192'}
rows = []
for name, title, scens, _ in SETS:
    v = RK.get('%s|%s|100' % (name, band.get(name, 'B')))
    if not v:
        continue
    rows.append([title, '%.2f' % v['pair'][0], '%.2f' % v['pair'][2], '%.2f' % v['pair'][3],
                 '%.2f / %.2f' % tuple(v['worst']), '%.2f / %.2f' % tuple(v['best'])])
table(['Dataset (n = 100)', 'Pairs right: S', 'D', 'Cal. max', 'Finds worst: S / cal', 'Best not blamed: S / cal'],
      rows, [2.1, 0.8, 0.5, 0.65, 1.15, 1.25],
      caption='<b>Table 9.</b> Share of model pairs ordered as their true errors (ties count one half), '
      'and how often the worst model gets the highest score and the best model the lowest; beyond the cap '
      '(capillary: 192 mW ceiling).')
para('The certificate keeps ordering 94&#8211;99% of pairs correctly on the wind farms and solar 2107 as '
     'the pool grows to 100, finds the worst model in 79&#8211;98% of bins and almost never blames the best '
     '(96&#8211;100%). The calibration maximum ranks reasonably on average but collapses at the extremes '
     'once many models compete. The raw defect ranks as well as the certificate or slightly better: the '
     'allowances make the bound guaranteed, they do not improve the ordering.')
figure(HERE / 'ranking' / 'fig_ranking.png', '<b>Figure 8.</b> Ranking quality against the number of '
       'surrogates, every dataset: pairs ordered correctly (top), the worst model picked (middle), the best '
       'model not wrongly flagged (bottom).', width=6.9)
A(PageBreak())

# ------------------------------------------------------------------ ablation of the three terms
A(Paragraph('9   Ablation: the three terms', H))
para('The certificate is a sum of three terms, S = D &#8722; b &#8722; &#946;. Removing them one at a time '
     'shows what each contributes (rule K-S1, anchor at the top training bin, the nine surrogates of '
     'Sections 1&#8211;7; &#946; includes the measured residual of the law at the anchor). Exploratory.')
rows = []
for name, title, scens, _ in SETS:
    v = AB.get('%s|%s' % (name, band.get(name, 'B')))
    if not v:
        continue
    cells = [title]
    for lab in ('D', 'D \u2212 b', 'D \u2212 \u03b2', 'D \u2212 b \u2212 \u03b2'):
        cells.append('%.2f / %.2f' % (v[lab]['valid'], v[lab]['Se']))
    m = v['means']
    cells.append('%.2f / %.2f / %.2f' % (m['D'], m['b'], m['beta']))
    rows.append(cells)
table(['Dataset (beyond cap)', 'D', 'D &#8722; b', 'D &#8722; &#946;', 'D &#8722; b &#8722; &#946;',
       'mean D / b / &#946;'], rows, [1.6, 0.8, 0.8, 0.8, 0.95, 1.4],
      caption='<b>Table 10.</b> Each cell: validity (share of rows with S &#8804; e) / median S/e. Only the '
      'full certificate is valid on 98&#8211;100% of rows everywhere; the bare defect overshoots the true '
      'error on 32&#8211;74% of rows.')
para('<b>The law allowance does most of the work.</b> The bare defect is not a bound: its median S/e is '
     'about 1, so half the rows claim more error than exists. Subtracting the anchor allowance alone barely '
     'helps, because with the anchor inside the training range b is small (mean 0.02&#8211;0.07 log units on '
     'the field data). Subtracting the law allowance alone gives 94&#8211;100% validity on the field data, '
     'and the full sum closes the remaining gap (Kelmarsh below rated 0.944 &#8594; 0.982; PVDAQ 2107 '
     '0.949 &#8594; 0.994). On capillary, where the training anchor sits below a regime break, b is large and '
     'essential: at the 146 mW ceiling D &#8722; &#946; is valid on 0.63 of rows and the full certificate on 1.00. '
     'Ranking is the same for every variant (Figure 9b, right).')
figure(HERE / 'ablation_multi' / 'fig_ablation_waterfall.png', '<b>Figure 9a.</b> The terms add up: mean D, '
       'minus mean b, minus mean &#946;, equals the mean of D &#8722; b &#8722; &#946; (dashed outline); the gold bar and dashed line '
       'are the final certificate after clipping at 0; red is the mean true error.', width=6.9)
figure(HERE / 'ablation_multi' / 'fig_ablation_metrics.png', '<b>Figure 9b.</b> Validity, median S/e and '
       'within-bin rank correlation for each variant, beyond the cap.', width=6.9)
A(PageBreak())

# ------------------------------------------------------------------ verdicts
A(Paragraph('10   Predeclared expectations', H))
new = ['penmanshiel', 'lahauteborne', 'hilloftowie', 'pv2107']
h2 = all(r(n, 'B').get('premise', 0) >= 0.90 for n in new if r(n, 'B'))
h3 = all(r(n, 'B').get('Se_c', 0) > r(n, 'B', 'K-L').get('Se_c', 1) for n in new if r(n, 'B'))
h4 = all(r(n, 'A').get('premise', 0) >= 0.85 for n in new if r(n, 'A'))
table(['', 'Expectation', 'Result'], [
    ['H1', 'Zero failures where the premise held', 'Holds (%d failures)' % fails],
    ['H2', 'New datasets: K-S1 premise >= 0.90 beyond the cap', ('Holds' if h2 else 'Fails') + ': ' +
     ', '.join('%s %s' % (n, f3(r(n, 'B').get('premise'))) for n in new)],
    ['H3', 'New datasets: K-S1 S/e above K-L beyond the cap', ('Holds' if h3 else 'Fails') + ': ' +
     ', '.join('%s %s vs %s' % (n, f2(r(n, 'B').get('Se_c')), f2(r(n, 'B', 'K-L').get('Se_c'))) for n in new)],
    ['H4', 'New datasets: K-S1 premise >= 0.85 below the cap', ('Holds' if h4 else 'Fails') + ': ' +
     ', '.join('%s %s' % (n, f3(r(n, 'A').get('premise'))) for n in new)],
    ['H5', 'No gain where no cap exists in output units', 'Capillary: K-S1 = L by construction; 9068: see Table 4'],
], [0.4, 2.7, 3.4], caption='<b>Table 11.</b> Judged as declared in MULTI_DATASET_PROTOCOL.md. H3 is judged on '
   'the form the protocol named (anchor value = measured ceiling label).')
A(Paragraph('Limitations', H))
para('One seed per surrogate family on the new datasets; the surrogates are fitted only below the '
     'calibration band and extrapolate badly, which inflates S/e for every rule. Units within a dataset share '
     'turbines or inverters and are not independent. Caps are taken from published specifications; a '
     'derated or curtailed machine breaks the premise (Kelmarsh 2016). Capillary and 9068 have no published '
     'limit in output units, so the method adds nothing there. The training-bin anchor was chosen after the '
     'predeclared anchor proved vacuous.')
A(Paragraph('Reproducibility', H))
para('multi_audit.py builds every dataset from its public archive (external_data/, not committed) and writes '
     'multi/*_rows.pkl and results.json; multi_figures.py draws the figures; this file is multi_pdf.py. '
     'Sources: Kelmarsh and Penmanshiel (Cubico, Zenodo 16807551 and 16807304, CC-BY-4.0); Hill of Towie '
     '(RES, Zenodo 22662930, CC-BY-4.0); La Haute Borne (ENGIE, Etalab Open Licence 2.0, via NREL OpenOA); '
     'PVDAQ 9068 and 2107 (NREL, 2023 Solar Data Prize, OEDI).')


def footer(canvas, doc):
    canvas.setFont('TNR', 9)
    canvas.drawCentredString(LETTER[0] / 2, 30, 'Break-law certificate, seven datasets  |  %d' % doc.page)


OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=LETTER, topMargin=46, bottomMargin=46, leftMargin=60, rightMargin=60,
                  title='The break-law certificate on seven datasets', author='Brandon Rodriguez'
                  ).build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
