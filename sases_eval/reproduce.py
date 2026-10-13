"""Rebuild every number and figure in output/pdf/sases_seven_datasets.pdf, in order.

  python reproduce.py            everything (hours; downloads must already be in external_data/)
  python reproduce.py --report   only the summaries, figures and the PDF (minutes)

Two environments: .venv (Python 3.8, numpy/scikit-learn; the audits) and .venv-torch
(Python 3.11, PyTorch CPU; the neural PDE surrogates). Raw data are not committed; see
MULTI_DATASET_PROTOCOL.md for sources. Each step is an existing script run unchanged.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = str(HERE.parent / '.venv' / 'Scripts' / 'python.exe')
PYT = str(HERE.parent / '.venv-torch' / 'Scripts' / 'python.exe')

COMPUTE = [
    (PY, 'multi_audit.py', 'build', 'penmanshiel', 'lahauteborne', 'hilloftowie', 'pv2107'),
    (PY, 'multi_audit.py', 'run', 'capillary', 'kelmarsh', 'lahauteborne', 'penmanshiel', 'hilloftowie', 'pv9068', 'pv2107'),
    (PY, 'ranking_audit.py', 'run'),
    (PY, 'ks3_audit.py', 'run', '2017', '2018', '2019', '2020', '2021'),
    (PYT, 'pde_surrogates.py', 'all'),
]
REPORT = [
    (PY, 'multi_audit.py', 'report'),
    (PY, 'ranking_audit.py', 'report'),
    (PY, 'ablation_multi.py'),
    (PY, 'bootstrap_ci.py'),
    (PY, 'ks3_audit.py', 'report'),
    (PYT, 'pde_surrogates.py', 'report'),
    (PY, 'law_bound_plots.py'),
    (PY, 'multi_figures.py', 'capillary', 'kelmarsh', 'penmanshiel', 'lahauteborne', 'hilloftowie', 'pv9068', 'pv2107'),
    (PY, 'per_dataset_figs.py'),
    (PY, 'ks3_figures.py'),
    (PY, 'pde_figures.py'),
    (PY, 'eq_cards.py'),
    (PY, 'report_simple.py'),
]


def main():
    steps = REPORT if '--report' in sys.argv else COMPUTE + REPORT
    for cmd in steps:
        print('>>', ' '.join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)), flush=True)
        subprocess.run(list(cmd), cwd=HERE, check=True)
    print('done: output/pdf/sases_seven_datasets.pdf')


if __name__ == '__main__':
    main()
