"""A direct calibration-ceiling certificate with the unchanged growth budget."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from piecewise import TM, TP, lp, TRAIN, slopes
from capillary2 import build, FC
from report_theory_audit import read_rows
from theory_audit import summarize

HERE=Path(__file__).resolve().parent
OUT=HERE/'ceiling'


def certificate(prediction, ceiling_label, slope, delta, rate):
    if delta < 0 or rate < 0:
        raise ValueError('Nonnegative distance and rate required')
    centre=np.asarray(ceiling_label)+np.asarray(slope)*delta
    radius=float(rate*delta)
    return centre,radius,max(float(np.linalg.norm(prediction-centre))-radius,0.)


def run():
    OUT.mkdir(exist_ok=True)
    fits=json.loads((HERE/'rerun/calibration_fits.json').read_text())
    configs={}
    for f in fits:
        configs.setdefault(f['config'],f)
    previous=read_rows()
    lookup={(r['config'],r['model'],r['seed'],r['trial'],r['b_mode'],r['anchor']):r for r in previous
            if r['method']=='theory_boundary'}
    rows=[]
    with threadpool_limits(limits=1):
        for kind,seed in [('mlp8',s) for s in range(3)]+[('mlp16x16',s) for s in range(3)]+[('linear',0)]:
            print('Ceiling audit:',kind,seed,flush=True)
            g=build(kind,seed,TRAIN,slopes(TRAIN))
            for tag,f in configs.items():
                if tag.startswith('sweep') and (kind,seed)!=('mlp8',0):continue
                q=np.array(f['q_high']); top=f['ceiling']; k=f['theory']['kappa']
                for t in f['test']:
                    ft=g(np.array([[lp[t]]]))[0]
                    centre,radius,S=certificate(ft,TM[top],q,lp[t]-lp[top],k)
                    err=float(np.linalg.norm(ft-TM[t])); residual=float(np.linalg.norm(TM[t]-centre))
                    covered=bool(residual<=radius+1e-10); valid=bool(S<=err+1e-10)
                    if covered:assert valid
                    old=lookup[(tag,kind,seed,t,'legacy_loto',f['anchor'])]
                    labelled=lookup[(tag,kind,seed,t,'labelled_anchor',f['anchor'])]
                    # Independent refit must reproduce the earlier prediction error.
                    assert abs(err-old['e'])<1e-8
                    rows.append(dict(config=tag,model=kind,seed=seed,trial=t,P=float(TP[t]),
                        ceiling=float(TP[top]),delta=float(lp[t]-lp[top]),kappa=k,radius=radius,
                        tube_residual=residual,margin=radius-residual,S=S,e=err,covered=covered,
                        valid=valid,anchor_covered=True,old_S=old['S'],labelled_anchor_S=labelled['S'],
                        prediction=ft.tolist(),centre=centre.tolist(),truth=TM[t].tolist()))
    summaries={}
    for kind,seed in [('mlp8',s) for s in range(3)]+[('mlp16x16',s) for s in range(3)]+[('linear',0)]:
        for group in ('canonical_146','canonical_192','sweep'):
            rs=[r for r in rows if r['config'].startswith(group) and r['model']==kind and r['seed']==seed]
            if rs:
                s=summarize(rs)
                s.update(mean_old_S_over_e=float(np.mean([r['old_S']/r['e'] for r in rs])),
                         mean_labelled_S_over_e=float(np.mean([r['labelled_anchor_S']/r['e'] for r in rs])))
                summaries[f'{group}|{kind}|{seed}']=s
    data=dict(rows=rows,summary=summaries,frequency_hz=FC.tolist(),
        target='Trial mean of window log band PSD; empirical target, not noise-free truth',
        assumption='True target remains inside the calibration-centred growth ball',
        protocol_sha256=hashlib.sha256((HERE/'CEILING_PROTOCOL.md').read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        spec_sha256=hashlib.sha256((HERE/'spec.npz').read_bytes()).hexdigest())
    tmp=OUT/'results.tmp';tmp.write_text(json.dumps(data,indent=2,allow_nan=False));tmp.replace(OUT/'results.json')
    scalar=[{k:v for k,v in r.items() if not isinstance(v,list)} for r in rows]
    with (OUT/'rows.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(scalar[0]));w.writeheader();w.writerows(scalar)
    print(json.dumps(summaries,indent=2),flush=True)


if __name__=='__main__':run()
