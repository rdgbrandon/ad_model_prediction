"""Export only published scientific artifacts, not arbitrary workspace files."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
EVAL=ROOT/'sases_eval'


def export():
    load=lambda p:json.loads((EVAL/p).read_text())
    with np.load(EVAL/'spec.npz',allow_pickle=False) as ds:
        trials=[]
        for n in dict.fromkeys(ds['trial']):
            mask=ds['trial']==n
            trials.append(dict(id=str(n),power=float(ds['P'][mask][0]),windows=int(mask.sum()),
                               spectrum=ds['Y'][mask].mean(0).tolist()))
        dataset=dict(trials=trials,windows=int(len(ds['Y'])),bands=int(ds['Y'].shape[1]),
                     frequencies=ds['fcent'].tolist(),edges=ds['edges'].tolist())
    data=dict(generated_at=datetime.now(timezone.utc).isoformat(),dataset=dataset,
              ceiling=load('ceiling/results.json'),consensus=load('consensus/results.json'),mechanism=load('mechanism/results.json'),
              previous=load('rerun/results.json'),growth=load('mechanism/growth_checks.json'),
              input_sha256=hashlib.sha256((EVAL/'spec.npz').read_bytes()).hexdigest())
    dest=ROOT/'web/data';dest.mkdir(exist_ok=True)
    tmp=dest/'snapshot.tmp';tmp.write_text(json.dumps(data,allow_nan=False),encoding='utf-8')
    tmp.replace(dest/'snapshot.json')
    print('Published dashboard snapshot:',data['generated_at'],flush=True)


if __name__=='__main__':export()
