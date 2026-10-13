"""Equation cards in the style of the SASES slides: one large typeset equation, a row of every
symbol with a short label beneath it, and one plain sentence. Notation follows the slides
(D_theta(x, lambda), T_lambda x, b_lambda, beta_lambda(x), S(x)). Writes eq_cards/*.png.
"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / 'eq_cards'
NAVY = '#14145f'
plt.rcParams.update({'mathtext.fontset': 'stix', 'font.family': 'STIXGeneral'})


def card(name, title, main, symbols, sentence, extra=None, size=30, width=11.0, height=None, sym_y=None):
    rows = 1 + (1 if extra else 0)
    h = height or (3.3 + (0.9 if extra else 0))
    fig = plt.figure(figsize=(width, h))
    fig.patch.set_facecolor('white')
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(plt.Rectangle((0, 0.9), 1, 0.1, color=NAVY, transform=ax.transAxes))
    ax.text(0.02, 0.95, title, color='white', fontsize=17, fontweight='bold', va='center')
    y_main = 0.68 if not extra else 0.72
    ax.text(0.5, y_main, main, fontsize=size, ha='center', va='center', color='k')
    y = y_main - 0.2 if sym_y is None else sym_y
    if extra:
        ax.text(0.5, y, extra, fontsize=size * 0.62, ha='center', va='center', color='k')
        y -= 0.16
    n = len(symbols)
    for i, (sym, lab) in enumerate(symbols):
        xc = (i + 0.5) / n
        ax.text(xc, y, sym, fontsize=15, ha='center', va='center')
        ax.text(xc, y - 0.09, lab, fontsize=9.5, ha='center', va='center', color='#333333')
    ax.text(0.5, 0.07, sentence, fontsize=14.5, ha='center', va='center', color=NAVY, style='italic')
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / ('%s.png' % name), dpi=220, bbox_inches='tight', pad_inches=0.05, facecolor='white')
    plt.close(fig)


def generic():
    card('law', 'Physical law with the published limit',
         r'$c(x) = \min\!\left(\bar{y}(a^{*}) + q\,\ln\frac{x}{x^{\max}_{\mathrm{law}}},\ \ln y_{\mathrm{cap}}\right)$',
         [(r'$x$', 'New input'), (r'$x^{\max}_{\mathrm{law}}$', 'Calibration ceiling'),
          (r'$\bar{y}(a^{*})$', 'Measured output at ceiling'), (r'$q$', 'Fitted law exponent'),
          (r'$y_{\mathrm{cap}}$', 'Published limit (spec sheet)'), (r'$\ln$', 'Natural logarithm')],
         'The power law from the calibration data, stopped at the machine’s published limit.')
    card('defect', 'Defect',
         r'$D_{\theta}(x,\lambda) = \|\, f_{\theta}(T_{\lambda}x) - A_{\lambda} f_{\theta}(x) - c_{\lambda} \,\|_{2}$',
         [(r'$x$', 'New input'), (r'$T_{\lambda}x$', 'Anchor input (top training bin)'), (r'$f_{\theta}$', 'Surrogate model'),
          (r'$A_{\lambda}$', 'Law scaling (= I here)'), (r'$c_{\lambda}$', r'Law shift $c(T_\lambda x) - c(x)$'),
          (r'$\|\cdot\|_2$', 'Euclidean length')],
         'The defect is the mismatch between the surrogate and the physical law.')
    card('anchor', 'Anchor-error allowance',
         r'$\|\, f_{\theta}(T_{\lambda}x) - f(T_{\lambda}x) \,\|_{2} \;\leq\; b_{\lambda}$',
         [(r'$T_{\lambda}x$', 'Anchor input'), (r'$f_{\theta}(T_{\lambda}x)$', 'Anchor prediction'),
          (r'$f(T_{\lambda}x)$', 'True (measured) anchor output'), (r'$b_{\lambda}$', 'Anchor error bound'),
          (r'$\|\cdot\|_2$', 'Euclidean length')],
         'Measured at the top training bin, so here b is the surrogate’s actual error there.')
    card('lawallow', 'Law allowance',
         r'$\beta_{\lambda}(x) = \kappa^{\prime}\,\min\!\left(\left[\ln\frac{x}{x^{\max}_{\mathrm{law}}}\right]_{+},\ \delta^{*}\right) + r_{\lambda}$',
         [(r'$\kappa^{\prime} = 2\kappa$', 'Declared growth rate'), (r'$[\cdot]_{+}$', 'Clip negatives to zero'),
          (r'$\delta^{*}$', 'Distance where law hits cap'), (r'$r_{\lambda}$', 'Law’s measured miss at anchor'),
          (r'$\beta_{\lambda}(x)$', 'Law departure bound')],
         'Grows with the log-distance past the calibration ceiling, and stops growing at the published limit.',
         extra=r'$\kappa = \max_{h}\ \frac{\|\bar{y}(n) - \hat{c}_{h}(n)\|_{2}}{d_{h}}, \qquad '
               r'\delta^{*} = \max_{j}\ \frac{\ln y_{\mathrm{cap},j} - \bar{y}_{j}(a^{*})}{q_{j}}, \qquad '
               r'r_{\lambda} = \|\, f(T_{\lambda}x) - c(T_{\lambda}x) \,\|_{2}$')
    card('certificate', 'Full certificate',
         r'$\|\, f_{\theta}(x) - f(x) \,\|_{2} \;\geq\; S(x) = \max_{\lambda \in \Lambda_{\mathrm{anc}}(x)}\ '
         r'\frac{\left[\sum_{j=1}^{3} r_{j}(x,\lambda)\right]_{+}}{\|A_{\lambda}\|_{2}}$',
         [(r'$r_{1} = D_{\theta}(x,\lambda)$', 'Defect'), (r'$r_{2} = -b_{\lambda}$', 'Minus anchor allowance'),
          (r'$r_{3} = -\beta_{\lambda}(x)$', 'Minus law allowance'), (r'$[u]_{+} = \max(u, 0)$', 'Clip at zero'),
          (r'$\Lambda_{\mathrm{anc}}(x)$', 'Admitted anchors (one here)')],
         'The guaranteed minimum error: the defect minus both allowances, if both allowances hold.', size=27,
         height=4.3, sym_y=0.30)


DATASETS = {
    'capillary': (r'$c_{j}(P) = \bar{y}_{j}(a^{*}) + q_{j}\,\ln\frac{P}{P^{\max}_{\mathrm{law}}}, \quad j = 1,\dots,12$',
                  [(r'$P$', 'Drive power (mW)'), (r'$P^{\max}_{\mathrm{law}}$', '146 or 192 mW'),
                   (r'$\bar{y}_{j}$', 'ln PSD in band j'), (r'$q_{j}$', 'Fitted exponent per band'),
                   (r'$y_{\mathrm{cap}}$', 'none published')],
                  'No published limit above the ceiling, so the law is a straight line and nothing freezes.'),
    'wind': (r'$c_{P}(U) = \min\!\left(\bar{y}_{P}(a^{*}) + q_{P}\ln\frac{U}{U^{\max}_{\mathrm{law}}},\ \ln P_{\mathrm{rated}}\right),'
             r'\quad c_{\omega}(U) = \min\!\left(\bar{y}_{\omega}(a^{*}) + q_{\omega}\ln\frac{U}{U^{\max}_{\mathrm{law}}},\ \ln \omega_{\max}\right)$',
             [(r'$U$', 'Wind speed (m/s)'), (r'$U^{\max}_{\mathrm{law}}$', '8.5 m/s band top'),
              (r'$q_{P},\ q_{\omega}$', 'Fitted (theory 3 and 1)'), (r'$P_{\mathrm{rated}}$', 'Rated power'),
              (r'$\omega_{\max}$', 'Max rotor speed')],
             None),
    'pv9068': (r'$c(G) = \bar{y}(a^{*}) + q\left(\min(\ln G,\ \ln 823) - \ln G^{\max}_{\mathrm{law}}\right)$',
               [(r'$G$', 'Irradiance (W/m$^2$)'), (r'$G^{\max}_{\mathrm{law}}$', '550 W/m$^2$ band top'),
                (r'$q$', 'Fitted (theory 1)'), (r'$823$', 'Inverter limit in irradiance')],
               'The published limit caps irradiance, not current: 1000 × 1949 / 2368.8 = 823 W/m².'),
    'pv2107': (r'$c(G) = \min\!\left(\bar{y}(a^{*}) + q\,\ln\frac{G}{G^{\max}_{\mathrm{law}}},\ \ln 27.6\ \mathrm{kW}\right)$',
               [(r'$G$', 'Irradiance (W/m$^2$)'), (r'$G^{\max}_{\mathrm{law}}$', '550 W/m$^2$ band top'),
                (r'$q$', 'Fitted (theory 1)'), (r'$27.6$ kW', 'ABB TRIO-27.6 rating')],
               'AC power follows irradiance until the inverter reaches its rated 27.6 kW (30 kW checked too).'),
}
WIND_CAPS = {'kelmarsh': ('2050 kW', '15.0 rpm', 'Senvion MM92'), 'penmanshiel': ('2050 kW', '17.1 rpm', 'Senvion MM82'),
             'lahauteborne': ('2050 kW', None, 'Senvion MM82; power only'),
             'hilloftowie': ('2300 kW', None, 'Siemens SWT-2.3-VS-82; power only')}


def per_dataset():
    for name in ('capillary', 'pv9068', 'pv2107'):
        main, syms, sent = DATASETS[name]
        card('law_%s' % name, 'Law for this dataset', main, syms, sent, size=24)
    main_w, syms_w, _ = DATASETS['wind']
    for name, (p, w, model) in WIND_CAPS.items():
        if w is None:
            main = (r'$c_{P}(U) = \min\!\left(\bar{y}_{P}(a^{*}) + q_{P}\,\ln\frac{U}{U^{\max}_{\mathrm{law}}},\ '
                    r'\ln %s\ \mathrm{kW}\right)$' % p.split()[0])
            syms = syms_w[:3] + [(r'$P_{\mathrm{rated}}$', p)]
            sent = 'Power follows the cube law until rated power (%s).' % model
            size = 26
        else:
            main = main_w
            syms = syms_w[:3] + [(r'$P_{\mathrm{rated}}$', p), (r'$\omega_{\max}$', w)]
            sent = 'Power and rotor speed follow the law until their published limits (%s).' % model
            size = 19
        card('law_%s' % name, 'Law for this dataset', main, syms, sent, size=size, width=12.5 if w else 11)


def pde_cards():
    card('law_pde', 'Exact symmetry law (PDE surrogates)',
         r'$u(x,\,t;\,p) = u(x,\,\lambda t;\,p/\lambda) \quad\Rightarrow\quad T_{\lambda}(u_0, p, t) = (u_0,\ p/\lambda,\ \lambda t),\ \ A_{\lambda} = I,\ \ c_{\lambda} = 0$',
         [(r'$p$', 'speed b or diffusivity D'), (r'$t$', 'time'), (r'$\lambda$', 'transform parameter'),
          (r'$u_0$', 'initial condition'), (r'$p\,t$', 'invariant (unchanged by T)')],
         'Advection and diffusion depend on p and t only through p·t, so an out-of-range p maps to an in-range anchor.',
         size=22, width=12)
    card('ks3', 'K-S3: shrink the allowance after the cap',
         r'$\beta_{\lambda}(x) = \kappa^{\prime}\delta\ \ (\delta \leq \delta^{*}), \qquad '
         r'\beta_{\lambda}(x) = \min\!\left(\kappa^{\prime}\delta^{*},\ q_{90}^{\mathrm{fleet}}\right)\ \ (\delta > \delta^{*})$',
         [(r'$\kappa^{\prime}\delta$', 'K-S1 below the cap'), (r'$\delta^{*}$', 'where the law hits its cap'),
          (r'$q_{90}^{\mathrm{fleet}}$', '90% conformal quantile, earlier years'), (r'$\min$', 'never wider than K-S1')],
         'Past the cap the allowance shrinks to the plateau error seen on the same turbines in earlier years.',
         size=24, width=12)

if __name__ == '__main__':
    generic(); per_dataset(); pde_cards()
    print('cards ->', OUT)
