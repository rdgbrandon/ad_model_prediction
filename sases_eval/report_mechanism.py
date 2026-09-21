"""Publish mechanism findings ahead of the prior results supplement."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import fitz
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image

HERE=Path(__file__).resolve().parent
OUT=HERE/'mechanism'


def main():
    data=json.loads((OUT/'results.json').read_text())
    styles=getSampleStyleSheet()
    styles['BodyText'].fontSize=10
    styles['BodyText'].leading=14
    story=[]
    md=['# Mechanism-checked results','',
        'The boundary correction is supported by new ablations and measured-interval checks. '
        'The specific KZ exponent is not identified by these data. This remains retrospective.', '']
    def p(t,style='BodyText'):
        story.append(Paragraph(escape(t),styles[style]));story.append(Spacer(1,8))
    def table(rows,widths):
        t=Table([[Paragraph(escape(str(x)),styles['BodyText']) for x in row] for row in rows],colWidths=widths)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf2')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.append(t);story.append(Spacer(1,10))
    p('Mechanism-checked error allowance','Title')
    p('New audit | 21 September 2026','Heading2')
    p('The previous 100% result survives direct checks of the proposed growth mechanism '
      'at the measured powers. Ablations show that correcting the boundary condition '
      'accounts for most of the coverage gain. They do not identify the KZ exponent as uniquely responsible.')
    p('Ablation: what actually supplies coverage?','Heading2')
    labels={'boundary_only':'Boundary only','fitted_plus_boundary':'Fitted slope + boundary',
            'theory_slope':'KZ slope only','theory_plus_boundary':'KZ slope + boundary',
            'zero_reference_plus_boundary':'Reference 0 + boundary','one_reference_plus_boundary':'Reference 1 + boundary'}
    tab=[['Allowance','Pooled coverage','Trial success / CP lower','Mean S/e']]
    md+=['| Allowance | Pooled coverage | All-config trial success / CP lower | Mean S/e |','|---|---:|---:|---:|']
    for key,label in labels.items():
        s=data['ablations']['sweep'][key]
        row=[label,f"{s['pooled_coverage']:.3f}",f"{s['all_configurations_covered_trials']}/3 / {s['cp95_lower_nominal']:.3f}",f"{s['mean_S_over_e']:.3f}"]
        tab.append(row);md.append('| '+' | '.join(row)+' |')
    table(tab,[187,87,142,88])
    p('348 configurations reuse three distinct test trials. Trial success means all '
      'configurations for that trial passed. CP values are one-sided 95% nominal '
      'binomial lower bounds, not intervals on the pooled rate. Same MLP(8), seed 0 '
      'and legacy LOTO b as the prior ablation; no models were retrained.')
    p('Does the proposed growth allowance hold?','Heading2')
    tab=[['Law configuration','Endpoint checks','Interval checks','Largest interval ratio']]
    for group,label in [('canonical_146','Ceiling 146 mW'),('canonical_192','Ceiling 192 mW'),('sweep','22-split sweep')]:
        g=data['growth'][group]; n=g['config_trial_checks']
        tab.append([label,f"{g['endpoint_pass']}/{n}",f"{g['interval_pass']}/{n}",f"{g['max_interval_ratio']:.3f}"])
        md+=['',f"{label}: endpoint {g['endpoint_pass']}/{n}; measured-interval {g['interval_pass']}/{n}; maximum interval growth / allowance {g['max_interval_ratio']:.3f}."]
    table(tab,[154,98,98,154])
    p('Growth is independent of anchor, so 12 repeated anchor checks were removed. '
      'The 29 sweep checks reuse three test trials and several intervals; they are '
      'not 29 independent observations. Ratios below one support the assumed envelope '
      'on measured secants only.')

    story.append(PageBreak())
    p('What this supports, and what it does not','Title')
    p('The exact decomposition','Heading2')
    p('Let r0 be the residual at the calibration ceiling, delta the log-power distance, '
      'q the fitted law slope and q_sec the measured ceiling-to-test slope. The identity '
      'r = r0 + delta*(q - q_sec) holds numerically for every audited configuration. '
      'The proposed allowance is norm(r0) + k*delta.')
    p('Its margin equals growth slack plus triangle-inequality slack: '
      '[k*delta - norm(delta*(q-q_sec))] + '
      '[norm(r0) + norm(delta*(q-q_sec)) - norm(r)]. '
      'The first term is nonnegative in every measured check, so endpoint coverage '
      'does not require vector cancellation to rescue a violated growth budget.')
    p('A falsification control: unseen excursions','Heading2')
    u=np.linspace(0,1,1001)
    fig,ax=plt.subplots(figsize=(8,2.4),layout='constrained')
    ax.plot(u,np.abs(u+2*np.sin(2*np.pi*u)),label='Constructed residual magnitude')
    ax.plot(u,u,'--',label='Allowance');ax.scatter([0,1],[0,1],color='black',label='Measured endpoints',zorder=5)
    ax.set(xlabel='Log-power distance',ylabel='Magnitude');ax.legend(fontsize=8);ax.spines[['top','right']].set_visible(False)
    fig.savefig(OUT/'hidden_excursion.png',dpi=170);plt.close(fig)
    story.append(Image(str(OUT/'hidden_excursion.png'),width=504,height=151))
    p('A deterministic curve r(delta)=delta+2*sin(2*pi*delta) passes both endpoint '
      'checks but exceeds the allowance delta by 2 inside the interval. This control '
      'shows why finite secant checks cannot prove a continuous derivative envelope. '
      'It is a mathematical example, not another physical trial.')
    p('Revised claim and next decisive evidence','Heading2')
    claim=('An explicit calibration-boundary residual plus a slope allowance repairs '
      'the failed origin-only envelope on this corpus. All measured secant-growth '
      'checks pass. The ablations support the boundary correction, while reference '
      'exponents 0, 0.5 and 1 are indistinguishable by coverage. These results establish '
      'a mechanism-supported retrospective case study, not 90% population coverage '
      'or validation of a unique weak-turbulence exponent.')
    p(claim);md+=['','## Replacement claim','',claim]
    p('Freeze the 0.5-reference rule unchanged before new data collection. Obtain '
      'denser powers to test for interior excursions and independently acquired '
      'held-out trials, ideally on another apparatus. At least 29 independent '
      'successes without failure are needed for a one-sided 95% binomial lower '
      'bound above 0.90; this is a best-case minimum, not a powered study design.')
    md+=['','## Reproduce','',
         'From the repository root:', '',
         '```powershell','.\\.venv\\Scripts\\python.exe sases_eval/mechanism_audit.py',
         '.\\.venv\\Scripts\\python.exe -m unittest discover -s sases_eval -p test_mechanism_audit.py -v',
         '.\\.venv\\Scripts\\python.exe sases_eval/report_mechanism.py','```','',
         'Raw artifacts: geometry.csv, ablations.csv, growth_checks.json, results.json. '
         'MECHANISM_PROTOCOL.md records the fixed diagnostics. The original rule and prior reports are unchanged.']
    (OUT/'results.md').write_text('\n'.join(md)+'\n')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.drawString(54,26,'Retrospective mechanism audit | no new independent trials')
        canvas.drawRightString(558,26,str(doc.page))
    SimpleDocTemplate(str(OUT/'mechanism_audit.pdf'),pagesize=(612,792),leftMargin=54,rightMargin=54,
        topMargin=35,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
    combined=fitz.open(OUT/'mechanism_audit.pdf')
    prior=fitz.open(HERE/'rerun/sases_theory_rerun.pdf')
    combined.insert_pdf(prior)
    combined.save(OUT/'sases_mechanism_checked.pdf')
    print('Published',len(combined),'pages including prior supplement')


if __name__=='__main__':main()
