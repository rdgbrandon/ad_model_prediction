"""End-to-end check against the running website, including a real dataset rebuild."""
import json,time
from urllib.request import Request,urlopen
from urllib.error import HTTPError

BASE='http://127.0.0.1:8765'
def get(path):
    with urlopen(BASE+path) as r:return json.load(r)
def start():
    req=Request(BASE+'/api/run',data=b'{"kind":"rebuild"}',
                headers={'Content-Type':'application/json','X-Lab-Request':'1','Origin':BASE})
    with urlopen(req) as r:return json.load(r)
before=get('/data/snapshot.json')['generated_at']
job=start();print('Started real rebuild job',job['id'],flush=True)
try:
    start();raise AssertionError('Concurrent job was incorrectly accepted')
except HTTPError as e:
    assert e.code==409
for _ in range(120):
    state=get('/api/status')
    if state['state'] in ('complete','failed'):break
    time.sleep(1)
assert state['state']=='complete',state
after=get('/data/snapshot.json')
assert after['generated_at']!=before
assert after['dataset']['windows']==448
s=after['ceiling']['summary']['canonical_192|mlp8|0']
assert abs(s['mean_S_over_e']-.809465390013326)<1e-8
assert s['all_configurations_covered_trials']==3
print('PASS: HDF5 rebuild, seven model refits, mechanism audit, serialized jobs and atomic dashboard refresh.',flush=True)
