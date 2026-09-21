"""Stronger conditional lower bounds from multiple calibration-only regions."""
import hashlib,json
from itertools import combinations
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from piecewise import TM,TP,lp,slopes
from theory_audit import summarize

HERE=Path(__file__).resolve().parent

def weighted_bound(pred,centres,radii,weights):
    w=np.maximum(np.asarray(weights,float),0)
    if w.sum()<=0:raise ValueError('Positive weight sum required')
    w=w/w.sum();centre=w@centres
    radius2=float(w@(radii*radii)-w@np.sum((centres-centre)**2,axis=1))
    if radius2 < -1e-9:return None,w # inconsistent assumptions; abstain
    return max(float(np.linalg.norm(pred-centre)-np.sqrt(max(radius2,0))),0),w

def combine(pred,centres,radii):
    singles=np.maximum(np.linalg.norm(centres-pred,axis=1)-radii,0)
    i=int(np.argmax(singles));initial=np.eye(len(radii))[i]
    best=float(singles[i]);weights=initial
    def objective(w):
        value,_=weighted_bound(pred,centres,radii,w)
        return -value if value is not None else 1e6
    # The returned score is recomputed from feasible weights, not the solver's
    # objective or convergence claim. Non-optimal weights remain valid.
    for start in (initial,np.ones(len(radii))/len(radii)):
        opt=minimize(objective,start,method='SLSQP',bounds=[(0,1)]*len(radii),
                     constraints={'type':'eq','fun':lambda w:w.sum()-1},
                     options={'maxiter':150,'ftol':1e-10})
        value,w=weighted_bound(pred,centres,radii,opt.x)
        if value is not None and value>best:best,weights=value,w
    return best,weights,float(singles[i])

def run():
    source=json.loads((HERE/'ceiling/results.json').read_text())
    fits=json.loads((HERE/'rerun/calibration_fits.json').read_text())
    lookup={f['config']:f for f in fits}
    rows=[]
    for row in source['rows']:
        fit=lookup[row['config']];cal=fit['lawcal'];pred=np.array(row['prediction'])
        centres=[];radii=[];subsets=[]
        for size in range(3,len(cal)+1):
            for sub in combinations(cal,size):
                top=max(sub,key=lambda t:TP[t]);q=slopes(list(sub));d=lp[row['trial']]-lp[top]
                centres.append(TM[top]+q*d);radii.append(np.linalg.norm(q-.5)*d);subsets.append(list(sub))
        centres=np.array(centres);radii=np.array(radii)
        S,w,best_single=combine(pred,centres,radii)
        residuals=np.linalg.norm(centres-np.array(row['truth']),axis=1)
        covered=bool(np.all(residuals<=radii+1e-9))
        if covered:assert S<=row['e']+1e-8
        assert S+1e-8>=row['S']
        rows.append(dict(row,baseline_S=row['S'],S=S,best_single_S=best_single,
                         covered=covered,valid=bool(S<=row['e']+1e-8),
                         margin=float(np.min(radii-residuals)),ball_count=len(radii),
                         weights=w.tolist(),subsets=subsets,all_ball_residuals=residuals.tolist(),
                         all_ball_radii=radii.tolist(),centres=centres.tolist()))
    summary={}
    for key in source['summary']:
        group,model,seed=key.split('|')
        rs=[r for r in rows if r['config'].startswith(group) and r['model']==model and r['seed']==int(seed)]
        summary[key]=dict(summarize(rs),baseline_mean_S_over_e=float(np.mean([r['baseline_S']/r['e'] for r in rs])),
                          max_single_mean_S_over_e=float(np.mean([r['best_single_S']/r['e'] for r in rs])))
    out=HERE/'consensus';out.mkdir(exist_ok=True)
    result=dict(rows=rows,summary=summary,assumption='All calibration-subset target balls contain the true spectrum',
                protocol_sha256=hashlib.sha256((HERE/'CONSENSUS_PROTOCOL.md').read_bytes()).hexdigest(),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    tmp=out/'results.tmp';tmp.write_text(json.dumps(result,allow_nan=False));tmp.replace(out/'results.json')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':run()
