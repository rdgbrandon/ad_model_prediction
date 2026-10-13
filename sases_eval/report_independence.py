"""Tables from independence/results.json. Reads results only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / 'independence/results.json').read_text())


def ci(c):
    return '[%.3f, %.3f]' % tuple(c)


def rule(n):
    print('-' * n)


print('ARE THE ROWS INDEPENDENT, AND WHAT DO THEY REALLY SUPPORT?')
print(D['note'])

print('\n\n=== 1. The slide 25 table, at every sample size the rows could claim ===')
hdr = ('%-21s%-7s%10s%17s%10s%17s%10s%17s'
       % ('method', 'side', 'rows', '95% CI rows', 'trials', '95% CI trials',
          'Kish n', '95% CI Kish'))
print(hdr); rule(len(hdr))
for m in D['methods']:
    print('%-21s%-7s%10s%17s%10s%17s%10.1f%17s'
          % (m['method'], m['side'], '%d/%d' % (m['held'], m['rows']), ci(m['ci_rows']),
             '%d/%d' % (m['trials_all_held'], m['trials']), ci(m['ci_trials']),
             m['n_eff'], ci(m['ci_n_eff'])))
print('A trial counts as held only if the method held on every row of that trial.')

print('\n=== 1b. The intermediate groupings ===')
hdr = '%-21s%14s%17s%16s%17s' % ('method', 'split x trial', '95% CI', 'repr x split x trial', '95% CI')
print(hdr); rule(len(hdr))
for m in D['methods']:
    print('%-21s%14s%17s%16s%17s'
          % (m['method'], '%d/%d' % (m['cases_all_held'], m['splits_x_trials']),
             ci(m['ci_cases']), '%d/%d' % (m['cells_all_held'], m['cases']),
             ci(m['ci_cells'])))

print('\n\n=== 2. How dependent are the rows? ===')
print('Share of the variance of the margin (e - score)/e explained by each grouping.')
print('If rows were independent draws, no grouping would explain much.')
keys = list(D['methods'][0]['variance_share'])
hdr = '%-31s' % 'grouping' + ''.join('%13s' % m['method'][:12] for m in D['methods'])
print(hdr); rule(len(hdr))
for k in keys:
    print('%-31s' % k + ''.join(
        '%13s' % ('--' if m['variance_share'][k] is None else '%.3f' % m['variance_share'][k])
        for m in D['methods']))
rule(len(hdr))
print('%-31s' % 'ICC(1) within test trial' + ''.join(
    '%13s' % ('--' if m['icc_trial'] is None else '%.3f' % m['icc_trial']) for m in D['methods']))
print('%-31s' % 'design effect' + ''.join('%13.1f' % m['design_effect'] for m in D['methods']))
print('%-31s' % 'effective n (Kish)' + ''.join('%13.1f' % m['n_eff'] for m in D['methods']))
print('%-31s' % 'exchangeability p (trial)' + ''.join(
    '%13s' % ('--' if m['exchangeability_p'] is None else '%.4f' % m['exchangeability_p'])
    for m in D['methods']))
print('\nexchangeability p: permutation test that the between-trial share of variance')
print('is no larger than chance. Small p means rows are NOT exchangeable across trials.')

print('\n\n=== 3. Where do the failures happen? ===')
for m in D['methods']:
    pt = m['per_trial']
    cells = '   '.join('%g mW %3d/%-3d' % (d['P'], d['held'], d['rows'])
                       for d in sorted(pt.values(), key=lambda d: d['P']))
    tail = ('' if m['failure_concentration_p'] is None
            else '   concentration p = %.4f' % m['failure_concentration_p'])
    print('%-21s %s%s' % (m['method'], cells, tail))
print('\nconcentration p: permutation chi-square that failures are spread evenly over')
print('trials. Small p means they cluster in particular trials.')

print('\n\n=== 4. Leave one test trial out: how much does any single trial move the summary? ===')
hdr = '%-21s%-12s%14s%14s' % ('method', 'trial left out', 'median s/e', 'rank rho')
print(hdr); rule(len(hdr))
for m in D['methods']:
    print('%-21s%-12s%14.3f%14s' % (m['method'], '(none)', m['median_ratio'],
                                    '%.3f' % m['rank'] if m['rank'] is not None else '--'))
    for t, v in m['leave_one_trial_out'].items():
        print('%-21s%-12s%14.3f%14s' % ('', '%g mW' % m['per_trial'][t]['P'],
                                        v['median_ratio'],
                                        '%.3f' % v['rank'] if v['rank'] is not None else '--'))

print('\n\n=== 5. The 931-row sweep, same treatment ===')
hdr = '%-32s%10s%17s%10s%17s%10s%17s' % ('indicator', 'rows', '95% CI', 'cells', '95% CI',
                                         'trials', '95% CI')
print(hdr); rule(len(hdr))
for k, v in D['sweep'].items():
    print('%-32s%10s%17s%10s%17s%10s%17s'
          % (k, '%d/%d' % (v['held'], v['rows']), ci(v['ci_rows']),
             '%d/%d' % (v['cells_all_held'], v['cells']), ci(v['ci_cells']),
             '%d/%d' % (v['trials_all_held'], v['trials']), ci(v['ci_trials'])))

print('\n\n=== 6. Two different claims, two different sample sizes ===')
print('"Holds on a new experiment" generalises over test trials (n = 4).')
print('"Holds for a new surrogate on these experiments" generalises over fits.')
hdr = ('%-21s%10s%17s%10s%17s%11s%17s'
       % ('method', 'trials', '95% CI', 'fits', '95% CI', 'families', '95% CI'))
print(hdr); rule(len(hdr))
for m in D['methods']:
    print('%-21s%10s%17s%10s%17s%11s%17s'
          % (m['method'], '%d/%d' % (m['trials_all_held'], m['trials']), ci(m['ci_trials']),
             '%d/%d' % (m['fits_all_held'], m['fits']), ci(m['ci_fits']),
             '%d/%d' % (m['families_all_held'], m['families']), ci(m['ci_families'])))

print('\n=== 7. The dependence is crossed: by surrogate as well as by trial ===')
hdr = '%-21s%14s%14s%14s%16s%16s' % ('method', 'Kish (trial)', 'crossed n', '95% CI crossed',
                                     'exch. p (fit)', 'fail conc. p (fam)')
print(hdr); rule(len(hdr))
for m in D['methods']:
    print('%-21s%14.1f%14.1f%16s%14s%16s'
          % (m['method'], m['n_eff'], m['n_eff_crossed'], ci(m['ci_n_eff_crossed']),
             '%.4f' % m['exchangeability_p_fit'] if m['exchangeability_p_fit'] is not None else '--',
             '%.4f' % m['failure_concentration_p_family']
             if m['failure_concentration_p_family'] is not None else '--'))
print('\ncrossed n: Var(mean) ~ s2_fit/n_fit + s2_trial/n_trial + s2_res/N, with the')
print('variance shares of section 2 standing in for components. It sizes the')
print('uncertainty of an average over these rows, not a count of experiments.')

print('\nFailure rate by surrogate family (competitors only):')
fams = list(D['methods'][1]['failure_rate_by_family'])
hdr = '%-21s' % 'method' + ''.join('%10s' % f[:9] for f in fams)
print(hdr); rule(len(hdr))
for m in D['methods']:
    print('%-21s' % m['method'] + ''.join('%10.2f' % m['failure_rate_by_family'][f] for f in fams))

print('\n\n=== 8. Paired tests: SASES against each competitor ===')
print('Same trials and fits score every method, so these are exact sign tests on the')
print('units where the two methods disagree about holding on every row.')
hdr = ('%-21s%-15s%7s%12s%12s%12s%14s'
       % ('competitor', 'unit', 'units', 'SASES only', 'comp. only', 'p (1-sided)', 'min attainable'))
print(hdr); rule(len(hdr))
for p in D['paired']:
    print('%-21s%-15s%7d%12d%12d%12s%14.4f'
          % (p['method'], p['unit'], p['units'], p['sases_only'], p['competitor_only'],
             '--' if p['p_one_sided'] is None else '%.4f' % p['p_one_sided'],
             p['smallest_attainable_p']))
