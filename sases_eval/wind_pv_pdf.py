# -*- coding: utf-8 -*-
"""Wind and solar results report, styled after the week-3 evaluation.

Every number is read at build time from wind_pv_report/summary.json and data.npz,
which wind_pv_data.py rebuilds from the audit outputs and gates against the stored
aggregates. Run wind_pv_data.py, then wind_pv_figures.py, then this script.
"""
import json
from pathlib import Path

import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import reportlab.platypus.paraparser as _pp
_pp.subFraction, _pp.supFraction = 0.22, 0.38
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, KeepTogether, PageBreak)

HERE = Path(__file__).resolve().parent
REP = HERE / 'wind_pv_report'
S = json.loads((REP / 'summary.json').read_text())
D = np.load(REP / 'data.npz')
OUT = HERE.parent / 'output' / 'pdf' / 'sases_wind_solar_results.pdf'
DATE = '3 October 2026'

# Times New Roman TTF carries the Greek and the relation signs the built-in Times lacks.
FONTS = Path('C:/Windows/Fonts')
for name, f in (('TNR', 'times.ttf'), ('TNR-B', 'timesbd.ttf'), ('TNR-I', 'timesi.ttf'),
                ('TNR-BI', 'timesbi.ttf')):
    pdfmetrics.registerFont(TTFont(name, str(FONTS / f)))
for b, i, n in ((0, 0, 'TNR'), (1, 0, 'TNR-B'), (0, 1, 'TNR-I'), (1, 1, 'TNR-BI')):
    addMapping('TNR', b, i, n)

INK = colors.HexColor('#000000')
TITLE = ParagraphStyle('TITLE', fontName='TNR', fontSize=17, leading=21, alignment=TA_CENTER,
                       textColor=INK, spaceAfter=8)
AUTH = ParagraphStyle('AUTH', fontName='TNR', fontSize=11, leading=15, alignment=TA_CENTER)
H = ParagraphStyle('H', fontName='TNR-B', fontSize=12.5, leading=15, spaceBefore=14,
                   spaceAfter=6, keepWithNext=1)
H2 = ParagraphStyle('H2', fontName='TNR-B', fontSize=11, leading=14, spaceBefore=10,
                    spaceAfter=4, keepWithNext=1)
BODY = ParagraphStyle('BODY', fontName='TNR', fontSize=10.5, leading=14.6, alignment=TA_JUSTIFY,
                      spaceAfter=7)
LEFT = ParagraphStyle('LEFT', parent=BODY, alignment=0)
ABS = ParagraphStyle('ABS', parent=BODY, leftIndent=24, rightIndent=24, fontSize=10, leading=13.8)
CAP = ParagraphStyle('CAP', fontName='TNR', fontSize=9.4, leading=12.3, alignment=TA_JUSTIFY,
                     spaceBefore=3, spaceAfter=11)
CELL = ParagraphStyle('CELL', fontName='TNR', fontSize=9.1, leading=11.4)
CELLB = ParagraphStyle('CELLB', parent=CELL, fontName='TNR-B')
NUM = ParagraphStyle('NUM', parent=BODY, leftIndent=18, firstLineIndent=-12, spaceAfter=5)

story = []
A = story.append


def para(t, st=BODY):
    A(Paragraph(t, st))


def heading(t, st=H):
    A(Paragraph(t, st))


def booktabs(data, widths, align=None, bold_rows=()):
    t = Table(data, colWidths=[w * inch for w in widths], hAlign='CENTER', repeatRows=1)
    st = [('LINEABOVE', (0, 0), (-1, 0), 1.1, INK), ('LINEBELOW', (0, 0), (-1, 0), 0.5, INK),
          ('LINEBELOW', (0, -1), (-1, -1), 1.1, INK), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
          ('TOPPADDING', (0, 0), (-1, -1), 2.6), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.6),
          ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
    t.setStyle(TableStyle(st))
    return t


def tab(headers, rows, widths, align=None, bold=()):
    """align: string of l/r/c per column. bold: row indices (0-based, data rows) set in bold."""
    def c(x, j, b):
        st = ParagraphStyle('c', parent=CELLB if b else CELL,
                            alignment={'l': 0, 'c': 1, 'r': 2}[(align or 'l' * len(headers))[j]])
        return Paragraph(str(x), st)
    data = [[c(h, j, True) for j, h in enumerate(headers)]]
    data += [[c(x, j, i in bold) for j, x in enumerate(r)] for i, r in enumerate(rows)]
    return booktabs(data, widths)


def figure(png, caption, width=6.4):
    from PIL import Image as PImage
    w, h = PImage.open(REP / png).size
    return KeepTogether([Image(str(REP / png), width=width * inch, height=width * inch * h / w),
                         Paragraph(caption, CAP)])


f3 = lambda x: '%.3f' % x
f2 = lambda x: '%.2f' % x
ci = lambda c: '[%.3f, %.3f]' % tuple(c)
n0 = lambda x: f'{x:,}'

# ------------------------------------------------------------------ derived numbers
W = S['wind']; PV = S['pv']; PL = S['pv_label']; T_W, T_P = S['wind_theorem'], S['pv_theorem']
abst_w = int(np.sum(~np.isfinite(D['wind_beta']))); abst_p = int(np.sum(~np.isfinite(D['pv_beta'])))
held_w = T_W['premise_held'] - abst_w; held_p = T_P['premise_held'] - abst_p
rows_w16 = W['2016A']['C']['rows'] + W['2016B']['C']['rows']
rows_w17 = W['2017A']['C']['rows'] + W['2017B']['C']['rows']
rows_p18 = PV['2018A']['C']['rows'] + PV['2018B']['C']['rows']
rows_p19 = PV['2019A']['C']['rows'] + PV['2019B']['C']['rows']
cert_units = {y: len({r['unit'] for r in json.loads((HERE / 'pv' / ('cert_%d.json' % y))
                                                     .read_text())['rows']}) for y in (2018, 2019)}
units_w17_B = len({r['unit'] for r in json.loads((HERE / 'wind/2017/results.json').read_text())['rows']
                   if r['scenario'] == 'B'})
prim = S['wind_primary_2016']
m16C = (D['wind_year'] == 2016) & (D['wind_rule'] == 'C')
short = {sc: float(np.median(D['wind_zeta'][m16C & (D['wind_scen'] == sc)] /
                             D['wind_beta'][m16C & (D['wind_scen'] == sc)])) for sc in 'AB'}
comp = S['wind_competitors_2016']


def ratio_at(g, b):
    m = g[:, 2] == b
    return float(np.median(g[m, 1] / g[m, 0]))


wg, pg = D['wind_growth'], D['pv_growth']
w_r = {b: ratio_at(wg, b) for b in (8.75, 10.25, 14.25)}
p_r = {b: ratio_at(pg, b) for b in (575.0, 775.0, 925.0, 1075.0)}
ps = D['pv_shape']
p_shape = {b: float(np.median(ps[ps[:, 0] == b, 1])) for b in np.unique(ps[:, 0])}
p_peak_bin = max((b for b in p_shape if b >= 800), key=lambda b: p_shape[b])
sig = {r['bin']: r for r in S['pv_signed']}
prem_rows = json.loads((HERE / 'pv/premise.json').read_text())['rows']
no17 = {rule: float(np.mean([r['covered_' + rule] for r in prem_rows
                             if r['scenario'] == 'A' and r['year'] != 2017])) for rule in ('P', 'E1')}
fail_rate_w = T_W['fails_without_premise'] / T_W['premise_failed']
fail_rate_p = T_P['fails_without_premise'] / T_P['premise_failed']

# ------------------------------------------------------------------------- title
A(Paragraph('Testing SASES on Wind-Turbine and Solar Data', TITLE))
A(Paragraph('Results and figures from two physical systems independent of the capillary corpus', AUTH))
A(Spacer(1, 4))
A(Paragraph('Brandon Rodriguez', AUTH))
A(Paragraph(DATE, AUTH))
A(Spacer(1, 10))
heading('Abstract')
para('The anchor-symmetry error certificate (SASES) was run on two systems unrelated to the '
     'capillary-wave corpus it was developed on. The first is Kelmarsh wind-turbine SCADA data, '
     'with power and rotor speed as functions of wind speed: 2016 was analysed under a predeclared '
     'protocol and 2017 was held back for confirmation (%d turbine-months, %s scored rows). The '
     'second is NREL PVDAQ plant 9068, with DC current as a function of irradiance (%d '
     'combiner-months, %s scored rows). '
     '<b>Proposition 1 held wherever its premise held</b>: no bound failure in %s wind or %s '
     'solar row-rule pairs whose premise was met with a finite allowance. <b>The law allowance '
     '&#946; decides everything else.</b> The ceiling theory-distance rule, which underlies the '
     'capillary headline numbers, covered the law residual on %.0f%% of wind test bins and %.0f%% '
     'of solar bins below clipping. A long-hop rule fitted on each unit\'s own calibration labels '
     'covered %.1f%% on solar but at most %.0f%% on wind, where the rotor-speed limit and the rated '
     'plateau lie outside the calibration band. A fleet-calibrated conformal allowance covered '
     '%.1f%% and %.1f%% on the untouched 2017 wind year. Valid allowances cost informativeness: on '
     'solar the certificate claims a median %.0f&#8211;%.0f%% of the true error. The evidence '
     'supports a narrower claim than &#8220;the bound holds every time&#8221;: the bound is as '
     'reliable as its allowance, and calibration data alone size the allowance correctly only '
     'when no regime change lies between the calibration band and the test point.'
     % (S['wind_units']['2016'] + S['wind_units']['2017'], n0(rows_w16 + rows_w17), S['pv_units'],
        n0(rows_p18 + rows_p19), n0(held_w), n0(held_p), 100 * W['2017A']['C']['premise'],
        100 * PL['A']['C']['premise'], 100 * PL['A']['E1']['premise'], 100 * W['2017A']['E1']['premise'],
        100 * W['2017A']['E3']['premise_committed'], 100 * W['2017B']['E3']['premise_committed'],
        100 * PV['2018A']['E1']['median_S_over_e'], 100 * PV['2019A']['E1']['median_S_over_e']), ABS)

heading('Summary of results', H2)
A(tab(['Result', 'Wind (Kelmarsh)', 'Solar (PVDAQ 9068)'], [
    ['Bound failures where the premise held', '0 of %s' % n0(held_w), '0 of %s' % n0(held_p)],
    ['Bound failures where the premise failed', '%s of %s (%.0f%%)' % (
        n0(T_W['fails_without_premise']), n0(T_W['premise_failed']), 100 * fail_rate_w),
     '%s of %s (%.0f%%)' % (n0(T_P['fails_without_premise']), n0(T_P['premise_failed']), 100 * fail_rate_p)],
    ['Premise coverage, ceiling rule C', '%s below rated, %s rated (2017)' % (
        f3(W['2017A']['C']['premise']), f3(W['2017B']['C']['premise'])),
     '%s below, %s above clipping' % (f3(PL['A']['C']['premise']), f3(PL['B']['C']['premise']))],
    ['Premise coverage, paper Eq. 5 (P)', '%s / %s' % (f3(W['2017A']['P']['premise']), f3(W['2017B']['P']['premise'])),
     '%s / %s' % (f3(PL['A']['P']['premise']), f3(PL['B']['P']['premise']))],
    ['Premise coverage, long-hop rule E1', '%s / %s' % (f3(W['2017A']['E1']['premise']), f3(W['2017B']['E1']['premise'])),
     '%s / %s' % (f3(PL['A']['E1']['premise']), f3(PL['B']['E1']['premise']))],
    ['Premise coverage, fleet conformal E3 (committed bins)',
     '%s / %s' % (f3(W['2017A']['E3']['premise_committed']), f3(W['2017B']['E3']['premise_committed'])),
     '%s / %s (previous year)' % (f3(PL['A']['E3_prev']['premise_committed']), f3(PL['B']['E3_prev']['premise_committed']))],
    ['Median S/e under the best valid rule, below the break', '%s (E3)' % f2(W['2017A']['E3']['median_S_over_e']),
     '%s&#8211;%s (E1, 2018&#8211;19)' % (f2(PV['2018A']['E1']['median_S_over_e']), f2(PV['2019A']['E1']['median_S_over_e']))],
], [2.45, 2.0, 1.95], 'lrr'))
A(Spacer(1, 3))
para('Pairs of entries are below / above the regime break (wind: 8.5&#8211;10.5 and 11.5&#8211;14.5 '
     'm/s; solar: 550&#8211;800 and 900&#8211;1,100 W/m&#178;). Solar coverage is the label-only '
     'analysis over all years. Row-rule pairs overlap and are not independent trials (Section 9).', CAP)

# --------------------------------------------------------------------- section 1
heading('1   The certificate and what was tested')
para('Each test point is a bin of the control variable (wind speed or irradiance) above a '
     'law-calibration band (LAWCAL). In log units the law predicts the bin mean y(x) from the '
     'top calibration bin: the certificate centre is c(x) = y<sub>top</sub> + q&#183;&#948;, where '
     'q is the law exponent fitted on LAWCAL and &#948; = ln(x/x<sub>top</sub>) is the '
     'extrapolation distance. For a surrogate prediction f(x), the raw defect is D = &#8214;f(x) '
     '&#8722; c(x)&#8214;, the certificate is S = max(D &#8722; &#946;, 0), and the true error is '
     'e = &#8214;f(x) &#8722; y(x)&#8214;. The law residual is &#950; = y(x) &#8722; c(x). If the '
     'premise &#8214;&#950;&#8214; &#8804; &#946; holds, the triangle inequality gives S &#8804; e '
     '(Proposition 1, ceiling form: the centre is labelled, so no anchor-error term b enters). '
     'The theorem is unconditional given its premise; the premise is carried entirely by the '
     'allowance &#946;. Table 1 lists the allowance rules tested.')
A(tab(['Rule', 'Allowance &#946;', 'Information used', 'Status'], [
    ['C', '&#8214;q<sub>cal</sub> &#8722; q<sub>th</sub>&#8214;&#183;&#948;', 'LAWCAL slope and theory exponent',
     'Behind every capillary headline number'],
    ['P', '2&#954;&#8242;<sub>short</sub>&#183;&#948;', 'LAWCAL labels, leave-the-top-out hops', 'The paper\'s Eq. 5'],
    ['E1', '2&#954;&#8242;<sub>long</sub>&#183;&#948;', 'TRAIN and LAWCAL labels, hops from every 4-bin window to every higher bin',
     'Designed after the 2016 wind failure'],
    ['E2', 'max(E1, 2&#183;quadratic departure)', 'Quadratic fit over TRAIN and LAWCAL', 'Wind only'],
    ['S', 'E1 + 2&#183;max(0, ln(G/G<sub>clip</sub>))', 'Spec sheet: G<sub>clip</sub> = 823 W/m&#178;', 'Solar only'],
    ['E3', 'Split-conformal 90% quantile of &#8214;&#950;&#8214; at the same bin; &#8734; if fewer than 9 units',
     'Labelled residuals from other units', 'Wind: other turbine-months (2016), all 2016 units (2017). '
     'Solar: previous year; all other years (added)'],
], [0.42, 1.75, 2.15, 2.08], 'llll'))
para('Table 1. Allowance rules. &#954;&#8242; is the largest observed ratio &#8214;&#950;&#8214;/&#948; '
     'over held-out calibration hops; the factor 2 is the paper\'s declared margin. E3 abstains '
     '(&#946; = &#8734;, S = 0) where too few comparable units reach the bin.', CAP)

# --------------------------------------------------------------------- section 2
heading('2   Data and design')
para('Table 2 summarises the two systems, and Figure 1 shows each law as measured. '
     'Both were chosen because each side of the law is measured by a separate instrument, '
     'so the law is not built into the data.')
A(tab(['', 'Wind', 'Solar'], [
    ['Source', 'Kelmarsh wind farm: 6 Senvion MM92 turbines, 10-min SCADA (Zenodo 16807551, CC-BY-4.0)',
     'NREL PVDAQ 9068, Kersey CO: 4.7 MW single-axis tracker, CdTe, 24 DC combiners, 5-min (OEDI)'],
    ['Law', 'ln P = 3 ln U and ln &#969; = 1 ln U', 'ln I = 1 ln G (current and irradiance from separate instruments)'],
    ['Unit', 'One turbine-month', 'One combiner-month'],
    ['Bins', '0.5 m/s, at least 6 records', '50 W/m&#178;, at least 6 records'],
    ['TRAIN / LAWCAL', '4.5&#8211;6.5 / 6.5&#8211;8.5 m/s', '150&#8211;350 / 350&#8211;550 W/m&#178;'],
    ['Test A / B', '8.5&#8211;10.5 (below rated) / 11.5&#8211;14.5 m/s (rated)',
     '550&#8211;800 (below clipping) / 900&#8211;1,100 W/m&#178; (above spec clipping)'],
    ['Units', '%d (2016, May&#8211;Dec), %d (2017)' % (S['wind_units']['2016'], S['wind_units']['2017']),
     '%d label-only (2017&#8211;2023); %d (2018) and %d (2019) scored' % (S['pv_units'], cert_units[2018], cert_units[2019])],
    ['Scored rows', '%s (2016) + %s (2017)' % (n0(rows_w16), n0(rows_w17)),
     '%s (2018) + %s (2019)' % (n0(rows_p18), n0(rows_p19))],
    ['Surrogates', 'Nine families (linear, cubic, kNN, kernel ridge, random forest, boosted trees, three MLPs), seed 0, fitted per unit on TRAIN', 'Same nine'],
    ['Protocols', 'WIND_PROTOCOL.md (2016), WIND_ADDENDUM.md (rule P, post hoc), ALLOWANCE_PROTOCOL.md (E1&#8211;E3; confirmed on 2017)',
     'PV_PROTOCOL.md, written before the data were opened; PV_DEVIATIONS.md'],
], [1.0, 2.7, 2.7], 'lll'))
para('Table 2. The two systems. Every unit is a self-contained replication: its own surrogates, '
     'its own law fit and its own test bins.', CAP)
A(figure('fig1_laws.png',
         '<b>Figure 1.</b> Each law against its theory exponent. Curves are medians over units of '
         'the bin-mean output relative to the top LAWCAL bin (8.25 m/s; 525 W/m&#178;); bands are '
         'interquartile ranges; dashed lines have the theory slopes 3, 1 and 1. Wind pools 2016 and '
         '2017 (%d turbine-months); solar pools all %d combiner-months. The rotor reaches its speed '
         'limit near 9 m/s, inside test band A; power plateaus at rated output, inside band B. '
         'Median solar current relative to the ceiling peaks at %.2f near %d W/m&#178; and falls to '
         '%.2f at 1,075 W/m&#178;: clipping arrives close to the spec-sheet onset.'
         % (S['wind_units']['2016'] + S['wind_units']['2017'], S['pv_units'], p_shape[p_peak_bin],
            p_peak_bin, p_shape[1075.0])))
para('The fitted LAWCAL exponents sit close to theory on both systems: median (q<sub>P</sub>, '
     'q<sub>&#969;</sub>) = (%.2f, %.2f) on wind 2016 and (%.2f, %.2f) on 2017 against (3, 1); median '
     'q = %.2f on solar (interquartile range %.2f&#8211;%.2f) against 1. This matters for rule C, '
     'whose rate is the distance between the two.'
     % (*S['wind_q_2016'], *S['wind_q_2017'], S['pv_q']['median'], S['pv_q']['q25'], S['pv_q']['q75']))

# --------------------------------------------------------------------- section 3
heading('3   Proposition 1 held on both systems')
para('On the capillary corpus the premise never failed, so the conditional guarantee was never '
     'at risk. Here it failed often, and the bound then failed on %.0f%% (wind) and %.0f%% (solar) '
     'of those pairs, so the guarantee was genuinely at stake (Table 3, Figure 2).'
     % (100 * fail_rate_w, 100 * fail_rate_p))
A(tab(['', 'Row-rule pairs', 'Premise held (finite &#946;)', 'Bound failed | premise held',
       'Premise failed', 'Bound failed | premise failed', 'Abstained (&#946; = &#8734;)'], [
    ['Wind 2016&#8211;17, 5 rules', n0(T_W['pairs']), n0(held_w), '<b>0</b>', n0(T_W['premise_failed']),
     '%s (%.0f%%)' % (n0(T_W['fails_without_premise']), 100 * fail_rate_w), n0(abst_w)],
    ['Solar 2018&#8211;19, 6 rules', n0(T_P['pairs']), n0(held_p), '<b>0</b>', n0(T_P['premise_failed']),
     '%s (%.0f%%)' % (n0(T_P['fails_without_premise']), 100 * fail_rate_p), n0(abst_p)],
], [1.3, 0.8, 0.95, 0.85, 0.8, 0.95, 0.75], 'lrrrrrr'))
para('Table 3. Premise against bound, every row under every rule. The same row appears once per '
     'rule, and rows share units, turbines, combiners and months, so the counts are not independent '
     'trials; they show that no row contradicts the theorem, not a coverage rate.', CAP)
A(figure('fig4_theorem.png',
         '<b>Figure 2.</b> Every row-rule pair placed by its premise margin &#946; &#8722; '
         '&#8214;&#950;&#8214; (positive: premise held) and S &#8722; e (positive: bound failed). '
         'Shading is log count per cell; cell edges lie exactly on zero, so no cell straddles a '
         'quadrant. Axes are clipped and points beyond are drawn at the edge. E3 abstentions are '
         'omitted (%s wind, %s solar). Proposition 1 forbids the shaded quadrant, and it is empty. '
         'The diagonal ridge S &#8722; e = &#8722;(&#946; &#8722; &#8214;&#950;&#8214;) collects rows on which '
         'the triangle inequality is tight (the truth lies between the certificate centre and the '
         'prediction): there the bound is sharp, and any shortfall in &#946; becomes a bound '
         'failure of the same size.' % (n0(abst_w), n0(abst_p))))

# --------------------------------------------------------------------- section 4
heading('4   The allowance decides the outcome')
heading('4.1   The predeclared wind run failed', H2)
para('The predeclared 2016 analysis used the consensus certificate with the ceiling theory-distance '
     'radius, the construction behind the capillary headline figures (931/931 and 399/399).')
A(tab(['Scenario', 'Units', 'Rows', 'Premise held', 'Bound held', 'Units valid on every row [95% CI]', 'Median S/e'], [
    ['A, below rated', prim['A']['units'], n0(prim['A']['rows']), f3(prim['A']['premise']), f3(prim['A']['validity']),
     '%d/%d %s' % (prim['A']['units_all_valid'], prim['A']['units'], ci(prim['A']['units_ci'])), f2(prim['A']['median_S_over_e'])],
    ['B, rated', prim['B']['units'], n0(prim['B']['rows']), f3(prim['B']['premise']), f3(prim['B']['validity']),
     '%d/%d %s' % (prim['B']['units_all_valid'], prim['B']['units'], ci(prim['B']['units_ci'])), f2(prim['B']['median_S_over_e'])],
], [1.05, 0.5, 0.55, 0.8, 0.75, 1.75, 0.75], 'lrrrrrr'))
para('Table 4. Predeclared wind result, 2016 (wind/results.json). Median S/e above 1 means the '
     'median row is not a lower bound.', CAP)
para('The premise held on no row. From labels alone, the median ratio of the law residual to the '
     'radius was %.1f below rated and %.1f in the rated region (median radius %.3f against median '
     'residual %.3f, and %.3f against %.3f). The rate &#8214;q<sub>cal</sub> &#8722; '
     'q<sub>th</sub>&#8214; measures how far the fitted exponent sits from theory, not how far the '
     'system departs from the law. On wind the two exponents nearly agree, so the radius collapses; '
     'on the capillary corpus the fitted slopes (1 to 7) were far from the Kibble&#8211;Zurek value '
     '0.5, which made the radius large by accident. <b>The capillary 100%% validity is a property of '
     'that corpus and that rate, not of the method.</b>'
     % (short['A'], short['B'], S['wind_shortfall_2016']['A']['radius_median'],
        S['wind_shortfall_2016']['A']['zeta_median'], S['wind_shortfall_2016']['B']['radius_median'],
        S['wind_shortfall_2016']['B']['zeta_median']))

heading('4.2   Expanding the allowance on wind: confirmed on 2017', H2)
para('Rules E1&#8211;E3 were designed after the 2016 residuals had been seen, so 2016 is development '
     'only. They were fixed in ALLOWANCE_PROTOCOL.md and confirmed on Kelmarsh 2017, a year not '
     'opened until then, through the unchanged pipeline. Table 5 gives 2017, with 2016 in parentheses.')
rows = []
for r, lab in (('C', 'C  theory distance'), ('P', 'P  paper Eq. 5'), ('E1', 'E1  long-hop &#954;&#8242;'),
               ('E2', 'E2  E1 + curvature'), ('E3', 'E3  fleet conformal')):
    a, b = W['2017A'][r], W['2017B'][r]
    a6, b6 = W['2016A'][r], W['2016B'][r]
    pa = a['premise_committed'] if r == 'E3' else a['premise']
    pb = b['premise_committed'] if r == 'E3' else b['premise']
    pa6 = a6['premise_committed'] if r == 'E3' else a6['premise']
    pb6 = b6['premise_committed'] if r == 'E3' else b6['premise']
    cia = a['premise_committed_ci'] if r == 'E3' else a['premise_ci']
    rows.append([lab, '%s (%s)' % (f3(pa), f3(pa6)), ci(cia), f3(a['validity']), f2(a['median_S_over_e']),
                 '%s (%s)' % (f3(pb), f3(pb6)), f3(b['validity']), f2(b['median_S_over_e']),
                 '%.0f%%' % (100 * b['abstain'])])
A(tab(['Rule', 'A: premise', 'A: 95% CI', 'A: valid', 'A: S/e', 'B: premise', 'B: valid', 'B: S/e', 'B: abstain'],
      rows, [1.25, 0.85, 0.95, 0.5, 0.45, 0.85, 0.5, 0.45, 0.6], 'lrrrrrrrr', bold=(4,)))
para('Table 5. Wind allowance ladder, 2017 confirmation year (2016 development in parentheses). '
     'Premise is the share of unit-bins (%d below rated, %d rated) whose residual &#946; covered; '
     'for E3 it is over committed bins only (%d of %d rated bins in 2017). Valid is the share of '
     'rows with S &#8804; e. S/e is the median.'
     % (W['2017A']['C']['unit_bins'], W['2017B']['C']['unit_bins'], W['2017B']['E3']['committed_bins'],
        W['2017B']['E3']['unit_bins']), CAP)
para('Calibration labels alone could not rescue the bound. E1 measures the law\'s error over hops '
     'as long as those at test and lifts coverage by %.0f points over P, but it tops out at %.0f%%, '
     'and the curvature term adds nothing: the dominant failure is the rotor reaching its speed '
     'limit near 9 m/s, a kink absent from the 4.5&#8211;8.5 m/s calibration data. Across the rated '
     'break no calibration-only rule covers more than %.0f%%, because a plateau cannot be '
     'extrapolated from below it. E3, which learns the residual at each bin from other units, '
     'covered %.1f%% below rated and %.1f%% of committed rated bins, with validity %.3f and %.3f. '
     'It spends a resource the method was meant not to need: labelled outcomes in the extrapolation '
     'range, gathered on comparable units.'
     % (100 * (W['2017A']['E1']['premise'] - W['2017A']['P']['premise']), 100 * W['2017A']['E1']['premise'],
        100 * max(W['2017B'][r]['premise'] for r in ('P', 'E1', 'E2')),
        100 * W['2017A']['E3']['premise_committed'], 100 * W['2017B']['E3']['premise_committed'],
        W['2017A']['E3']['validity'], W['2017B']['E3']['validity']))

heading('4.3   Solar: a calibration-only allowance worked below clipping', H2)
rows = []
for r, lab in (('C', 'C  theory distance'), ('P', 'P  paper Eq. 5'), ('E1', 'E1  long-hop &#954;&#8242;'),
               ('S', 'S  spec sheet'), ('E3_prev', 'E3  previous year'), ('E3_loyo', 'E3  other years (added)')):
    a, b = PL['A'][r], PL['B'][r]
    rows.append([lab, f3(a['premise_committed']), ci(a['premise_committed_ci']), f2(a['beta_over_zeta']),
                 '%.0f%%' % (100 * a['abstain']), f3(b['premise_committed']), ci(b['premise_committed_ci']),
                 '%.0f%%' % (100 * b['abstain'])])
A(tab(['Rule', 'A: premise', 'A: 95% CI', 'A: &#946;/&#8214;&#950;&#8214;', 'A: abstain', 'B: premise', 'B: 95% CI', 'B: abstain'],
      rows, [1.45, 0.65, 0.95, 0.65, 0.55, 0.65, 0.95, 0.55], 'lrrrrrrr', bold=(2,)))
para('Table 6. Solar premise coverage, label-only, %d combiner-months (%s unit-bins below clipping, '
     '%s above). Coverage for E3 is over committed bins; &#946;/&#8214;&#950;&#8214; is the median '
     'ratio over finite allowances.'
     % (S['pv_units'], n0(PL['A']['unit_bins']), n0(PL['B']['unit_bins'])), CAP)
para('Below clipping E1 covered %.1f%% of unit-bins and at least 90%% on all %d combiners (lowest '
     '%.3f). The paper\'s rule P reached %.3f, with a confidence interval that includes 0.90. Rule C '
     'failed for the third time in three systems (%.3f), as its mechanism predicts: the fitted slope '
     'sits near 1, so its rate collapses. That failure is structural. The fleet rule is weaker '
     'here than on wind because consecutive years of one plant are not exchangeable (soiling, '
     'degradation, sensor changes): in the 2019 scored units, the previous-year pool covered only '
     '%.3f. Figure 3 sets the two systems side by side.'
     % (100 * PL['A']['E1']['premise'], PL['A']['E1']['combiners'], PL['A']['E1']['combiner_min'],
        PL['A']['P']['premise'], PL['A']['C']['premise'], PV['2019A']['E3_prev']['premise']))
A(figure('fig3_coverage.png',
         '<b>Figure 3.</b> Premise coverage by allowance rule, with 95% Clopper&#8211;Pearson '
         'intervals at the unit-bin level. Wind panels are the 2017 confirmation year; solar panels '
         'are the label-only analysis over all years. E3 coverage is over committed bins, with the '
         'abstention share printed beside it. The dashed line is the 90% target.'))

# --------------------------------------------------------------------- section 5
heading('5   Why the same rule worked on solar and failed on wind')
para('A rate learned on calibration hops transfers to the test range when the law residual per unit '
     'distance, &#8214;&#950;&#8214;/&#948;, does not rise between the two. Figure 4 shows it '
     'directly. On wind the median ratio rises from %.2f at 8.75 m/s to %.2f at 10.25 m/s and %.2f at '
     '14.25 m/s, with little spread between units: the departure is systematic and lies beyond every '
     'calibration hop. On solar it falls across band A, from %.2f at 575 W/m&#178; to %.2f at 775 '
     'W/m&#178;. The capillary corpus sits between: the proposal (&#167;6.5) reports &#950; &#8776; '
     '11.0&#948; &#8722; 0.48, close to linear, with a calibration-fitted rate biased 10&#8211;15%% '
     'low. It is not plotted because it uses the anchor form, whose &#950; is not comparable.'
     % (w_r[8.75], w_r[10.25], w_r[14.25], p_r[575.0], p_r[775.0]))
A(figure('fig2_growth.png',
         '<b>Figure 4.</b> (a) Law residual against extrapolation distance and (b) residual per unit '
         'distance, medians per bin with interquartile bands. Wind: every bin above the ceiling, '
         '2016&#8211;17. Solar: the test bins of bands A and B (the 800&#8211;900 W/m&#178; gap is '
         'not a test band).'))
para('<b>The falling ratio on solar is not evidence of a clean law.</b> Table 7 gives the signed '
     'residual, the bin mean minus the extrapolated calibration line. Its median grows from %+.3f at '
     '575 W/m&#178; to %+.3f at 775 W/m&#178;: current rises faster than proportionally, and per unit '
     'distance the systematic part grows from %.2f to %.2f, faster than linearly, as on wind. What '
     'dominates &#8214;&#950;&#8214; at short distance is month-to-month scatter (interquartile '
     'range %.3f wide at 575 W/m&#178;), which also dominates the short calibration hops that E1 '
     'learns from. E1 covers band A because a scatter-inflated rate, doubled, exceeds the systematic '
     'departure there. The operative condition is therefore about the total residual a rule must '
     'cover. On solar it held across band A with margin supplied by scatter; it need not hold over '
     'a longer extrapolation.'
     % (sig[575.0]['signed'], sig[775.0]['signed'], sig[575.0]['signed'] / sig[575.0]['delta'],
        sig[775.0]['signed'] / sig[775.0]['delta'], sig[575.0]['q75'] - sig[575.0]['q25']))
A(tab(['Bin (W/m&#178;)', 'Unit-bins', 'Median &#948;', 'Median signed residual', 'Interquartile range',
       'Share above line', 'Median &#8214;&#950;&#8214;'],
      [['%.0f' % r['bin'], r['n'], f3(r['delta']), '%+.3f' % r['signed'],
        '[%+.3f, %+.3f]' % (r['q25'], r['q75']), f2(r['above']), f3(r['abs_median'])] for r in S['pv_signed']],
      [0.85, 0.7, 0.75, 1.1, 1.25, 0.85, 0.85], 'rrrrrrr'))
para('Table 7. Solar signed law residual by irradiance bin, all %d combiner-months (log units; '
     '0.01 is a 1%% departure of current from the extrapolated line). Bins of 825 and 875 W/m&#178; '
     'lie between the test bands.' % S['pv_units'], CAP)
para('<b>Band B is not a clean-law test, and the earlier explanation of it was wrong.</b> The signed '
     'residual peaks at %+.3f near 825 W/m&#178;, crosses zero near 975 W/m&#178; and reaches %+.3f at '
     '1,075 W/m&#178;. Clipping arrives near the spec-sheet onset and pulls the current back across '
     'the extrapolated line, as the protocol anticipated (a power-limited inverter raises voltage, '
     'which lowers current). The over-rise below clipping and the clipping above it partly cancel, '
     'so the band-B residual is moderate (median %.3f) and rules P and E1 over-cover it (%.3f and '
     '%.3f). This corrects pv/FINDINGS.md, which attributed the failure of hypothesis H3 to a late '
     'clipping onset caused by hot cells. The coverage figures are unchanged; only their explanation is.'
     % (sig[825.0]['signed'], sig[1075.0]['signed'], PL['B']['zeta_median'], PL['B']['P']['premise'],
        PL['B']['E1']['premise']))

# --------------------------------------------------------------------- section 6
heading('6   Validity costs informativeness')
para('S/e is the share of the true error the certificate claims. It must be read beside validity: '
     'a rule that does not cover the law residual returns large S/e precisely because it '
     'subtracts too little. Table 8 and Figure 5 show the trade on both systems.')
para('Under E1 the solar certificate is valid on %.1f%% (2019) and %.1f%% (2018) of rows below '
     'clipping and claims a median %.0f%% and %.0f%% of the error, staying silent on about %.0f%% of '
     'rows. The roughly 70%% that the capillary deck quotes came from rule C, which is not a valid '
     'allowance. On wind, E3 is valid on %.1f%% of rows below rated and claims a median %.0f%% of the '
     'error, but only because these surrogates extrapolate badly: their median error is %.2f log units '
     '(a factor of about %.1f in power), and beside an error that large the law\'s own error is small. '
     'An accurate surrogate would mostly receive a silent certificate.'
     % (100 * PV['2019A']['E1']['validity'], 100 * PV['2018A']['E1']['validity'],
        100 * PV['2019A']['E1']['median_S_over_e'], 100 * PV['2018A']['E1']['median_S_over_e'],
        100 * np.mean([PV['2019A']['E1']['silent'], PV['2018A']['E1']['silent']]),
        100 * W['2017A']['E3']['validity'], 100 * W['2017A']['E3']['median_S_over_e'],
        W['2017A']['E3']['median_e'], np.exp(W['2017A']['E3']['median_e'])))

rows = []
for r, lab in (('C', 'C'), ('P', 'P'), ('E1', 'E1'), ('S', 'S'), ('E3_prev', 'E3 previous year'),
               ('E3_loyo', 'E3 other years')):
    rows.append([lab] + ['%s / %s / %s' % (f3(PV[g][r]['validity']), f2(PV[g][r]['median_S_over_e']),
                                           f2(PV[g][r]['silent'])) for g in ('2019A', '2018A', '2019B', '2018B')])
_t8 = (tab(['Rule', '2019, below clipping', '2018, below clipping', '2019, above', '2018, above'], rows,
      [1.3, 1.3, 1.3, 1.25, 1.25], 'lrrrr', bold=(2,)))
A(KeepTogether([_t8, Paragraph('Table 8. Solar full certificate: validity / median S/e / silent share (S &#8804; 0.01) per year '
     'and band. 2019 was the declared scoring year (%d units); 2018 was added because 2019 proved '
     'sparse (%d units).' % (cert_units[2019], cert_units[2018]), CAP)]))
A(figure('fig5_price.png',
         '<b>Figure 5.</b> Median S/e by allowance rule. Filled markers: bound valid on at least 90%% '
         'of rows; open markers: fewer. Validity is printed beside each row. Wind: 2017. Solar: 2018 '
         'and 2019 pooled (%s rows). Rules that look most informative are the invalid ones.'
         % n0(rows_p18 + rows_p19)))
# --------------------------------------------------------------------- section 7
heading('7   Simple baselines on wind')
labels = (('sases', 'SASES consensus (predeclared)'), ('sample_max_heuristic', 'Calibration maximum'),
          ('raw_defect', 'Raw defect'), ('ols_error_heuristic', 'OLS error predictor'))
A(tab(['Method', 'A: below e', 'A: median score/e', 'A: rank &#961;', 'B: below e', 'B: rank &#961;'],
      [[lab, f3(comp['A'][k]['below_e']), f2(comp['A'][k]['median_score_over_e']), f3(comp['A'][k]['rank_rho']),
        f3(comp['B'][k]['below_e']), f3(comp['B'][k]['rank_rho'])] for k, lab in labels],
      [2.0, 0.8, 1.05, 0.8, 0.8, 0.8], 'lrrrrr'))
para('Table 9. Wind 2016, every method read as a lower bound. Rank &#961; is the mean Spearman '
     'correlation with the true error across the nine surrogates within each unit-bin.', CAP)
para('The largest surrogate error seen on the calibration bins sat below the true error on %.1f%% '
     'of rows below rated, beating SASES under the predeclared rule in every paired comparison '
     '(wind/report.txt). It is not a certificate: it is below the error here only because surrogate '
     'error grows with distance on wind, and on the capillary corpus, where it did not grow, it '
     'failed (kernel ridge). The raw defect, which claims nothing, ranks surrogates as well as the '
     'certificate (&#961; = %.3f against %.3f): the ranking power comes from the defect, not from '
     'the allowance. Both baselines belong in every comparison.'
     % (100 * comp['A']['sample_max_heuristic']['below_e'], comp['A']['raw_defect']['rank_rho'],
        comp['A']['sases']['rank_rho']))

# --------------------------------------------------------------------- section 8
heading('8   Verdicts on the predeclared hypotheses')
A(tab(['', 'Expectation', 'Result'], [
    ['Wind H1', 'Bound holds where the premise holds; premise holds on most units',
     '<b>Fails.</b> Premise held on no row (rule C)'],
    ['Wind H2', 'Premise fails in B; the bound fails only where the premise failed',
     'Vacuous as declared (premise never held); supported under rule P: 0 failures in %s premise-held rows'
     % n0(W['2016A']['P']['premise_rows'] + W['2016B']['P']['premise_rows'])],
    ['Wind H3', 'SASES beats every competitor below rated', '<b>Fails.</b> Calibration maximum wins everywhere'],
    ['Wind H4', 'Positive rank correlation below rated', 'Holds (&#961; = %.3f), no better than the raw defect'
     % comp['A']['sases']['rank_rho']],
    ['Allowance A1', 'Zero failures where the premise held, every rule', 'Holds, both years'],
    ['Allowance A2', 'E1, E2 beat P below rated, stay under 0.90', 'Holds: %s &#8594; %s / %s'
     % (f3(W['2017A']['P']['premise']), f3(W['2017A']['E1']['premise']), f3(W['2017A']['E2']['premise']))],
    ['Allowance A3', 'Neither E1 nor E2 covers the rated region', 'Holds (%s)' % f3(W['2017B']['E1']['premise'])],
    ['Allowance A4', 'E3 reaches 0.90 in both scenarios', 'Holds: %s and %s on committed bins'
     % (f3(W['2017A']['E3']['premise_committed']), f3(W['2017B']['E3']['premise_committed']))],
    ['Allowance A5', 'E3 pays in informativeness', 'Holds, mildly below rated, strongly at rated (silent %.0f%%, abstains %.0f%%)'
     % (100 * W['2017B']['E3']['silent'], 100 * W['2017B']['E3']['abstain'])],
    ['Solar H1', 'Rule C fails below clipping', 'Holds (%s)' % f3(PL['A']['C']['premise'])],
    ['Solar H2', 'P and E1 reach 0.90 below clipping', 'E1 holds (%s); P misses narrowly (%s, CI includes 0.90)'
     % (f3(PL['A']['E1']['premise']), f3(PL['A']['P']['premise']))],
    ['Solar H3', 'P and E1 fall below 0.5 above clipping; S reaches 0.90',
     'First half falsified (%s, %s) by cancellation of over-rise and clipping (Section 5); S holds by over-covering'
     % (f3(PL['B']['P']['premise']), f3(PL['B']['E1']['premise']))],
    ['Solar H4', 'E3 reaches 0.90 in both scenarios', 'Holds where it commits (%s, %s) but abstains on %.0f%% and %.0f%% of bins'
     % (f3(PL['A']['E3_prev']['premise_committed']), f3(PL['B']['E3_prev']['premise_committed']),
        100 * PL['A']['E3_prev']['abstain'], 100 * PL['B']['E3_prev']['abstain'])],
    ['Solar H5', 'Zero failures where the premise held', 'Holds, 0 of %s' % n0(held_p)],
], [0.95, 2.55, 2.9], 'lll'))
para('Table 10. Wind H1&#8211;H4: WIND_PROTOCOL.md, 2016. A1&#8211;A5: ALLOWANCE_PROTOCOL.md, judged on '
     '2017. Solar H1&#8211;H5: PV_PROTOCOL.md.', CAP)

# --------------------------------------------------------------------- section 9
heading('9   What this changes in the paper\'s claims')
for i, t in enumerate([
        '<b>Keep Proposition 1, and report its cross-tab.</b> It has now been at risk on two '
        'independent systems and never failed when its premise held.',
        '<b>Retire the ceiling theory-distance allowance.</b> Its rate shrinks as the law improves. '
        'The capillary figures 931/931 and 399/399 rest on it and cannot be stated as a property '
        'of the method.',
        '<b>State a scope, not a universal rate.</b> With a calibration-only allowance the bound was '
        'valid when no regime change separated the calibration band from the test point (solar '
        'below clipping). Across a regime change (wind rotor limit, rated plateau) &#946; needs '
        'outside information: theory or a solver sweep (the proposal\'s Section 7), a spec sheet, or '
        'exchangeable labelled residuals from comparable units.',
        '<b>Size &#954;&#8242; on hops as long as those used at test.</b> The paper\'s Eq. 5 was '
        'borderline on solar (%s) and failed on wind (%s below rated).'
        % (f3(PL['A']['P']['premise']), f3(W['2017A']['P']['premise'])),
        '<b>Quote S/e only beside validity.</b> Under a valid allowance expect roughly 20&#8211;40% '
        'of the error on solar, not 70%.',
        '<b>Include the calibration maximum and the raw defect in every comparison.</b> Which of '
        'them beats the certificate depends on how surrogate error grows with distance, which a '
        'practitioner cannot know in advance.']):
    para('%d.  %s' % (i + 1, t), NUM)

# -------------------------------------------------------------------- section 10
heading('10   Limitations')
para('<b>Dependence.</b> Wind units share six turbines and one farm; solar units share 24 combiners, '
     'two inverters and one site. Confidence intervals are at the unit-bin level and treat bins as '
     'independent; clustering by turbine or combiner would widen them. Each surrogate family was fit '
     'with one seed.')
para('<b>Design order.</b> Rules E1&#8211;E3 were designed after the 2016 wind residuals were seen; '
     'only the 2017 results test them. E3 in 2017 calibrates on 2016 data from the same six turbines, '
     'so it tests transfer across time, not across sites; a second farm (for example Hill of Towie, '
     'Zenodo 14870023) would test the latter.')
para('<b>Solar data.</b> The plant\'s pyranometers were largely offline in 2020&#8211;22, so 2019 is '
     'sparse and 2018 was added as a scoring year (PV_DEVIATIONS.md, recorded before any result). '
     'The label-only analysis includes 2017 units, which the protocol reserved for E3 calibration; '
     'excluding them, band-A coverage is %.3f for P and %.3f for E1. Irradiance from two pyranometer '
     'pads does not see the cloud shadow each combiner sees, which is much of the scatter in Table 7.'
     % (no17['P'], no17['E1']))

# -------------------------------------------------------------------- section 11
heading('11   Reproducibility')
para('This report is generated by three scripts in sases_eval/. <b>wind_pv_data.py</b> rebuilds the '
     'row-level allowances with the audits\' own functions (allowance_audit, wind_paper_rule, '
     'pv_audit) and refuses to continue unless every premise share, validity and median S/e matches '
     'wind/allowance.json and wind/paper_rule.json to 10<super>&#8722;12</super>, and the solar '
     'coverage matches pv/report.txt. <b>wind_pv_figures.py</b> draws the figures from its output, '
     'and <b>wind_pv_pdf.py</b> sets every number in this document from the same output. Raw '
     'archives are not committed: Kelmarsh_SCADA_2016_3082.zip and Kelmarsh_SCADA_2017_3083.zip '
     '(Zenodo 16807551) and the PVDAQ 9068 irradiance and combiner files '
     '(s3://oedi-data-lake/pvdaq/2023-solar-data-prize/9068_OEDI/).', LEFT)
A(KeepTogether([tab(['Input', 'SHA-256 (first 16 hex)'],
      [[k, v[:16]] for k, v in S['inputs_sha256'].items()], [3.0, 2.0], 'll')]))


def footer(canvas, doc):
    canvas.setFont('TNR', 9)
    canvas.drawCentredString(LETTER[0] / 2, 35, 'SASES on wind and solar data  |  %s  |  %d' % (DATE, doc.page))


OUT.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(OUT), pagesize=LETTER, topMargin=48, bottomMargin=50, leftMargin=75,
                  rightMargin=75, title='SASES on wind and solar data', author='Brandon Rodriguez',
                  subject='Independent replication of the SASES certificate').build(
    story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
