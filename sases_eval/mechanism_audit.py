"""Mechanism tests for the unchanged successful allowance; no model retraining."""
import csv
import json
import hashlib
from pathlib import Path
import numpy as np
from piecewise import TP, TM, lp
from honest_beta import law_from
from report_theory_audit import read_rows
from theory_audit import summarize

HERE = Path(__file__).resolve().parent
OUT = HERE / 'mechanism'


def geometry(r0, residual_increment, budget):
    actual = float(np.linalg.norm(r0 + residual_increment))
    triangle = float(np.linalg.norm(r0) + np.linalg.norm(residual_increment))
    return dict(actual=actual, cancellation=triangle-actual,
                growth_slack=budget-float(np.linalg.norm(residual_increment)),
                margin=float(np.linalg.norm(r0)+budget-actual))


def hidden_excursion(amplitude=2.0, grid_size=1001):
    # q_high=1.5, KZ reference=.5, r0=0, delta in [0,1].
    u = np.linspace(0, 1, grid_size)
    residual = u + amplitude*np.sin(2*np.pi*u)
    beta = u
    return dict(endpoint_covered=bool(abs(residual[-1]) <= beta[-1]+1e-12),
                max_interior_excess=float(np.max(np.abs(residual)-beta)),
                amplitude=amplitude, grid_size=grid_size)


def run():
    OUT.mkdir(exist_ok=True)
    fits = json.loads((HERE/'rerun/calibration_fits.json').read_text())
    lookup = {(f['config'],f['anchor']): f for f in fits}
    base = [r for r in read_rows() if r['model']=='mlp8' and r['seed']==0
            and r['method']=='theory_boundary' and r['b_mode']=='legacy_loto']
    records, ablations, intervals = [], [], {}
    for row in base:
        f = lookup[(row['config'],row['anchor'])]
        q = np.array(f['q_high'])
        a, top, t = f['anchor'], f['ceiling'], row['trial']
        c, c0, _, _ = law_from(f['lawcal'])
        r0 = TM[a]-TM[top]-c(lp[a],lp[top])-c0
        r = TM[a]-TM[t]-c(lp[a],lp[t])-c0
        delta = lp[t]-lp[top]
        secant = (TM[t]-TM[top])/delta
        increment = delta*(q-secant)
        assert np.allclose(r, r0+increment, atol=1e-11)
        k = f['theory']['kappa']
        geo = geometry(r0, increment, k*delta)
        assert abs(geo['margin']-row['margin']) < 1e-10
        interval_key = (row['config'],t)
        if interval_key not in intervals:
            chain = [top] + sorted([n for n in f['test'] if TP[n]<=TP[t]], key=lambda n: TP[n])
            slopes = [(TM[right]-TM[left])/(lp[right]-lp[left]) for left,right in zip(chain[:-1],chain[1:])]
            norms = [float(np.linalg.norm(q-s)) for s in slopes]
            intervals[interval_key] = dict(config=row['config'], trial=t,
                ceiling=float(TP[top]), power=float(TP[t]), kappa=k,
                endpoint_growth=float(np.linalg.norm(q-secant)),
                max_interval_growth=max(norms), interval_growth=norms,
                chain=chain, endpoint_pass=bool(np.linalg.norm(q-secant)<=k+1e-10),
                all_intervals_pass=bool(max(norms)<=k+1e-10))
        records.append(dict(config=row['config'], anchor=a, trial=t,
            boundary=float(np.linalg.norm(r0)), increment_norm=float(np.linalg.norm(increment)),
            derivative_ratio=float(np.linalg.norm(q-secant)/k), **geo))
        kap = f['fitted_kappa']
        choices = dict(boundary_only=float(np.linalg.norm(r0)),
                       fitted_plus_boundary=(float(np.linalg.norm(r0))+kap*delta) if kap is not None else None,
                       theory_slope=k*delta, theory_plus_boundary=float(np.linalg.norm(r0))+k*delta,
                       zero_reference_plus_boundary=float(np.linalg.norm(r0))+np.linalg.norm(q)*delta,
                       one_reference_plus_boundary=float(np.linalg.norm(r0))+np.linalg.norm(q-1)*delta)
        for method, bt in choices.items():
            rr = dict(row, method=method, beta=bt, S=max(row['D']-row['b']-bt,0) if bt is not None else None,
                      margin=bt-row['zeta'] if bt is not None else None,
                      covered=bool(row['zeta']<=bt+1e-10) if bt is not None else None)
            rr['valid'] = bool(rr['S']<=row['e']+1e-10) if rr['S'] is not None else None
            ablations.append(rr)
    summary = {}
    for group in ('canonical_146','canonical_192','sweep'):
        summary[group] = {m:summarize([r for r in ablations if r['config'].startswith(group) and r['method']==m])
                          for m in choices}
    growth = {}
    for group in ('canonical_146','canonical_192','sweep'):
        rs = [r for r in intervals.values() if r['config'].startswith(group)]
        growth[group] = dict(config_trial_checks=len(rs), unique_test_trials=len(set(r['trial'] for r in rs)),
            endpoint_pass=sum(r['endpoint_pass'] for r in rs), interval_pass=sum(r['all_intervals_pass'] for r in rs),
            max_endpoint_ratio=max(r['endpoint_growth']/r['kappa'] for r in rs),
            max_interval_ratio=max(r['max_interval_growth']/r['kappa'] for r in rs))
    result = dict(ablations=summary, growth=growth, synthetic=hidden_excursion(),
        sha256={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                [HERE/'mechanism_audit.py', HERE/'MECHANISM_PROTOCOL.md',HERE/'rerun/calibration_fits.json',HERE/'rerun/audit_rows.csv']})
    for name, rows in [('geometry',records),('ablations',ablations)]:
        with (OUT/(name+'.csv')).open('w',newline='') as out:
            w=csv.DictWriter(out, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (OUT/'growth_checks.json').write_text(json.dumps(list(intervals.values()),indent=2))
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    run()
