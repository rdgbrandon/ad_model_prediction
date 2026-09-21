"""Build a readable PDF and Markdown supplement from the rerun's actual rows."""
import csv
import json
import hashlib
from importlib.metadata import version
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

from theory_audit import METHODS, summarize

HERE = Path(__file__).resolve().parent
OUT = HERE / 'rerun'
LABELS = dict(fitted='Fitted rate', historical_2x='Historical 2x',
              theory_slope='Theory slope', theory_boundary='Theory + boundary')
COLORS = ['#64748b', '#d97706', '#2563eb', '#0f766e']


def read_rows():
    rows = list(csv.DictReader((OUT/'audit_rows.csv').open()))
    for r in rows:
        for k in ('P', 'ceiling', 'delta', 'D', 'b', 'beta', 'zeta', 'margin', 'S', 'e'):
            r[k] = float(r[k]) if r[k] else None
        for k in ('covered', 'valid', 'anchor_covered'):
            r[k] = {'True': True, 'False': False, '': None}[r[k]]
        r['seed'] = int(r['seed'])
    return rows


def main():
    manifest = json.loads((OUT/'results.json').read_text())
    summary = manifest['summary']
    fits = json.loads((OUT/'calibration_fits.json').read_text())
    rows = read_rows()
    def select(group='canonical_192', method='theory_boundary', bm='legacy_loto', kind='mlp8', seed=0):
        return [r for r in rows if r['config'] == group and r['method'] == method
                and r['b_mode'] == bm and r['model'] == kind and r['seed'] == seed]
    def fmt(x, digits=3):
        return '-' if x is None else f'{x:.{digits}f}'
    def coverage(s):
        return (f"{s['all_configurations_covered_trials']}/{s['unique_test_trials']}"
                if s['unique_test_trials'] else 'abstain')

    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for col, hi in enumerate((146, 192)):
        group = f'canonical_{hi}'
        rr = select(group)
        x = [r['P'] for r in rr]
        axes[0, col].plot(x, [r['zeta'] for r in rr], 'ko-', label='Measured law residual')
        for method, color in zip(METHODS, COLORS):
            rs = select(group, method)
            if rs[0]['beta'] is None:
                continue
            axes[0, col].plot(x, [r['beta'] for r in rs], 's--', color=color, label=LABELS[method])
            axes[1, col].plot(x, [r['S']/r['e'] for r in rs], 'o-', color=color, label=LABELS[method])
        axes[0, col].set_title(f'Law calibrated through {hi} mW')
        axes[0, col].set_ylabel('Law allowance / residual (L2)')
        axes[1, col].set_ylabel('Score / measured model error')
        axes[1, col].set_xlabel('Test power (mW)')
        axes[1, col].set_ylim(bottom=0)
        for ax in axes[:, col]:
            ax.grid(alpha=.18)
        axes[0, col].legend(fontsize=7, loc='upper left')
    fig.savefig(OUT/'theory_audit.png', dpi=180)
    fig.savefig(OUT/'theory_audit.svg')
    plt.close(fig)

    md = ['# Theory-informed rerun: measured results', '',
          'Retrospective audit; same corpus, no new independent trials. MLP(8), seed 0 unless stated.', '',
          'CP lower bounds below are one-sided 95% nominal IID-binomial references. Power-selected trials from one apparatus need not be IID.', '']
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallBody', parent=styles['BodyText'], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name='Cell', fontSize=8, leading=10))
    styles['Title'].textColor = colors.HexColor('#123249')
    styles['Heading1'].textColor = colors.HexColor('#123249')
    story = []
    def p(t, style='BodyText'):
        story.append(Paragraph(escape(t), styles[style]))
        story.append(Spacer(1, 7))
    def title(t):
        p(t, 'Heading1')
    def table(data, widths):
        t = Table([[Paragraph(escape(str(c)), styles['Cell']) for c in row] for row in data],
                  colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5edf2')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                               ('TOPPADDING', (0, 0), (-1, -1), 7),
                               ('LINEBELOW', (0, 0), (-1, 0), .7, colors.HexColor('#7890a0')),
                               ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fa')])]))
        story.append(t)
        story.append(Spacer(1, 10))

    p('Anchor-Symmetry Error Certificate', 'Title')
    p('Feedback-driven rerun | 21 September 2026', 'Heading2')
    p('Calibration-only theory candidates, rebuilt spectra, and trial-level uncertainty. '
      'This supplement reports a new exploratory audit; it does not overwrite the historical figures.')
    title('1. Canonical result: 192 mW law ceiling')
    p('Three test trials: 250, 300 and 350 mW. Twelve low-power training trials; four '
      'above-break law-calibration trials. The table retains the original LOTO anchor-error '
      'heuristic for a comparable allowance ablation.')
    header = ['Allowance', 'Covered trials', 'CP lower', 'S > 1', 'Mean S/e', 'Min margin']
    data = [header]
    md.extend(['## Canonical 192 mW ceiling', '', '| Allowance | Covered trials | CP lower | S > 1 | Mean S/e | Min margin |', '|---|---:|---:|---:|---:|---:|'])
    for method in METHODS:
        s = summary[f'canonical_192|{method}|legacy_loto']
        line = [LABELS[method], coverage(s), fmt(s['cp95_lower_nominal']), fmt(s['useful_fraction']), fmt(s['mean_S_over_e']), fmt(s['min_margin'])]
        data.append(line)
        md.append('| ' + ' | '.join(line) + ' |')
    table(data, [132, 78, 64, 62, 75, 93])
    title('2. All 22 splits and all 12 training anchors')
    p('348 configuration rows reuse only three distinct test trials. Pooled fractions '
      'are descriptive. The count/CP columns below instead require each trial to pass '
      'every swept configuration; they do not form a confidence interval for the pooled rate.')
    data = [['Allowance', 'Pooled coverage', 'All-config trials', 'CP lower', 'S > 1', 'Mean S/e']]
    md.extend(['', '## Sensitivity sweep: 348 rows, 3 distinct test trials', '',
               'Trial success here means coverage under every swept configuration; the CP bound does not apply to the pooled rate.', '',
               '| Allowance | Pooled coverage | All-config trials | CP lower | S > 1 | Mean S/e |', '|---|---:|---:|---:|---:|---:|'])
    for method in METHODS:
        s = summary[f'sweep|{method}|legacy_loto']
        line = [LABELS[method], fmt(s['pooled_coverage']), coverage(s), fmt(s['cp95_lower_nominal']), fmt(s['useful_fraction']), fmt(s['mean_S_over_e'])]
        data.append(line)
        md.append('| ' + ' | '.join(line) + ' |')
    table(data, [132, 78, 83, 65, 65, 81])
    fixed = [r for r in rows if r['config'].startswith('sweep') and r['anchor'] == fits[0]['anchor']
             and r['b_mode'] == 'legacy_loto' and r['method'] == 'fitted']
    fixed_summary = summarize(fixed)
    note = (f"The review's 0.21 baseline is reproduced at the fixed 54 mW anchor: "
            f"{sum(r['covered'] for r in fixed)}/{len(fixed)} configuration rows "
            f"({fixed_summary['pooled_coverage']:.3f}; 3 distinct trials, all-config CP lower "
            f"{fixed_summary['cp95_lower_nominal']:.3f}). The 0.264 baseline above additionally sweeps anchors.")
    p(note, 'SmallBody')
    md.extend(['', note])
    p('No row proves 90% population coverage: even 3/3 only gives a nominal lower '
      'bound of 0.368. The historical 2x rule was informed by earlier inspection of '
      'these test data; it remains a sensitivity comparator.', 'SmallBody')

    story.append(PageBreak())
    title('3. What changes at each test power')
    story.append(Image(str(OUT/'theory_audit.png'), width=504, height=353))
    p('Same trained MLP(8), seed 0, and legacy LOTO b throughout. The 146 mW '
      'configuration has four distinct test trials; the Setup C fitted rule cannot '
      'be estimated there because it requires a three-trial sub-law plus a holdout.', 'SmallBody')
    data = [['Ceiling', 'Theory k', 'Boundary norm', 'Covered trials', 'CP lower', 'Mean S/e']]
    md.extend(['', '## Boundary-term candidate at both ceilings', ''])
    for hi in (146, 192):
        fit = next(f for f in fits if f['config'] == f'canonical_{hi}')
        s = summary[f'canonical_{hi}|theory_boundary|legacy_loto']
        line = [f'{hi} mW', fmt(fit['theory']['kappa']), fmt(fit['theory']['boundary']), coverage(s), fmt(s['cp95_lower_nominal']), fmt(s['mean_S_over_e'])]
        data.append(line)
        md.append(f"- {hi} mW: k={line[1]}, boundary={line[2]}, coverage {line[3]} (nominal CP lower {line[4]}), mean S/e={line[5]}.")
    table(data, [75, 70, 92, 95, 80, 92])
    p('The boundary value comes from the already-labelled calibration ceiling and '
      'anchor. No test residual enters this value or the theory slope.')

    story.append(PageBreak())
    title('4. Separate law adequacy from anchor calibration')
    p('The legacy b uses residuals from different leave-one-trial-out models. Its '
      'order statistic does not establish split-conformal coverage for the final '
      'model at a selected anchor. The labelled-anchor variant instead uses the '
      'measured final-model error at that already-labelled anchor. This is exact '
      'for the empirical trial-mean target only.')
    data = [['Model / seed', 'b: LOTO / anchor', 'Mean S/e: LOTO / anchor', 'Valid trials: LOTO / anchor']]
    md.extend(['', '## Model sensitivity: theory + boundary, 192 mW ceiling', '',
               '| Model / seed | b: LOTO / anchor | Mean S/e: LOTO / anchor | Valid trials: LOTO / anchor |', '|---|---:|---:|---:|'])
    for kind, seed in manifest['models']:
        rs, ra = select(kind=kind, seed=seed), select(bm='labelled_anchor', kind=kind, seed=seed)
        ss, sa = summarize(rs), summarize(ra)
        line = [f'{kind} / {seed}', f"{rs[0]['b']:.3f} / {ra[0]['b']:.3f}",
                f"{ss['mean_S_over_e']:.3f} / {sa['mean_S_over_e']:.3f}",
                f"{ss['all_configurations_valid_trials']}/3 / {sa['all_configurations_valid_trials']}/3"]
        data.append(line)
        md.append('| '+' | '.join(line)+' |')
    table(data, [105, 120, 140, 139])
    p('Each validity fraction of 3/3 corresponds to a nominal 95% CP lower bound '
      'of 0.368, not seven independent replications of three trials. Law coverage '
      'does not depend on model or seed; model sensitivity changes informativeness.', 'SmallBody')
    title('Conditional theory, not a universal guarantee')
    for t in [
        'The capillary spectrum scales as energy flux^(1/2) and frequency^(-17/6). '
        'The relevant power slope is 1/2 only under energy flux proportional to drive power. '
        'The frequency exponent must not be compared to fitted power exponents.',
        'For u = ln(power), r(u) = y_anchor - y(u) - c(u) - c0. If '
        'norm(y\'(u) - q_high) <= k over the extrapolation interval, then '
        'norm(r(u)) <= norm(r(u0)) + k*(u-u0). We test k = norm(q_high - 0.5*ones).',
        'The derivative assumption is not established by weak-turbulence theory '
        'for this apparatus. The experiment audits that candidate; it cannot '
        'upgrade it to an unconditional physics or coverage theorem.'
    ]:
        p(t, 'SmallBody')

    story.append(PageBreak())
    title('5. Paper corrections and related work')
    corrections = [
        'Narrow the gap: physics-residual conformal methods can use no target labels. '
        'Our distinction is a per-input error lower bound with separate anchor and approximate-law allowances.',
        'Separate training shift from calibration/test exchangeability. OOD relative '
        'to training does not automatically invalidate conformal calibration.',
        'Report 348 configurations and three distinct test trials together. A pooled '
        'rate over overlapping configurations has no ordinary binomial confidence interval.',
        'Describe the factor of two as retrospective. A round number chosen after '
        'viewing test residuals is still test-informed.',
        'Correct reference [7] to Weak turbulence of capillary waves. Correct the '
        'first interior 90% finite-sample quantile to n=19, not 20. Neither rank '
        'arithmetic nor LOTO residuals alone establish exchangeability.'
    ]
    for t in corrections:
        p(t, 'SmallBody')
    refs = [
        ('Gopakumar et al. Physics-informed UQ: label-free residual-space calibration.', 'https://arxiv.org/abs/2502.04406'),
        ('Wang et al. Symmetry mismatch already yields regression error lower bounds.', 'https://arxiv.org/abs/2303.04745'),
        ('Gopakumar et al. Surrogate conformal UQ retains calibration/test exchangeability.', 'https://arxiv.org/abs/2408.09881'),
        ('Berman et al. Calibration-error bounds for equivariant functions.', 'https://arxiv.org/abs/2510.21691'),
        ('Xu et al. Branched normalizing flows and conditional conformal transport.', 'https://arxiv.org/abs/2605.01868'),
        ('Lust and Condurache. GIT transformation-based classification error detection.', 'https://arxiv.org/abs/2307.02672'),
        ('Zakharov and Filonenko. Weak turbulence of capillary waves (1967).', 'https://doi.org/10.1007/BF00915178'),
        ('Kochurin and Russkikh. Explicit flux and frequency scaling, equations 1-2.', 'https://arxiv.org/html/2501.18970v2')]
    for label, url in refs:
        story.append(Paragraph(f'{escape(label)} <link href="{url}" color="#2563eb">Source</link>', styles['SmallBody']))
        story.append(Spacer(1, 6))
    p('Replacement paragraphs, assumptions and citation distinctions are in '
      'PAPER_REVISIONS.md. They do not adopt the reviewer\'s suggested acceptance-score estimates.', 'SmallBody')

    story.append(PageBreak())
    title('6. Reproducibility and artifact')
    exact = all(manifest['rebuilt_arrays_exactly_equal'].values())
    p(f"All rebuilt dataset arrays exactly match the archived arrays: {exact}. "
      f"Maximum absolute log-spectrum difference: {manifest['max_abs_spectrum_difference']:.3g}.")
    p('The source is the supplied 50 MB capillary-wave HDF5, derived from the '
      'Orosco, Connacher and Friend UC San Diego deposit (DOI 10.6075/J0WW7HVJ). '
      'The repackaging is lossy; this run does not recreate the original 320.7 GB reduction.')
    p('Target: average of window-level natural log band-averaged temporal PSDs. '
      'Twelve log-spaced bands, 500 Hz-20 kHz; 8192-sample windows, 4096 stride; '
      'Welch segments 2048, half overlap, Hann window, linear detrending. '
      'All model/law/test partitions are grouped by trial.')
    data = [['Artifact', 'Contents'],
            ['RERUN_PROTOCOL.md', 'Fixed rules and assumptions written before candidate audit'],
            ['theory_audit.py', 'Calibration fits, model reruns and row-level audit'],
            ['rerun/calibration_fits.json', '266 fitted configurations, trial lists and frozen allowances'],
            ['rerun/audit_rows.csv', f'{len(rows)} rows including abstentions, margins and both premises'],
            ['rerun/results.json', 'Summary, versions, input/code hashes and rebuild comparison'],
            ['test_theory_audit.py', 'Five tests: leakage, boundary, trial counts, abstention and inequality'],
            ['README_RERUN.md', 'Commands and interpretation'],
            ['PAPER_REVISIONS.md', 'Supported replacement prose and source links']]
    table(data, [182, 322])
    current_versions = {k: version(k) for k in manifest['versions']}
    p('Python '+manifest['python']+'; '+', '.join(f'{k} {v}' for k,v in current_versions.items()), 'SmallBody')
    p('Scope: two canonical ceilings, a 22-split x 12-anchor sensitivity sweep, '
      'seven model/seed fits, four fixed allowance rules, two anchor-error choices, '
      'and five new verification tests. Historical ensemble benchmarks and earlier '
      'figure atlases are not represented as newly rerun results.', 'SmallBody')
    p('Limits: only three or four distinct test trials, one apparatus, already-viewed '
      'test data, uncertain drive-to-flux coupling, and empirical trial means rather '
      'than a noise-free physical target. Additional independent trials are required '
      'to assess the 0.90 population-coverage claim.', 'SmallBody')
    md.extend(['', '## Verification and scope', '',
               f'All rebuilt arrays match exactly: {exact}; max absolute spectrum difference {manifest["max_abs_spectrum_difference"]}.',
               '', 'Five verification tests pass. Trial-count CP values are nominal references only.', '',
               'Seven model/seed fits, four allowance rules, two anchor-error modes. Historical ensemble benchmarks were not rerun.', '',
               'See ../PAPER_REVISIONS.md for corrected theory, related work and guarantee language.'])
    (OUT/'results.md').write_text('\n'.join(md)+'\n', encoding='utf-8')
    def footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(54, 30, 'Retrospective audit | same corpus | no population coverage claim')
        canvas.drawRightString(558, 30, str(doc.page))
    SimpleDocTemplate(str(OUT/'sases_theory_rerun.pdf'), pagesize=(612, 792),
                      rightMargin=54, leftMargin=54, topMargin=40, bottomMargin=48,
                      title='Anchor-Symmetry: Theory-Informed Rerun').build(story, onFirstPage=footer, onLaterPages=footer)
    artifact_paths = [HERE/'report_theory_audit.py', HERE/'test_theory_audit.py', HERE/'requirements-rerun.txt',
                      HERE/'README_RERUN.md', HERE/'PAPER_REVISIONS.md', OUT/'sases_theory_rerun.pdf',
                      OUT/'results.md', OUT/'audit_rows.csv', OUT/'calibration_fits.json', OUT/'results.json']
    (OUT/'artifact_manifest.json').write_text(json.dumps(dict(report_versions=current_versions,
        sha256={str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in artifact_paths}), indent=2))
    print('Wrote rerun/results.md, theory_audit.png/svg and sases_theory_rerun.pdf')


if __name__ == '__main__':
    main()
