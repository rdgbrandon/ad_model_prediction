"""Extract PVDAQ 9068 records for pv_audit.py. See PV_PROTOCOL.md.

G: mean of the two temperature-compensated POA pyranometers, kept when both are
positive and agree within 5%. I: DC current of each of the 24 combiners, kept
when finite and > 0.5 A. Matched on timestamp. Only 150 <= G < 1100 W/m2 is
kept: every analysis band lies inside it, so nothing analysed is lost.
"""
import csv
import hashlib
from array import array
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / 'external_data' / 'pvdaq_9068'
OUT = HERE / 'pv'
G_LO, G_HI = 150.0, 1100.0


def num(s):
    try:
        v = float(s)
    except ValueError:
        return None
    return v if np.isfinite(v) else None


def run():
    OUT.mkdir(exist_ok=True)
    G = {}
    with (RAW / '9068_irradiance_data.csv').open(newline='') as f:
        r = csv.reader(f)
        hdr = [h.strip() for h in next(r)]
        i1 = hdr.index(next(h for h in hdr if 'pad_1_poa_irradiance_temp_compensated' in h))
        i2 = hdr.index(next(h for h in hdr if 'pad_2_poa_irradiance_temp_compensated' in h))
        for row in r:
            a, b = num(row[i1]), num(row[i2])
            if a is None or b is None or a <= 0 or b <= 0:
                continue
            g = 0.5 * (a + b)
            if abs(a - b) <= 0.05 * g and G_LO <= g < G_HI:
                G[row[0].strip()] = g
    print('irradiance timestamps kept: %d' % len(G), flush=True)

    comb, yr, mo, gg, ii = array('b'), array('h'), array('b'), array('f'), array('f')
    with (RAW / '9068_dc_combiner_data.csv').open(newline='') as f:
        r = csv.reader(f)
        hdr = [h.strip() for h in next(r)]
        cur = [(k, h.split('combiner_dc_output_')[1].split('_')[0]) for k, h in enumerate(hdr)
               if 'dc_current' in h]
        labels = [lab for _, lab in cur]
        print('combiners: %d  %s ... %s' % (len(cur), labels[0], labels[-1]), flush=True)
        for row in r:
            g = G.get(row[0].strip())
            if g is None:
                continue
            y, m = int(row[0][:4]), int(row[0][5:7])
            for c, (k, _) in enumerate(cur):
                v = num(row[k]) if k < len(row) else None
                if v is not None and v > 0.5:
                    comb.append(c); yr.append(y); mo.append(m); gg.append(g); ii.append(v)
    np.savez_compressed(OUT / 'records.npz', combiner=np.frombuffer(comb, np.int8),
                        year=np.frombuffer(yr, np.int16), month=np.frombuffer(mo, np.int8),
                        G=np.frombuffer(gg, np.float32), I=np.frombuffer(ii, np.float32),
                        labels=np.array(labels))
    h = hashlib.sha256()
    for name in ('9068_irradiance_data.csv', '9068_dc_combiner_data.csv'):
        h.update((RAW / name).read_bytes())
    (OUT / 'raw_sha256.txt').write_text(h.hexdigest() + '\n')
    print('records %d -> %s' % (len(gg), OUT / 'records.npz'))


if __name__ == '__main__':
    run()
