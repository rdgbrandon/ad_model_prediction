"""Run the unchanged wind pipeline on another Kelmarsh year.

build_wind.py and wind_audit.py are imported, not edited, so the source hashes
recorded in the 2016 results still match their files. Only the archive, the
months and the output folder are redirected. Usage: python run_wind_year.py 2017
"""
import sys
from pathlib import Path

import build_wind
import wind_audit

ARCHIVES = {2017: 'Kelmarsh_SCADA_2017_3083.zip', 2018: 'Kelmarsh_SCADA_2018_3084.zip'}

if __name__ == '__main__':
    year = int(sys.argv[1])
    here = Path(__file__).resolve().parent
    out = here / 'wind' / str(year)
    build_wind.ARCHIVE = here.parent / 'external_data' / 'kelmarsh' / ARCHIVES[year]
    build_wind.MONTHS = range(1, 13)      # commercial operation all year
    build_wind.OUT = out
    build_wind.run()
    wind_audit.OUT = out
    wind_audit.run()
