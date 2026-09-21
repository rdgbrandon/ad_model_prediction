"""Build the plain-language summary PDF from the published audit results.

Reads sases_eval/consensus/results.json and web/data/snapshot.json so the
figures and every quoted number stay tied to the committed run.

    python make_summary_pdf.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether,
                                PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

ROOT = Path(__file__).resolve().parent
FIG = ROOT / 'figures_summary'
FIG.mkdir(exist_ok=True)

# Validated categorical slots 1-3 from the data-viz reference palette,
# plus its chart chrome. Checked with scripts/validate_palette.js --mode light.
BLUE, ORANGE, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
INK, SECOND, MUTED = '#0b0b0b', '#52514e', '#898781'
GRID, BASELINE, SURFACE = '#e1e0d9', '#c3c2b7', '#fcfcfb'

MODEL_LABEL = {'linear': 'Straight-line model',
               'mlp8': 'Small neural network',
               'mlp16x16': 'Larger neural network'}

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Segoe UI', 'DejaVu Sans'],
    'font.size': 9,
    'axes.edgecolor': BASELINE,
    'axes.labelcolor': SECOND,
    'text.color': INK,
    'xtick.color': MUTED,
    'ytick.color': MUTED,
    # White so the figure blends into the printed page rather than sitting in
    # a visible grey panel.
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
})


def load():
    consensus = json.loads((ROOT / 'sases_eval/consensus/results.json').read_text())
    snapshot = json.loads((ROOT / 'web/data/snapshot.json').read_text())
    return consensus, snapshot


def fig_results(consensus):
    """Headline: how much of the mistake each rule set can account for."""
    order = [('linear', 0), ('mlp16x16', 0), ('mlp16x16', 1), ('mlp16x16', 2),
             ('mlp8', 0), ('mlp8', 1), ('mlp8', 2)]
    labels, one, several = [], [], []
    for model, seed in order:
        s = consensus['summary']['canonical_192|%s|%d' % (model, seed)]
        name = MODEL_LABEL[model]
        if model != 'linear':
            name += '  (run %d)' % seed
        labels.append(name)
        one.append(s['baseline_mean_S_over_e'] * 100)
        several.append(s['mean_S_over_e'] * 100)

    y = np.arange(len(labels))[::-1]
    height = 0.36
    fig, ax = plt.subplots(figsize=(7.1, 3.7))
    ax.barh(y + height / 2 + 0.02, one, height, label='Using one rule',
            color=BLUE, zorder=3)
    ax.barh(y - height / 2 - 0.02, several, height, label='Using several rules',
            color=ORANGE, zorder=3)

    for yi, a, b in zip(y, one, several):
        ax.text(a + 1.2, yi + height / 2 + 0.02, '%.0f%%' % a, va='center',
                ha='left', fontsize=8, color=SECOND)
        gain = b - a
        tag = '%.0f%%' % b + ('   +%.1f' % gain if gain > 0.05 else '')
        ax.text(b + 1.2, yi - height / 2 - 0.02, tag, va='center', ha='left',
                fontsize=8, color=SECOND)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.5, color=INK)
    # Headroom so the value labels never run into the axis edge.
    ax.set_xlim(0, 108)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'], fontsize=8)
    ax.set_xlabel('Share of the real mistake we can prove, on average', fontsize=8.5)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis='y', length=0)
    # Above the plot: inside the axes the legend collides with the lowest bars.
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.01), frameon=False,
              fontsize=8.5, ncol=2, handlelength=1.1, columnspacing=1.6)
    fig.tight_layout()
    out = FIG / 'results.png'
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def fig_corpus(snapshot):
    """Where the 20 experiments sit, and what each one is used for."""
    roles = [('Not used here', '#b9b7b0'), ('Teach the model', BLUE),
             ('Build the checking rules', ORANGE), ('Check the answers', AQUA)]
    train = {12.25, 15.5, 18.5, 21.7, 24.3, 26.0, 28.0, 36.0, 41.0, 46.0, 54.0}
    calib = {106.0, 125.0, 146.0, 192.0}
    test = {250.0, 300.0, 350.0}

    fig, ax = plt.subplots(figsize=(7.1, 1.95))
    for t in snapshot['dataset']['trials']:
        p = t['power']
        if p in test:
            c, r = AQUA, 3
        elif p in calib:
            c, r = ORANGE, 2
        elif p in train:
            c, r = BLUE, 1
        else:
            c, r = '#b9b7b0', 0
        ax.scatter([p], [0], s=115, color=c, zorder=3,
                   edgecolors=SURFACE, linewidths=1.6)

    ax.annotate('12 experiments teach the model', xy=(26, 0.055), fontsize=8,
                color=BLUE, ha='center')
    ax.annotate('4 build the rules', xy=(140, -0.078), fontsize=8,
                color=ORANGE, ha='center')
    ax.annotate('3 are the real test', xy=(292, 0.055), fontsize=8,
                color='#0f7d57', ha='center')
    ax.annotate('not used', xy=(7.0, -0.078), fontsize=8,
                color='#8a8880', ha='center')

    ax.set_xscale('log')
    ax.set_xlim(5.5, 460)
    ax.set_ylim(-0.14, 0.13)
    ax.set_yticks([])
    ax.set_xticks([10, 30, 100, 300])
    ax.set_xticklabels(['10 mW', '30 mW', '100 mW', '300 mW'], fontsize=8)
    ax.set_xlabel('Power pushing the liquid surface (stronger to the right)',
                  fontsize=8.5)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    out = FIG / 'corpus.png'
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def fig_idea():
    """The whole idea in one picture: a guess outside the possible-answer circle."""
    fig, ax = plt.subplots(figsize=(7.1, 2.6))
    cx, cy, r = 0.27, 0.5, 0.155
    ax.add_patch(plt.Circle((cx, cy), r, facecolor='#e8f3ff',
                            edgecolor=BLUE, linewidth=2, zorder=2))
    ax.plot([cx], [cy], marker='o', ms=7, color=BLUE, zorder=4)
    ax.text(cx, cy - r - 0.085, 'Where the real answer should be',
            ha='center', fontsize=8.5, color=BLUE)
    ax.text(cx, cy + r + 0.055, 'Built only from earlier measurements',
            ha='center', fontsize=8, color=MUTED)

    gx, gy = 0.80, 0.5
    ax.plot([gx], [gy], marker='D', ms=9, color=ORANGE, zorder=4)
    ax.text(gx, gy - 0.10, "The computer's guess", ha='center',
            fontsize=8.5, color=ORANGE)

    ax.annotate('', xy=(gx - 0.022, gy), xytext=(cx + r, cy),
                arrowprops=dict(arrowstyle='<->', color=INK, linewidth=1.4))
    ax.text((cx + r + gx) / 2, gy + 0.062,
            'The guess must be wrong by at least this much',
            ha='center', fontsize=9, color=INK)

    ax.set_xlim(0, 1.0)
    ax.set_ylim(0.22, 0.78)
    # Without this the circle renders as an ellipse, which breaks the metaphor.
    ax.set_aspect('equal', adjustable='box')
    ax.axis('off')
    fig.tight_layout()
    out = FIG / 'idea.png'
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# Document
# --------------------------------------------------------------------------

def styles():
    ss = getSampleStyleSheet()
    s = {}
    s['title'] = ParagraphStyle('t', parent=ss['Title'], fontName='Helvetica-Bold',
                                fontSize=23, leading=27, textColor=colors.HexColor(INK),
                                alignment=0, spaceAfter=4)
    s['sub'] = ParagraphStyle('sub', parent=ss['Normal'], fontName='Helvetica',
                              fontSize=11, leading=15, textColor=colors.HexColor(SECOND),
                              spaceAfter=14)
    s['h'] = ParagraphStyle('h', parent=ss['Heading1'], fontName='Helvetica-Bold',
                            fontSize=13.5, leading=17, textColor=colors.HexColor(INK),
                            spaceBefore=15, spaceAfter=6)
    s['h2'] = ParagraphStyle('h2', parent=ss['Heading2'], fontName='Helvetica-Bold',
                             fontSize=10.5, leading=14, textColor=colors.HexColor(INK),
                             spaceBefore=10, spaceAfter=4)
    s['body'] = ParagraphStyle('b', parent=ss['Normal'], fontName='Helvetica',
                               fontSize=10, leading=14.6, textColor=colors.HexColor('#1a1a18'),
                               alignment=TA_JUSTIFY, spaceAfter=8)
    s['cap'] = ParagraphStyle('c', parent=ss['Normal'], fontName='Helvetica-Oblique',
                              fontSize=8.5, leading=12, textColor=colors.HexColor(MUTED),
                              spaceAfter=10)
    s['pull'] = ParagraphStyle('p', parent=ss['Normal'], fontName='Helvetica-Bold',
                               fontSize=11.5, leading=16, textColor=colors.HexColor('#0f4f8f'),
                               spaceBefore=4, spaceAfter=10, leftIndent=10)
    s['note'] = ParagraphStyle('n', parent=ss['Normal'], fontName='Helvetica',
                               fontSize=9.3, leading=13.4, textColor=colors.HexColor('#3d3b36'),
                               alignment=TA_JUSTIFY, leftIndent=9, rightIndent=9,
                               spaceBefore=5, spaceAfter=5)
    s['bullet'] = ParagraphStyle('bu', parent=s['body'], leftIndent=16,
                                 bulletIndent=4, spaceAfter=6)
    s['small'] = ParagraphStyle('s', parent=ss['Normal'], fontName='Helvetica',
                                fontSize=8.4, leading=11.6,
                                textColor=colors.HexColor(MUTED), spaceAfter=4,
                                leftIndent=14, bulletIndent=3)
    return s


def boxed(flowables, fill='#f2f6fb', line='#c8dcf0'):
    t = Table([[flowables]], colWidths=[6.9 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(fill)),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor(line)),
        ('LEFTPADDING', (0, 0), (-1, -1), 11),
        ('RIGHTPADDING', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def data_table(rows, widths, align_right=(), header=True, s=None):
    # Plain strings in a Table do not wrap; they run straight over the next
    # column. Every cell becomes a Paragraph so the column widths are honoured.
    cell = ParagraphStyle('cell', fontName='Helvetica', fontSize=8.6,
                          leading=11.4, textColor=colors.HexColor('#1a1a18'))
    head = ParagraphStyle('cellh', parent=cell, fontName='Helvetica-Bold',
                          textColor=colors.HexColor(INK))
    wrapped = []
    for i, row in enumerate(rows):
        style = head if (header and i == 0) else cell
        wrapped.append([c if hasattr(c, 'wrap')
                        else Paragraph(str(c).replace('\n', '<br/>'), style)
                        for c in row])
    t = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.6),
        ('LEADING', (0, 0), (-1, -1), 11.4),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a18')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, colors.HexColor(GRID)),
    ]
    if header:
        style += [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(INK)),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0efe9')),
            ('LINEBELOW', (0, 0), (-1, 0), 0.8, colors.HexColor(BASELINE)),
        ]
    for col in align_right:
        style.append(('ALIGN', (col, 0), (col, -1), 'RIGHT'))
    t.setStyle(TableStyle(style))
    return t


def build(consensus, snapshot, figs):
    s = styles()
    story = []
    p = lambda text, st='body': story.append(Paragraph(text, s[st]))

    c192 = lambda m, seed: consensus['summary']['canonical_192|%s|%d' % (m, seed)]
    lin, big1, sm0 = c192('linear', 0), c192('mlp16x16', 1), c192('mlp8', 0)

    # ---------------- Page 1 ----------------
    p('How Wrong Is the Computer&rsquo;s Guess?', 'title')
    p('A plain-language summary of a method that proves a prediction is wrong by '
      'at least a certain amount &mdash; what it achieves, where it falls short, '
      'and how it compares with the other approaches people use.', 'sub')

    p('The short version', 'h')
    p('Scientists shook a liquid surface harder and harder and recorded the tiny '
      'waves that appeared. A computer model learned from the gentle shakes and '
      'was then asked to predict what the strong shakes would look like. The usual '
      'question is &ldquo;was the prediction right?&rdquo; This project asks a '
      'different and much harder one:')
    story.append(boxed([Paragraph(
        'Without looking at the answer, can we prove the prediction is wrong &mdash; '
        'and by at least how much?', s['pull'])]))
    story.append(Spacer(1, 10))
    p('The answer is yes, but only if you are willing to assume something about '
      'the physics. The method now accounts for roughly <b>%.0f%%</b> of the '
      'straight-line model&rsquo;s real mistake and about <b>%.0f%%</b> of the '
      'small neural network&rsquo;s, using nothing but earlier measurements. The '
      'catch is that the whole thing rests on an assumption that has only been '
      'checked on three or four experiments.'
      % (lin['mean_S_over_e'] * 100, sm0['mean_S_over_e'] * 100))

    p('What was actually measured', 'h')
    p('Twenty recordings were made of a liquid surface driven at different powers, '
      'from a gentle 7 milliwatts to a strong 350. Each recording gets turned into '
      'a &ldquo;fingerprint&rdquo;: twelve numbers describing how much the surface '
      'wobbles slowly versus quickly. The model&rsquo;s job is to predict that '
      'fingerprint for a power it has never seen.')
    story.append(Image(str(figs['corpus']), width=6.9 * inch, height=1.89 * inch))
    p('The twenty experiments and what each is used for. Note how far the three '
      'test experiments sit from everything the model learned on &mdash; that gap '
      'is the whole difficulty.', 'cap')

    story.append(boxed([
        Paragraph('One number to keep in mind', s['h2']),
        Paragraph('Everything below is measured as a <b>share of the real mistake '
                  'we can prove</b>. If the model&rsquo;s prediction was actually '
                  'off by 10 units and our method proves it was off by at least 8, '
                  'that is 80%. It is <i>not</i> a measure of how accurate the '
                  'model is &mdash; a high score means our warning is informative, '
                  'not that the prediction is good. 0% means we cannot prove '
                  'anything, which is not the same as the prediction being right.',
                  s['note'])], fill='#f7f6f0', line='#ddd9cb'))

    story.append(PageBreak())

    # ---------------- Page 2 ----------------
    p('How the method works', 'h')
    p('Imagine a friend tells you a hidden target is somewhere inside a circle '
      'drawn on a map. You do not know exactly where the target is, but you know '
      'the circle. Now someone guesses a spot far outside that circle. Even if the '
      'target sits at the very nearest edge, the guess is still wrong by the gap '
      'between the guess and the circle. You can state a minimum error without '
      'ever being told the true location.')
    story.append(Image(str(figs['idea']), width=6.9 * inch, height=2.53 * inch))
    p('The entire method in one picture. The circle comes from measurements we '
      'already had; the diamond is the prediction being judged.', 'cap')

    p('Where the circle comes from', 'h2')
    p('The four experiments at 106, 125, 146 and 192 milliwatts were already '
      'measured, so their answers are known. Physics suggests the fingerprint '
      'should drift in a predictable direction as you turn the power up. Starting '
      'from the strongest measured experiment and drifting along that expected '
      'direction gives the centre of the circle. How much the drift rule might be '
      'off gives its radius. Push further past what was measured and the circle '
      'grows, which is exactly right: the further you extrapolate, the less you '
      'should claim.')
    p('Crucially, the true answer for the test experiment is never used to compute '
      'the warning. It is unsealed afterwards, only to check whether it really did '
      'land inside the circle.')

    p('Why bother, if you could just measure it?', 'h2')
    p('Because in real use there is nothing to measure. A model like this exists '
      'so that someone can skip the experiment &mdash; predict the outcome at a '
      'setting nobody has run, and act on it. At that moment there is no answer '
      'to check against, and the model will happily produce a confident-looking '
      'prediction whether or not it has any idea what it is doing.')
    p('A warning built only from old measurements is something you can actually '
      'have in that situation. It will never tell you a prediction is good '
      '&mdash; it can only catch predictions that are provably bad. A silent '
      'warning means &ldquo;no proof of error found here&rdquo;, which is a much '
      'weaker statement than &ldquo;this prediction is fine.&rdquo;')

    story.append(PageBreak())

    # ---------------- Page 3 ----------------
    p('The results', 'h')
    story.append(Image(str(figs['results']), width=6.9 * inch, height=3.59 * inch))
    p('Each row is one model, at the setting where the checker may use '
      'measurements up to 192 milliwatts. Longer bars mean a more informative '
      'warning. The orange bars are the newest method, described just below.',
      'cap')
    p('The straight-line model is a deliberately poor predictor, so its mistakes '
      'are large and easy to prove. The larger neural network is the most accurate '
      'of the three, and there the method struggles: its errors are small enough '
      'to hide inside the circle, so little or nothing can be proven. That is the '
      'honest shape of the result &mdash; <b>the worse the model, the louder the '
      'warning</b>.')

    p('The newest experiment: combining several rules', 'h')
    p('Until recently the checker fitted one drift rule using all four calibration '
      'experiments. The new idea: fit a separate rule on <i>every</i> group of at '
      'least three of them, then report whichever gives the strongest provable '
      'error. Because the choice uses only the prediction and the earlier '
      'measurements, it is still fair &mdash; no peeking at the answer.')
    p('It worked, modestly. For the straight-line model the provable share rose '
      'from <b>%.1f%%</b> to <b>%.1f%%</b>. For one run of the larger neural '
      'network it rose from <b>%.1f%%</b> to <b>%.1f%%</b>. The small neural '
      'network barely moved.' % (lin['baseline_mean_S_over_e'] * 100,
                                 lin['mean_S_over_e'] * 100,
                                 big1['baseline_mean_S_over_e'] * 100,
                                 big1['mean_S_over_e'] * 100))

    p('Three reasons not to celebrate too hard', 'h2')
    for head, text in [
        ('The number cannot go down.',
         'The original single rule is one of the candidates being compared, and we '
         'report the best candidate. So this comparison can only show an increase '
         'or no change. A gain of zero is the floor of the test, not a failure of '
         'the method.'),
        ('The clever part did nothing.',
         'The method includes machinery for blending several circles together. '
         'Across all 78 checks, blending beat simply picking the single best '
         'circle by at most 0.0008 &mdash; against typical mistakes of about 13. '
         'Essentially the entire gain comes from picking one group: the three '
         'experiments at 125, 146 and 192 milliwatts, dropping the 106 one.'),
        ('One setting could not improve at all.',
         'When the checker may only use measurements up to 146 milliwatts it has '
         'three calibration experiments, and there is exactly one way to choose '
         'three from three. Its zero change is arithmetic, not evidence.'),
    ]:
        story.append(Paragraph('<b>%s</b> %s' % (head, text), s['bullet'],
                               bulletText='•'))

    story.append(Spacer(1, 4))
    story.append(boxed([
        Paragraph('And the price: a stronger assumption', s['h2']),
        Paragraph('The old method needed the answer to be inside <b>one</b> '
                  'circle. The new one needs it inside <b>all five at once</b> '
                  '(up to 42 in the widest test). That held every single time we '
                  'checked &mdash; but in the tightest case the answer cleared the '
                  'circle&rsquo;s edge by only 0.20 units, where the comfortable '
                  'cases had room of 1.1 to 1.9. Squeezing a better number out '
                  'also squeezes the assumption holding it up.', s['note'])],
        fill='#fdf4ee', line='#f0cdb4'))

    p('A trap worth naming', 'h2')
    p('It is tempting to report &ldquo;the proven minimum never exceeded the real '
      'error, 78 times out of 78&rdquo; as if that were a successful test. It is '
      'not. When the answer is inside the circles, the mathematics <i>guarantees</i> '
      'the minimum cannot exceed the real error &mdash; the code checks this as an '
      'internal consistency check, not as evidence. There is really only one thing '
      'being tested here: did the answer land inside the circles? It did, on three '
      'to four distinct experiments. That is the whole evidence base.')

    p('How this compares with other methods', 'h')
    p('Almost every well-known technique answers the opposite question. They say '
      '&ldquo;the true answer is probably within this range&rdquo; &mdash; an '
      '<i>upper</i> limit on how wrong you might be. This project produces a '
      '<i>lower</i> limit: proof that you are definitely wrong by at least some '
      'amount. Very few methods do that, and there is a good mathematical reason '
      'why.')

    rows = [
        ['Approach', 'What it tells you', 'What it needs', 'How it compares here'],
        ['Conformal prediction\n(the standard tool)',
         'A range the answer probably falls in, with a stated success rate',
         'Typically 100-1000 measured examples that resemble the test case',
         'Far stronger guarantees, but needs hundreds of examples. This project '
         'has 3-4, so the standard route is simply unavailable'],
        ['Ensembles and Bayesian\nneural networks',
         'A spread of opinions across many models, read as confidence',
         'Lots of training and retraining; no measured answers needed',
         'Cheap and popular, but known to be overconfident exactly where this '
         'project operates: far outside the training range'],
        ['Physics-residual methods\n(e.g. calibrated PINN uncertainty)',
         'How badly the prediction violates a known equation',
         'The governing equation written down explicitly',
         'Needs no answers at all, which is better. But it scores violation of '
         'the equation, not the actual error, and no exact equation is available '
         'for these waves'],
        ['Certified error bounds\nfor physics networks',
         'A rigorous ceiling on the error',
         'The exact equation plus a stability constant',
         'Genuinely rigorous, but an upper limit, and reported as loose in '
         'practice. Different question from this one'],
        ['This project',
         'A floor: proof the prediction is off by at least this much',
         'A handful of measured examples plus a physics-based drift assumption',
         'Works with very little data and answers the rarer question. Pays for it '
         'with an assumption that is hard to verify'],
    ]
    story.append(data_table(rows, [1.32 * inch, 1.5 * inch, 1.45 * inch, 2.63 * inch]))
    story.append(Spacer(1, 12))

    # Keep this heading with its first paragraph; on its own it lands as an
    # orphan at the foot of the page.
    story.append(KeepTogether([
        Paragraph('Why the assumption is not a sloppy shortcut', s['h2']),
        Paragraph(
            'A 2025 theory paper asked whether you can prove a model is wrong '
            'without assuming anything about the underlying problem. The answer '
            'is essentially no. Once a family of models is flexible enough to '
            'fit far more data than you have, every assumption-free lower bound '
            'collapses to the useless statement &ldquo;the error is at least '
            'zero.&rdquo; Their threshold is sharp: it bites once the models '
            'could fit roughly the square of your sample size.', s['body'])]))
    story.append(boxed([Paragraph(
        'So the physics assumption in this project is not a corner being cut. '
        'Some such assumption is <i>mathematically required</i> for this kind of '
        'claim to say anything at all. The fair criticism is not that an '
        'assumption exists &mdash; it is that this particular one has been tested '
        'on only three or four experiments.', s['note'])],
        fill='#f2f6fb', line='#c8dcf0'))

    p('A related idea', 'h2')
    p('One other line of work does derive genuine error floors: when a network is '
      'built to assume a symmetry that the real world only partly has, that '
      'mismatch forces a minimum error. The spirit is the same &mdash; a '
      'structural assumption about the world converted into a provable floor. '
      'This project differs in getting its structure from measured calibration '
      'experiments rather than from a symmetry group.')

    p('The honest bottom line', 'h')

    rows = [
        ['Claim', 'Status'],
        ['The arithmetic is correct',
         'Solid. The geometry is a standard inequality, and the awkward cases '
         '(contradictory circles, ties, the no-improvement case) are covered by '
         'unit tests. The published numbers reproduce exactly from a clean copy.'],
        ['The improvement is real and fairly earned',
         'Yes. No test answer influences the score or the choice of rule. But it '
         'is modest, it cannot come out negative, and it comes from picking a '
         'group rather than from the blending machinery.'],
        ['The warnings were correct on the data',
         'Yes, on every one of the 78 checks. Note that this is 3-4 distinct '
         'experiments; the 78 comes from repeating across models, random starts '
         'and overlapping splits, which add no new evidence.'],
        ['The method will work on new experiments',
         'Not established, and not establishable with this data. Three successes '
         'out of three support a success-rate floor of only about 37%, and even '
         'that figure assumes the experiments are independent, which experiments '
         'chosen by turning one dial on one rig are not.'],
    ]
    story.append(data_table(rows, [2.0 * inch, 4.9 * inch]))
    story.append(Spacer(1, 12))

    p('One thing that genuinely improved', 'h2')
    p('In an earlier version of this work, the proven minimum was so far below the '
      'real error that the check passed no matter what &mdash; it could not have '
      'detected a broken assumption. That is no longer true. The proven minimum '
      'now comes within about 1.0 unit of the real error in the tightest case, and '
      'exceeds 90% of it in 16 of the 78 checks. The check now has teeth.')

    p('What would actually settle it', 'h2')
    for text in [
        'More high-power experiments. Around 30 independent test cases would be '
        'needed before any claim about a success rate is even measurable. The '
        'current corpus has three.',
        'Experiments from a second apparatus. Everything here comes from one rig, '
        'and the data had already been examined before these checks were designed.',
        'A test where the assumption is expected to fail. Every check so far '
        'passed, which is encouraging but also means the premise has never been '
        'observed breaking. A method that has never been seen to fail has not '
        'really been stress-tested.',
    ]:
        story.append(Paragraph(text, s['bullet'], bulletText='•'))

    story.append(Spacer(1, 12))
    story.append(boxed([
        Paragraph('In one sentence', s['h2']),
        Paragraph('The method does something unusual and useful &mdash; it turns '
                  'a few old measurements into proof that a prediction is wrong '
                  '&mdash; the newest change made it modestly sharper in a way '
                  'that is real but partly automatic, and the honest limit is not '
                  'the mathematics but the three experiments it rests on.',
                  s['note'])], fill='#f7f6f0', line='#ddd9cb'))

    story.append(Spacer(1, 16))
    sources = [Paragraph('Sources for the comparison', s['h2'])]
    for text in [
        'Gopakumar et al., <i>Uncertainty Quantification of Surrogate Models using '
        'Conformal Prediction</i> (arXiv:2408.09881).',
        'Gopakumar et al., <i>Calibrated Physics-Informed Uncertainty '
        'Quantification</i> (arXiv:2502.04406).',
        'M&uuml;ller et al., <i>Are All Models Wrong? Fundamental Limits in '
        'Distribution-Free Empirical Model Falsification</i> (arXiv:2502.06765, '
        'COLT 2025) &mdash; the impossibility result.',
        'Certified machine learning: <i>A posteriori error estimation for '
        'physics-informed neural networks</i> (arXiv:2203.17055).',
        'Wang et al., <i>A General Theory of Correct, Incorrect, and Extrinsic '
        'Equivariance</i> (arXiv:2303.04745) &mdash; error floors from symmetry '
        'mismatch.',
        'Wave measurements: UC San Diego deposit, doi.org/10.6075/J0WW7HVJ. '
        'Code and full results: github.com/rdgbrandon/ad_model_prediction.',
    ]:
        sources.append(Paragraph(text, s['small'], bulletText='•'))
    # Keep the reference list from splitting across a page boundary.
    story.append(KeepTogether(sources))

    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 7.6)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(0.85 * inch, 0.52 * inch,
                      'How Wrong Is the Computer’s Guess?  |  '
                      'Plain-language summary of the capillary-wave error study')
    canvas.drawRightString(7.65 * inch, 0.52 * inch, 'Page %d' % doc.page)
    canvas.setStrokeColor(colors.HexColor(GRID))
    canvas.setLineWidth(0.5)
    canvas.line(0.85 * inch, 0.70 * inch, 7.65 * inch, 0.70 * inch)
    canvas.restoreState()


def main():
    consensus, snapshot = load()
    figs = {'results': fig_results(consensus),
            'corpus': fig_corpus(snapshot),
            'idea': fig_idea()}
    out = ROOT / 'How_Wrong_Is_The_Guess.pdf'
    doc = BaseDocTemplate(str(out), pagesize=LETTER,
                          leftMargin=0.85 * inch, rightMargin=0.85 * inch,
                          topMargin=0.75 * inch, bottomMargin=0.85 * inch,
                          title='How Wrong Is the Computer’s Guess?',
                          author='Capillary-wave error-certificate study')
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id='body')
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=footer)])
    doc.build(build(consensus, snapshot, figs))
    print('Wrote', out)


if __name__ == '__main__':
    main()
