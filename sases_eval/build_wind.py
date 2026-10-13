"""Extract the Kelmarsh 2016 records used by wind_audit.py. See WIND_PROTOCOL.md.

Reads the raw Zenodo archive from external_data/kelmarsh/ (not committed) and
writes wind/records.npz: one row per kept 10-minute record. Filters, exactly as
declared: wind speed, power and rotor speed finite; power > 10 kW; rotor speed
> 0; months May to December.
"""
import csv
import hashlib
import io
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parent / 'external_data' / 'kelmarsh' / 'Kelmarsh_SCADA_2016_3082.zip'
OUT = HERE / 'wind'
COLS = ('Date and time', 'Wind speed (m/s)', 'Power (kW)', 'Rotor speed (RPM)')
MONTHS = range(5, 13)


def read_turbine(z, name):
    f = io.TextIOWrapper(z.open(name), encoding='utf-8', errors='replace', newline='')
    header = None
    for line in f:
        if line.startswith('# Date and time'):
            header = next(csv.reader([line[2:]]))
            break
    idx = [header.index(c) for c in COLS]
    out = []
    for row in csv.reader(f):
        try:
            stamp = row[idx[0]]
            U, P, w = (float(row[i]) for i in idx[1:])
        except (ValueError, IndexError):
            continue
        if not (np.isfinite(U) and np.isfinite(P) and np.isfinite(w)):
            continue
        if P <= 10 or w <= 0 or U <= 0:
            continue
        month = int(stamp[5:7])
        if month in MONTHS:
            out.append((month, U, P, w))
    return out


def run():
    OUT.mkdir(exist_ok=True)
    z = zipfile.ZipFile(ARCHIVE)
    names = sorted(n for n in z.namelist() if n.startswith('Turbine_Data_Kelmarsh_'))
    turbine, month, U, P, W = [], [], [], [], []
    for name in names:
        t = int(name.split('_')[3])
        recs = read_turbine(z, name)
        print('turbine %d: %d records kept' % (t, len(recs)), flush=True)
        for m, u, p, w in recs:
            turbine.append(t); month.append(m); U.append(u); P.append(p); W.append(w)
    np.savez_compressed(OUT / 'records.npz', turbine=np.array(turbine), month=np.array(month),
                        U=np.array(U), P=np.array(P), omega=np.array(W),
                        archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest())
    print('records', len(U), '-> wind/records.npz')


if __name__ == '__main__':
    run()
