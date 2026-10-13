# -*- coding: utf-8 -*-
"""Law-allowance report: how each allowance is derived, and whether a neural network
or a Kolmogorov-Arnold network can learn a better one. Every number is read at build
time from learned/{derivation,dev,confirm}.json (allowance_derivation.py and
learned_allowance.py, which gate against the stored audit outputs)."""
import json
from pathlib import Path

import numpy as np
import reportlab.platypus.paraparser as _pp
_pp.subFraction, _pp.supFraction = 0.22, 0.38
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                                KeepTogether)

HERE = Path(__file__).resolve().parent
L = HERE / 'learned'
DER = json.loads((L / 'derivation.json').read_text())
DEV = json.loads((L / 'dev.json').read_text())['pools']
CON = json.loads((L / 'confirm.json').read_text())['pools']
OUT = HERE.parent / 'output' / 'pdf' / 'sases_law_allowance_learned.pdf'
DATE = '3 October 2026'

FONTS = Path('C:/Windows/Fonts')
for name, f in (('TNR', 'times.ttf'), ('TNR-B', 'timesbd.ttf'), ('TNR-I', 'timesi.ttf'), ('TNR-BI', 'timesbi.ttf')):
    pdfmetrics.registerFont(TTFont(name, str(FONTS / f)))
for b, i, n in ((0, 0, 'TNR'), (1, 0, 'TNR-B'), (0, 1, 'TNR-I'), (1, 1, 'TNR-BI')):
    addMapping('TNR', b, i, n)
INK = colors.HexColor('#000000')
TITLE = ParagraphStyle('T', fontName='TNR', fontSize=17, leading=21, alignment=TA_CENTER, spaceAfter=8)
AUTH = ParagraphStyle('AU', fontName='TNR', fontSize=11, leading=15, alignment=TA_CENTER)
H = ParagraphStyle('H', fontName='TNR-B', fontSize=12.5, leading=15, spaceBefore=14, spaceAfter=6, keepWithNext=1)
H2 = ParagraphStyle('H2', fontName='TNR-B', fontSize=11, leading=14, spaceBefore=10, spaceAfter=4, keepWithNext=1)
BODY = ParagraphStyle('B', fontName='TNR', fontSize=10.5, leading=14.6, alignment=TA_JUSTIFY, spaceAfter=7)
LEFT = ParagraphStyle('LEFT', parent=BODY, alignment=0)
ABS = ParagraphStyle('ABS', parent=BODY, leftIndent=24, rightIndent=24, fontSize=10, leading=13.8)
CAP = ParagraphStyle('CAP', fontName='TNR', fontSize=9.4, leading=12.3, alignment=TA_JUSTIFY, spaceBefore=3, spaceAfter=11)
CAPL = ParagraphStyle('CAPL', parent=CAP, alignment=0)
CELL = ParagraphStyle('C', fontName='TNR', fontSize=9.0, leading=11.2)
CELLB = ParagraphStyle('CB', parent=CELL, fontName='TNR-B')
NUM = ParagraphStyle('NUM', parent=BODY, leftIndent=18, firstLineIndent=-12, spaceAfter=5)
EQ = ParagraphStyle('EQ', parent=BODY, alignment=TA_CENTER, spaceBefore=2, spaceAfter=8)

story = []
A = story.append


def para(t, st=BODY):
    A(Paragraph(t, st))


def heading(t, st=H):
    A(Paragraph(t, st))


def tab(headers, rows, widths, align=None, bold=(), keep=False):
    def c(x, j, b):
        st = ParagraphStyle('c', parent=CELLB if b else CELL,
                            alignment={'l': 0, 'c': 1, 'r': 2}[(align or 'l' * len(headers))[j]])
        return Paragraph(str(x), st)
    data = [[c(h, j, True) for j, h in enumerate(headers)]]
    data += [[c(x, j, i in bold) for j, x in enumerate(r)] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * inch for w in widths], hAlign='CENTER', repeatRows=1)
    t.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 1.1, INK), ('LINEBELOW', (0, 0), (-1, 0), 0.5, INK),
                           ('LINEBELOW', (0, -1), (-1, -1), 1.1, INK), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('TOPPADDING', (0, 0), (-1, -1), 2.4), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.4),
                           ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]))
    return t


def table_cap(t, cap, pre=()):
    """A table, its caption and any leading heading or sentence, never split."""
    A(KeepTogether(list(pre) + [t, Paragraph(cap, CAP)]))


def figure(png, caption, width=6.4):
    from PIL import Image as PImage
    w, h = PImage.open(L / png).size
    A(KeepTogether([Image(str(L / png), width=width * inch, height=width * inch * h / w), Paragraph(caption, CAP)]))


f2 = lambda x: '%.2f' % x
f3 = lambda x: '%.3f' % x
f4 = lambda x: '%.4f' % x
ci = lambda c: '[%.3f, %.3f]' % tuple(c)
n0 = lambda x: f'{x:,}'
W, P, CAPI = DER['wind'], DER['pv'], DER['capillary']
WD, PD18, PD19 = DEV
WC = CON[0]
PC = {p['test']: p for p in CON[1:]}


def R(pool, sc, rule, key='premise'):
    return pool['results'][sc][rule][key]


def cov(pool, sc, rule):
    o = pool['results'][sc][rule]
    return o['committed'] if o['committed'] is not None else o['premise']


MAIN = ['C', 'P', 'E1', 'Z', 'A-NN', 'A-KAN', 'E3', 'F0', 'F-lin', 'F-GBT', 'F-NN-ens', 'F-KAN-ens']
NAME = {'C': 'C', 'P': 'P', 'E1': 'E1', 'Z': 'Z', 'S': 'S', 'A-NN': 'A-NN', 'A-KAN': 'A-KAN', 'E3': 'E3',
        'F0': 'F0', 'F-lin': 'F-lin', 'F-GBT': 'F-GBT', 'F-NN-ens': 'F-NN', 'F-KAN-ens': 'F-KAN'}
FLEET_FEAT = ['F-lin', 'F-GBT', 'F-NN-ens', 'F-KAN-ens']

# ------------------------------------------------------------------- derived
wq = np.linalg.norm(W['q']); pq = np.linalg.norm(P['q'])
wt = {t['bin']: t for t in W['tests']}; pt = {t['bin']: t for t in P['tests']}
best_wind_A = max(FLEET_FEAT, key=lambda r: R(WC, 'A', r, 'median_S_over_e') if cov(WC, 'A', r) >= 0.9 else -1)
seeds_kan = [cov(WC, s, k) for s in 'AB' for k in ('F-KAN', 'F-KAN#1', 'F-KAN#2')]
seeds_nn = [cov(WC, s, k) for s in 'AB' for k in ('F-NN', 'F-NN#1', 'F-NN#2')]

# ------------------------------------------------------------------- title
A(Paragraph('Deriving the Law Allowance: Formulas, Neural Networks and KANs', TITLE))
A(Paragraph('Worked derivations on capillary, wind and solar data, and learned allowances confirmed on an unseen wind year', AUTH))
A(Spacer(1, 4)); A(Paragraph('Brandon Rodriguez', AUTH)); A(Paragraph(DATE, AUTH)); A(Spacer(1, 10))
heading('Abstract')
para('Every SASES law allowance answers one question: how far can the real system depart from its '
     'law at extrapolation distance &#948;? This report derives each rule step by step on one real unit of '
     'each system, then asks whether a neural network (MLP) or a Kolmogorov&#8211;Arnold network (KAN) can '
     'learn a better allowance. Learned allowances were developed on wind 2016&#8211;17 and solar '
     '2017&#8211;19, frozen in a written protocol, and confirmed on Kelmarsh 2018, a year never opened before. '
     '<b>(1)</b> A model fitted to a unit\'s own calibration data cannot see a regime break outside that data. '
     'The one that appeared to, an MLP covering every wind test bin, did so because its tanh units flatten '
     'beyond the data. Its principled form, rule Z (outputs keep rising but never faster than the fitted law, '
     '&#946; = &#8214;q&#8214;&#948;), covered %.0f%% and %.0f%% of wind 2018 bins below and above rated from each '
     'turbine\'s own data, where the best earlier own-data rule covered %.0f%% and %.0f%%. <b>(2)</b> Learned '
     'from other turbines and calibrated conformally, the MLP and KAN gave valid allowances on wind 2018 '
     '(coverage %.2f&#8211;%.2f) but were no better than gradient-boosted trees, and all four learners recover '
     'the same convex dependence on distance. They held coverage where the featureless fleet rules slipped '
     'to %.2f. <b>(3)</b> On solar no learned rule improved on the own-data long-hop rule E1 (%.3f and %.3f in '
     '2023): solar years are not exchangeable, and the learned fleet models covered only %.2f&#8211;%.2f below clipping.'
     % (100 * R(WC, 'A', 'Z'), 100 * R(WC, 'B', 'Z'), 100 * R(WC, 'A', 'E1'), 100 * R(WC, 'B', 'E1'),
        min(R(WC, s, r) for s in 'AB' for r in ('F-NN-ens', 'F-KAN-ens')),
        max(R(WC, s, r) for s in 'AB' for r in ('F-NN-ens', 'F-KAN-ens')),
        min(R(WC, 'A', 'E3'), R(WC, 'B', 'F0')), R(PC[2023], 'A', 'E1'), R(PC[2023], 'B', 'E1'),
        min(R(PC[2023], 'A', r) for r in FLEET_FEAT),
        max(R(PC[2023], 'A', r) for r in FLEET_FEAT)), ABS)

# --------------------------------------------------------------- section 1
heading('1   What the allowance does')
para('For a test input x beyond the law-calibration band (LAWCAL), the certificate extrapolates the law '
     'from the top calibration bin: c(x) = y<sub>top</sub> + q&#183;&#948;, with q the exponent fitted on '
     'LAWCAL and &#948; = ln(x/x<sub>top</sub>) the extrapolation distance. The law residual is '
     '&#950; = y(x) &#8722; c(x), the raw defect of a surrogate f is D = &#8214;f(x) &#8722; c(x)&#8214;, '
     'and the certificate is')
para('S = max(D &#8722; &#946;, 0),', EQ)
para('a lower bound on the true error e = &#8214;f(x) &#8722; y(x)&#8214; whenever the premise '
     '&#8214;&#950;&#8214; &#8804; &#946; holds. The allowance &#946; must be fixed without the test label, '
     'so it is a prediction of how far the real system departs from its law at distance &#948;. Too small, '
     'and the bound fails; too large, and S collapses to zero. Every rule below is a different answer to '
     'one question: <i>how large can &#8214;&#950;&#8214; be at this distance?</i>')

# --------------------------------------------------------------- section 2
heading('2   How each allowance is derived')
A(tab(['Rule', 'Allowance &#946;', 'Derived from', 'Assumes'], [
    ['C', '&#8214;q<sub>cal</sub> &#8722; q<sub>th</sub>&#8214;&#183;&#948;', 'LAWCAL slope, theory exponent',
     'The law departs at the rate the fitted exponent differs from theory'],
    ['P', "2&#954;&#8242;<sub>short</sub>&#183;&#948;", 'Leave-the-top-out hops inside LAWCAL',
     'Residual per unit distance at test &#8804; twice the worst short calibration hop'],
    ['E1', "2&#954;&#8242;<sub>long</sub>&#183;&#948;", 'Hops from every 4-bin window of TRAIN+LAWCAL to every higher labelled bin',
     'Same, measured over longer hops'],
    ['E2', 'max(E1, 2&#183;quadratic departure)', 'Quadratic fit over TRAIN+LAWCAL', 'Curvature visible in calibration continues'],
    ['S', 'E1 + 2&#183;max(0, ln(G/G<sub>clip</sub>))', 'Spec sheet (solar)', 'Current stops rising at the clipping onset'],
    ['Z', '&#8214;q&#8214;&#183;&#948;', 'LAWCAL slope only',
     '<b>New.</b> Each output keeps rising but never faster than the fitted law'],
    ['E3', 'k-th smallest &#8214;&#950;&#8214; at the same bin over n fleet units, k = ceil(0.9(n+1))',
     'Labelled residuals from other units', 'Units exchangeable at each bin; abstains if n &lt; 9'],
    ['F0', '&#948; &#215; k-th smallest &#8214;&#950;&#8214;/&#948; in the band', 'Fleet residuals pooled per band',
     '<b>New.</b> Residual per unit distance exchangeable within a band'],
    ['F-model', 'CV+ quantile of &#963;<sub>k</sub>(x)&#183;s<sub>i</sub>, s = &#8214;&#950;&#8214;/&#963;',
     'Fleet residuals and a learned scale &#963;(x)', '<b>New.</b> Exchangeable normalised residuals; &#963; from ridge, trees, MLP or KAN'],
    ['A-model', 'max(E1, 2&#8214;g(u) &#8722; c(u)&#8214;)', 'MLP or KAN fitted to the unit\'s 8 labelled bins',
     '<b>New.</b> The fitted curve\'s extrapolation shows the departure'],
], [0.7, 1.8, 1.9, 2.0], 'llll'))
para('Table 1. The allowance rules. Rules marked new were introduced in this study; '
     'LEARNED_ALLOWANCE_PROTOCOL.md records when and why.', CAPL)

heading('2.1   Worked example: wind turbine-month %s' % W['unit'], H2)
para('This turbine-month from Kelmarsh 2017 was chosen because its long-hop rate &#954;&#8242; is the median '
     'of its year. All values are natural logs of power P (kW) and rotor speed &#969; (rpm). The script '
     'allowance_derivation.py recomputes every step and asserts each final value equals the audit '
     'functions\' output.')
rows = [[r['role'], '%.2f' % r['bin'], '%.2f' % r['x'], f4(r['y'][0]), f4(r['y'][1])] for r in W['labelled']]
table_cap(tab(['Band', 'Bin (m/s)', 'Mean U', 'ln P', 'ln &#969;'], rows, [0.9, 0.9, 0.9, 0.9, 0.9], 'lrrrr'),
          'Table 2. The eight labelled bins of %s. The LAWCAL fit gives q = (%.3f, %.3f) against theory (3, 1); '
          'the ceiling is the %.2f m/s bin.' % (W['unit'], W['q'][0], W['q'][1], W['top']))
para('<b>Step 1, the rates.</b> Rule C: &#954; = &#8214;(%.3f, %.3f) &#8722; (3, 1)&#8214; = %s. Rule P fits the '
     'law on the first three LAWCAL bins and predicts the fourth, then on the first two and predicts the '
     'third and fourth; the three ratios &#8214;&#950;&#8214;/&#948; are %s, so &#954;&#8242;<sub>short</sub> = %s. '
     'Rule E1 fits every window of four consecutive labelled bins and predicts every higher labelled bin: '
     '%d hops with ratios from %s to %s, so &#954;&#8242;<sub>long</sub> = %s. Rule Z needs only '
     '&#8214;q&#8214; = %s.'
     % (W['q'][0], W['q'][1], f4(W['kappa_C']), ', '.join(f3(h['ratio']) for h in W['hops_P']), f4(W['kappa_P']),
        len(W['hops_E1']), f3(min(h['ratio'] for h in W['hops_E1'])), f3(max(h['ratio'] for h in W['hops_E1'])),
        f4(W['kappa_E1']), f3(wq)))
t1, t2 = wt[9.75], wt[12.75]
para('<b>Step 2, the fleet quantities.</b> E3 at 9.75 m/s pools the residual of the %d 2016 turbine-months '
     'that reach that bin and takes the %d-th smallest; at 12.75 m/s only %d units reach the bin, so it '
     'takes the %d-th, the largest. F0 pools &#8214;&#950;&#8214;/&#948; over every 2016 bin in the band '
     '(%d below rated, %d rated) and takes the 90%% conformal quantile: rates %s and %s.'
     % (t1['e3_pool_n'], t1['e3_k'], t2['e3_pool_n'], t2['e3_k'], t1['f0_n'], t2['f0_n'], f3(t1['f0_rate']),
        f3(t2['f0_rate'])))
rr = ['C', 'P', 'E1', 'Z', 'E3', 'F0']
rows = []
for t in (t1, t2):
    rows.append(['%.2f m/s' % t['bin'], f4(t['delta']), f4(t['zeta_norm'])] +
                ['%s%s' % (f3(t['beta'][r]), '' if t['covered'][r] else '&#8224;') for r in rr])
table_cap(tab(['Test bin', '&#948;', '&#8214;&#950;&#8214;'] + rr, rows, [0.85, 0.6, 0.6] + [0.6] * 6, 'lrrrrrrrr'),
          'Table 3. Allowance &#946; for each rule at two test bins of %s; &#8224; marks a miss (&#946; &lt; '
          '&#8214;&#950;&#8214;). The calibration data say the residual grows at about %.2f per unit distance at '
          'most (E1 uses twice that); the test bins need %.2f and %.2f.'
          % (W['unit'], W['kappa_E1'], t1['zeta_norm'] / t1['delta'], t2['zeta_norm'] / t2['delta']))
para('Every rule built from this unit\'s own fitted rates misses both test bins. The calibration hops '
     'all sit in the region where the law holds, so they cannot reveal that the rotor reaches its speed '
     'limit near 9 m/s. Z covers both because it assumes only that the outputs keep rising no faster than '
     'the law, which a speed limit and a power plateau satisfy. The fleet rules cover both because other '
     'turbines have already been observed past the break.')

heading('2.2   Worked example: solar combiner-month %s' % P['unit'], H2)
s1, s2 = pt[675.0], pt[975.0]
para('Output is ln I (DC current, A) against ln G (irradiance, W/m&#178;); theory q = 1. The LAWCAL fit gives '
     'q = %.3f, well below theory, and &#954; = %s for rule C. The P hops give ratios %s (&#954;&#8242; = %s); '
     'E1\'s %d hops range from %s to %s (&#954;&#8242; = %s); &#8214;q&#8214; = %s for Z. The spec-sheet term '
     'of rule S is 2 ln(%.0f/823) = %s at the 975 W/m&#178; bin and zero below the onset.'
     % (P['q'][0], f4(P['kappa_C']), ', '.join(f3(h['ratio']) for h in P['hops_P']), f4(P['kappa_P']),
        len(P['hops_E1']), f3(min(h['ratio'] for h in P['hops_E1'])), f3(max(h['ratio'] for h in P['hops_E1'])),
        f4(P['kappa_E1']), f3(pq), s2['x'], f3(s2['spec_term'])))
rr = ['C', 'P', 'E1', 'Z', 'S', 'E3', 'F0']
rows = [['%.0f W/m&#178;' % t['bin'], f4(t['delta']), f4(t['zeta_norm'])] +
        ['%s%s' % (f3(t['beta'][r]), '' if t['covered'][r] else '&#8224;') for r in rr] for t in (s1, s2)]
table_cap(tab(['Test bin', '&#948;', '&#8214;&#950;&#8214;'] + rr, rows, [0.9, 0.55, 0.55] + [0.56] * 7, 'lrrrrrrrrr'),
          'Table 4. Allowances for %s. E3 and F0 calibrate on 2017 (E3 pools %d and %d units at the two bins).'
          % (P['unit'], s1['e3_pool_n'], s2['e3_pool_n']))
para('Here the own-data rates P and E1 cover both bins, because on solar the scatter between months '
     'already makes short calibration hops look steep. Z misses both: below clipping the current rises '
     'faster than the fitted slope q = %.2f, which breaks Z\'s one assumption.' % P['q'][0])

heading('2.3   Capillary corpus', H2)
para('The capillary headline numbers used rule C with theory exponent 0.5 (Kibble&#8211;Zurek). In '
     'configuration %s, the law fitted on %s gives twelve band exponents between %.2f and %.2f, so '
     '&#954; = &#8214;q &#8722; 0.5&#8214; = %.2f. At trial %s (%.0f mW) the distance from the %.0f mW ceiling '
     'is &#948; = %.3f, so &#946; = %.2f against a residual of %.2f: covered. The allowance covers here only '
     'because the fitted exponents sit far from 0.5, not because &#954; measures departure from the law; '
     'on wind and solar, where fitted exponents are close to theory, the same rule covers 0&#8211;25%% of bins.'
     % (CAPI['config'].replace('_', ' '), ', '.join(CAPI['lawcal']), CAPI['q_min'], CAPI['q_max'], CAPI['kappa'],
        CAPI['trial'], CAPI['P_mW'], CAPI['ceiling_mW'], CAPI['delta'], CAPI['beta'], CAPI['zeta']))
figure('figL1_derivation.png',
       '<b>Figure 1.</b> The derivation as a picture. Hollow points: the calibration hops E1 learns its rate '
       'from. Black points: the test residuals the allowance must cover. Grey lines: the own-data rates '
       '(C, P, E1). Bars: the fleet allowances at the test bins. On wind every calibration hop lies far below '
       'what the test bins need.')

# --------------------------------------------------------------- section 3
heading('3   Can a neural network or a KAN learn the allowance?')
para('A learned allowance must obey the same rule as every other: it may not read the scored unit\'s test '
     'labels. That leaves two places a model can learn from, and they behave very differently.')
para('<b>Family A: the unit\'s own calibration data.</b> Fit an MLP (16 tanh units) or a KAN to the eight '
     'labelled bins, extrapolate to the test bin, and use twice the departure of that extrapolation from the '
     'law line as an allowance, max(E1, 2&#8214;g(u) &#8722; c(u)&#8214;). This is rule E2 with a flexible '
     'curve in place of a quadratic.')
para('<b>Family F: other units, calibrated conformally.</b> Learn how large the residual is from labelled '
     'residuals of other units, then calibrate the learned scale so the allowance has a coverage guarantee. '
     'A model m is fitted to ln&#8214;&#950;&#8214; on features the unit has at deployment (Table 5); its '
     'scale &#963;(x) = exp m(x) is clipped to the training range; normalised scores s = &#8214;&#950;&#8214;/&#963; '
     'are computed out of fold (5 folds grouped by unit) and kept separate by band (CV+ with Mondrian '
     'bands, Barber et al. 2021). The allowance at a test point is the ceil(0.9(n+1))-th smallest of '
     '&#963;<sub>k</sub>(x)&#183;s<sub>i</sub> over the n training points of its band. Under exchangeable units this '
     'covers at least about 90%, whatever the model, so the model only decides how tight the allowance is. '
     'Four scale models are compared: ridge regression, gradient-boosted trees, an MLP (16&#215;16) and a KAN; '
     'the MLP and KAN are reported as the geometric-mean ensemble of three seeds.')
table_cap(tab(['System', 'Features (all from the unit\'s TRAIN and LAWCAL bins plus the test input)'], [
    ['Wind', '&#948;, ln U, q<sub>P</sub>, q<sub>&#969;</sub>, ln P and ln &#969; at the ceiling, quadratic curvature of each '
             'output, E1 &#954;&#8242;, RMS residual of the LAWCAL fit'],
    ['Solar', '&#948;, ln G, q, ln I at the ceiling, curvature, E1 &#954;&#8242;, RMS LAWCAL residual, sin and cos of the month'],
], [0.8, 5.6], 'll'), 'Table 5. Features of the learned scale models.')
para('<b>The KAN.</b> A Kolmogorov&#8211;Arnold network puts a learnable univariate function on every edge '
     'instead of a fixed activation on every node (Liu et al. 2024): each edge computes '
     '&#966;(x) = a&#183;SiLU(x) + &#931;<sub>k</sub> c<sub>k</sub>B<sub>k</sub>(x) with cubic B-splines on a uniform grid, and '
     'each node sums its incoming edges. The network here is [d, 4, 1] with five grid intervals, ridge and '
     'second-difference penalties, trained by full-batch Adam. There is no deep-learning library in this '
     'environment, so it is written in numpy (kan.py); test_kan.py checks that the spline basis is a '
     'partition of unity, that the hand-written gradient matches finite differences to 10<super>&#8722;6</super>, '
     'and that the network fits a known nonlinear function.')
para('<b>Design.</b> LEARNED_ALLOWANCE_PROTOCOL.md was written before any learned allowance was fitted and '
     'before Kelmarsh 2018 was downloaded. Development used wind 2016 &#8594; 2017 and solar 2017 &#8594; '
     '2018 and 2017&#8211;18 &#8594; 2019. Three changes were made after development and recorded before '
     'confirmation: rule Z was added, learned scales were clipped to the training range, and seed ensembles '
     'were added. Confirmation trained on wind 2016&#8211;17 and scored Kelmarsh 2018, a year never opened '
     'before, through the unchanged pipeline (72 turbine-months, 9 surrogates each); solar trained on '
     '2017&#8211;19 and scored 2022&#8211;23, which had been opened before for other rules.')

# --------------------------------------------------------------- section 4
heading('4   Development: what the first run showed')
para('<b>Wind.</b> Every fleet rule covered at least %.2f below rated and %.2f in the rated region. The plain '
     'fleet rate F0 removed E3\'s %.0f%% abstention in the rated region and claimed more of the error (median '
     'S/e %.2f against %.2f). Contrary to the protocol\'s expectation, the own-data MLP covered %.3f and %.3f. '
     'Its tanh units saturate beyond the calibration data, so it extrapolates a plateau, and wind has one: an '
     'inductive bias that happens to match the physics, not something learned from the eight bins.'
     % (min(cov(WD, 'A', r) for r in ['E3', 'F0'] + FLEET_FEAT), min(cov(WD, 'B', r) for r in ['E3', 'F0'] + FLEET_FEAT),
        100 * R(WD, 'B', 'E3', 'abstain'), R(WD, 'B', 'F0', 'median_S_over_e'), R(WD, 'B', 'E3', 'median_S_over_e'),
        R(WD, 'A', 'A-NN'), R(WD, 'B', 'A-NN')))
para('<b>Solar.</b> Trained on 2017, which covers only August&#8211;December, the feature models failed on 2018 '
     '(ridge %.2f, trees %.2f below clipping): January&#8211;July inputs lie outside the training support, and '
     'conformal calibration cannot repair a covariate shift. Before clipping was added, the MLP\'s predicted '
     'scale reached 10<super>5</super> times the residual on such inputs (recorded in the protocol\'s development '
     'log); with clipping, MLP and KAN coverage on the solar development pools still varied by up to %.2f '
     'between seeds. These observations produced the three recorded changes: rule Z, scale clipping and '
     'seed ensembles.' % (R(PD18, 'A', 'F-lin'), R(PD18, 'A', 'F-GBT'),
                          max(max(R(p, s, f + x) for x in ('', '#1', '#2')) - min(R(p, s, f + x) for x in ('', '#1', '#2'))
                              for p in (PD18, PD19) for s in p['results'] for f in ('F-NN', 'F-KAN'))))

figure('figL2_dev.png',
       '<b>Figure 2.</b> Development pools. Premise coverage with 95% Clopper&#8211;Pearson intervals; '
       'columns give median &#946;/&#8214;&#950;&#8214; (lower is tighter), median S/e (share of the true error '
       'claimed) and abstention. F-NN and F-KAN are three-seed ensembles.')
# --------------------------------------------------------------- section 5
PRE6 = [Paragraph('5   Confirmation on unseen data', H),
        Paragraph('Table 6 gives wind 2018. Proposition 1 held throughout: no row whose premise held had S &gt; e.', BODY)]
rows = [[NAME[r], f3(cov(WC, 'A', r)), ci(R(WC, 'A', r, 'committed_ci')), f3(R(WC, 'A', r, 'validity')),
         f2(R(WC, 'A', r, 'median_S_over_e')), f3(cov(WC, 'B', r)), f3(R(WC, 'B', r, 'validity')),
         f2(R(WC, 'B', r, 'median_S_over_e'))] for r in MAIN]
table_cap(tab(['Rule', 'A: coverage', 'A: 95% CI', 'A: valid', 'A: S/e', 'B: coverage', 'B: valid', 'B: S/e'], rows,
              [0.7, 0.8, 1.0, 0.65, 0.6, 0.8, 0.65, 0.6], 'lrrrrrrr',
              bold=tuple(i for i, r in enumerate(MAIN) if r in ('Z', 'F-GBT', 'F-KAN-ens'))),
          'Table 6. Wind 2018, never opened before confirmation: %d turbine-months, %s scored rows. Coverage is '
          'the share of test unit-bins with &#946; &#8805; &#8214;&#950;&#8214; (A: %d, B: %d); valid is the share '
          'of rows with S &#8804; e; S/e is the median. Fleet rules train on 2016&#8211;17 (%d turbine-months).'
          % (len({k[0] for k in WC['test_keys']}), n0(R(WC, 'A', 'C', 'rows') + R(WC, 'B', 'C', 'rows')),
             R(WC, 'A', 'C', 'unit_bins'), R(WC, 'B', 'C', 'unit_bins'), WC['n_train_units']), pre=PRE6)
spread = lambda keys: max(max(R(WC, s, k) for k in keys) - min(R(WC, s, k) for k in keys) for s in 'AB')
para('<b>Wind.</b> Z covered every 2018 test bin in both scenarios from each turbine\'s own data, with '
     'validity %.3f and %.3f, where E1 managed %.3f and %.3f. The fleet rules that use no features slipped '
     'slightly below the 90%% target (E3 %.3f below rated, F0 %.3f in the rated region; both intervals include '
     '0.90), while every feature-based learner held: trees %.3f / %.3f, KAN %.3f / %.3f, MLP %.3f / %.3f, '
     'ridge %.3f / %.3f. The learners were not tighter than E3; they reached higher coverage at about the '
     'same width (median &#946;/&#8214;&#950;&#8214; %.2f&#8211;%.2f below rated against %.2f for E3). The KAN '
     'matched the trees (S/e %.2f against %.2f below rated, %.2f against %.2f rated) and was the most stable '
     'across seeds (coverage spread %.3f, against %.3f for the MLP).'
     % (R(WC, 'A', 'Z', 'validity'), R(WC, 'B', 'Z', 'validity'), R(WC, 'A', 'E1', 'validity'), R(WC, 'B', 'E1', 'validity'),
        R(WC, 'A', 'E3'), R(WC, 'B', 'F0'), R(WC, 'A', 'F-GBT'), R(WC, 'B', 'F-GBT'), R(WC, 'A', 'F-KAN-ens'),
        R(WC, 'B', 'F-KAN-ens'), R(WC, 'A', 'F-NN-ens'), R(WC, 'B', 'F-NN-ens'), R(WC, 'A', 'F-lin'), R(WC, 'B', 'F-lin'),
        min(R(WC, 'A', r, 'tightness') for r in FLEET_FEAT), max(R(WC, 'A', r, 'tightness') for r in FLEET_FEAT),
        R(WC, 'A', 'E3', 'tightness'), R(WC, 'A', 'F-KAN-ens', 'median_S_over_e'), R(WC, 'A', 'F-GBT', 'median_S_over_e'),
        R(WC, 'B', 'F-KAN-ens', 'median_S_over_e'), R(WC, 'B', 'F-GBT', 'median_S_over_e'),
        spread(('F-KAN', 'F-KAN#1', 'F-KAN#2')), spread(('F-NN', 'F-NN#1', 'F-NN#2'))))
figure('figL3_confirm.png',
       '<b>Figure 3.</b> Confirmation: wind 2018 (a, b) and solar 2023 (c, d). Solar 2022 has only %d '
       'below-clipping unit-bins and appears in Table 7. The solar confirmation is label-only, so it has no S/e.'
       % R(PC[2022], 'A', 'C', 'unit_bins'))
SOL = ['C', 'P', 'E1', 'Z', 'S', 'A-NN', 'A-KAN', 'E3', 'F0', 'F-lin', 'F-GBT', 'F-NN-ens', 'F-KAN-ens']
rows = [[NAME[r], f3(cov(PC[2022], 'A', r)), f3(cov(PC[2023], 'A', r)), ci(R(PC[2023], 'A', r, 'committed_ci')),
         f2(R(PC[2023], 'A', r, 'tightness')), f3(cov(PC[2023], 'B', r)), f2(R(PC[2023], 'B', r, 'tightness'))] for r in SOL]
table_cap(tab(['Rule', '2022 A', '2023 A', '2023 A: 95% CI', '2023 A: &#946;/&#8214;&#950;&#8214;', '2023 B',
               '2023 B: &#946;/&#8214;&#950;&#8214;'], rows, [0.7, 0.75, 0.75, 1.15, 1.0, 0.75, 1.0], 'lrrrrrr', bold=(2,)),
          'Table 7. Solar confirmation, label-only premise coverage (2022: %d unit-bins below clipping, none above; '
          '2023: %d and %d). Fleet rules train on 2017&#8211;19 (%d combiner-months).'
          % (R(PC[2022], 'A', 'C', 'unit_bins'), R(PC[2023], 'A', 'C', 'unit_bins'), R(PC[2023], 'B', 'C', 'unit_bins'),
             PC[2023]['n_train_units']))
para('<b>Solar.</b> The own-data rule E1 stayed best: %.3f and %.3f in 2023, and %.3f in 2022, whose '
     'interval includes 0.90. The learned own-data curves reduce to E1 here because the E1 term dominates '
     'the maximum. The featureless fleet rules held in 2023 (E3 %.3f, F0 %.3f below clipping) but collapsed '
     'in 2022 (%.3f and %.3f), a sparse year recorded while the plant\'s pyranometers were partly offline. '
     'The feature-based learners failed in 2023 (%.2f&#8211;%.2f below clipping): the features of a '
     'combiner-month shift from year to year on this plant, and a scale model trained on earlier years '
     'carries that shift into the allowance. Z covered %.3f below clipping, under the target as predicted, '
     'because current rises faster than the fitted law before clipping.'
     % (R(PC[2023], 'A', 'E1'), R(PC[2023], 'B', 'E1'), R(PC[2022], 'A', 'E1'), R(PC[2023], 'A', 'E3'), R(PC[2023], 'A', 'F0'),
        R(PC[2022], 'A', 'E3'), R(PC[2022], 'A', 'F0'), min(R(PC[2023], 'A', r) for r in FLEET_FEAT),
        max(R(PC[2023], 'A', r) for r in FLEET_FEAT), R(PC[2023], 'A', 'Z')))

heading('6   What a neural network or KAN adds')
para('<b>Fitted to the unit\'s own data: nothing real.</b> The calibration bins contain no trace of a break '
     'that lies beyond them, and no model can extract what is not there. The MLP\'s coverage on wind comes '
     'from its activation function, not from the data; the KAN, whose SiLU base and spline grid extrapolate '
     'nearly linearly, covered less (%.3f and %.3f on 2018). On solar both reduce to E1. The useful lesson '
     'from the MLP is the assumption it smuggled in, which rule Z states openly.'
     % (R(WC, 'A', 'A-KAN'), R(WC, 'B', 'A-KAN')))
para('<b>Trained on other units: a valid but unremarkable scale.</b> With conformal calibration any scale '
     'model gives a valid allowance when units are exchangeable; the model only sets the width. Figure 4 '
     'shows what the four learners found on wind: the same convex growth of the residual with distance, the '
     'super-linear departure that defeats every own-data rate, with little dependence on the other features. '
     'The KAN reproduces the trees\' curve smoothly; the MLP adds a non-physical kink in rotor speed. A table '
     'of fleet residuals per bin (E3) or a single fleet rate (F0) captures most of the same information. The '
     'learners\' advantage on wind 2018 was robustness to a year that differed from its training years, not '
     'tightness.')
figure('figL4_partial.png',
       '<b>Figure 4.</b> Learned scale &#963; on wind 2016&#8211;17, varying one feature with the others at their '
       'median. (a) Against extrapolation distance, with training residuals in grey: all four learners find '
       'the same convex curve (the ridge model is clipped at the training maximum). (b) Against rotor speed '
       'at the ceiling bin, at the median rated-band distance: almost flat, apart from the MLP\'s artefact.')
heading('6.1   What improved', H2)
_t8 = (tab(['Setting', 'Before', 'After', 'Change on wind 2018 (below rated / rated)'], [
    ['Wind, own data only', 'E1', 'Z', 'coverage %.2f / %.2f &#8594; %.2f / %.2f; validity %.2f / %.2f &#8594; %.2f / %.2f'
     % (R(WC, 'A', 'E1'), R(WC, 'B', 'E1'), R(WC, 'A', 'Z'), R(WC, 'B', 'Z'), R(WC, 'A', 'E1', 'validity'),
        R(WC, 'B', 'E1', 'validity'), R(WC, 'A', 'Z', 'validity'), R(WC, 'B', 'Z', 'validity'))],
    ['Wind, with fleet data', 'E3', 'F-KAN or F-GBT', 'coverage %.2f / %.2f &#8594; %.2f / %.2f (KAN) at S/e %.2f / %.2f &#8594; %.2f / %.2f'
     % (R(WC, 'A', 'E3'), R(WC, 'B', 'E3'), R(WC, 'A', 'F-KAN-ens'), R(WC, 'B', 'F-KAN-ens'), R(WC, 'A', 'E3', 'median_S_over_e'),
        R(WC, 'B', 'E3', 'median_S_over_e'), R(WC, 'A', 'F-KAN-ens', 'median_S_over_e'), R(WC, 'B', 'F-KAN-ens', 'median_S_over_e'))],
    ['Wind, rated-region abstention', 'E3 (%.0f%% in 2017)' % (100 * R(WD, 'B', 'E3', 'abstain')), 'F0 and learners',
     'none by construction: bins are pooled within a band'],
    ['Solar', 'E1', 'E1', 'no learned rule improved it; E1 %.3f / %.3f in 2023' % (R(PC[2023], 'A', 'E1'), R(PC[2023], 'B', 'E1'))],
], [1.45, 0.95, 1.0, 3.0], 'llll'))
table_cap(_t8, 'Table 8. Recommended allowances by setting. Z costs informativeness (median S/e %.2f and %.2f '
     'against %.2f and %.2f for the fleet KAN): without outside data, a valid bound is a weaker one.'
     % (R(WC, 'A', 'Z', 'median_S_over_e'), R(WC, 'B', 'Z', 'median_S_over_e'), R(WC, 'A', 'F-KAN-ens', 'median_S_over_e'),
        R(WC, 'B', 'F-KAN-ens', 'median_S_over_e')))

_t9 = (tab(['', 'Expectation', 'Result'], [
    ['L1', 'No bound failure where the premise held', 'Holds: asserted on every scored row, development and wind 2018'],
    ['L2', 'Own-data NN and KAN stay below 0.75 / 0.10 on wind', '<b>Falsified in development</b> (MLP %.3f / %.3f); replaced before confirmation'
     % (R(WD, 'A', 'A-NN'), R(WD, 'B', 'A-NN'))],
    ['L2 revised', 'A-NN &#8805; 0.90 on wind 2018 in both scenarios; A-KAN no higher', 'Holds: %.3f / %.3f; A-KAN %.3f / %.3f'
     % (R(WC, 'A', 'A-NN'), R(WC, 'B', 'A-NN'), R(WC, 'A', 'A-KAN'), R(WC, 'B', 'A-KAN'))],
    ['L3', 'Every fleet rule &#8805; 0.90 on wind 2018 within sampling error, no abstention',
     'Holds: lowest are E3 %.3f %s and F0 %.3f %s; no abstention' % (R(WC, 'A', 'E3'), ci(R(WC, 'A', 'E3', 'premise_ci')),
                                                                    R(WC, 'B', 'F0'), ci(R(WC, 'B', 'F0', 'premise_ci')))],
    ['L4', 'A feature-based learner tighter than E3 and F0 at equal coverage',
     '<b>Not supported as stated</b>: none was tighter; they reached higher coverage at about the same width. On solar they failed'],
    ['L5', 'NN and KAN no better than trees or ridge beyond seed variation', 'Holds: KAN about equal to trees, MLP slightly looser'],
    ['Z1', 'Z &#8805; 0.90 in both wind scenarios on 2018', 'Holds: %.3f / %.3f' % (R(WC, 'A', 'Z'), R(WC, 'B', 'Z'))],
    ['Z2', 'Z &lt; 0.90 on solar below clipping in 2022&#8211;23', 'Holds: %.3f and %.3f' % (R(PC[2022], 'A', 'Z'), R(PC[2023], 'A', 'Z'))],
], [0.85, 2.55, 3.0], 'lll'))
table_cap(_t9, 'Table 9. Expectations from LEARNED_ALLOWANCE_PROTOCOL.md.',
          pre=[Paragraph('7   Verdicts on the protocol\'s expectations', H)])

heading('8   Limitations')
para('<b>One farm, one plant.</b> Wind 2018 comes from the same six turbines as the training years, so it tests '
     'transfer across time, not across sites. Solar 2022&#8211;23 had been opened before for the formula rules, '
     'so the solar confirmation is weaker than the wind one.')
para('<b>Z is an assumption, not a measurement.</b> It holds for systems that saturate (rated power, a '
     'rotor-speed limit) and fails for any system whose output can rise faster than its law past the '
     'calibration band, as solar current does before clipping. Using it requires a physical argument for '
     'the system at hand, of the kind the proposal\'s Section 7 asks for.')
para('<b>Conformal assumptions.</b> CV+ guarantees at least 1 &#8722; 2&#945; in theory and about 1 &#8722; &#945; in '
     'practice under exchangeable units; pooling bins within a band adds the assumption that normalised '
     'residuals are exchangeable across bins. Neither holds across solar years. Intervals treat unit-bins '
     'as independent, although units share turbines and combiners.')
para('<b>The KAN is minimal.</b> It has no grid refinement, pruning or symbolic extraction, the features that '
     'make KANs interpretable in the original paper. A richer KAN might fit differently, but it would face '
     'the same limit: on own data there is nothing to learn, and on fleet data the trees already capture the '
     'signal.')

heading('9   Reproducibility')
para('Run in sases_eval/: test_kan.py (gate), allowance_derivation.py (worked examples, asserted against the '
     'audit functions), learned_allowance.py dev and confirm (gated against wind/allowance.json and '
     'pv/premise.json before any learned rule is scored), learned_figures.py and learned_pdf.py. Kelmarsh '
     '2018 (Kelmarsh_SCADA_2018_3084.zip, Zenodo 16807551) is built by run_wind_year.py 2018 through the '
     'unchanged build_wind and wind_audit. The protocol and its development log are in '
     'LEARNED_ALLOWANCE_PROTOCOL.md.', LEFT)

story_marker = len(story)


def footer(canvas, doc):
    canvas.setFont('TNR', 9)
    canvas.drawCentredString(LETTER[0] / 2, 35, 'Law allowances: formulas, NN and KAN  |  %s  |  %d' % (DATE, doc.page))


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(OUT), pagesize=LETTER, topMargin=48, bottomMargin=50, leftMargin=75, rightMargin=75,
                      title='Law allowances: formulas, NN and KAN', author='Brandon Rodriguez').build(
        story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == '__main__':
    build()
