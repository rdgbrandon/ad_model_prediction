# A clean-law system: the calibration-only allowance works, and why it did not on wind

NREL PVDAQ system 9068 (Kersey, Colorado): 4.7 MW single-axis tracker, CdTe
modules, 24 DC combiners, 5-minute data 2017-2023. Law: photocurrent is
proportional to irradiance, ln I = 1 x ln G, with current and plane-of-array
irradiance from separate instruments. A unit is one combiner-month: 813 units,
5,587 test bins for the label-only analysis; 24,840 scored rows with nine
surrogates in 2018 and 2019. Protocol `PV_PROTOCOL.md`, written before the data
were opened; `PV_DEVIATIONS.md` records two additions made on data availability
alone (pyranometers largely offline 2020-2022) before any result existed.

## The question, answered

Does a calibration-only allowance work when the law holds smoothly across the
extrapolation range? **Yes.** Below clipping (550-800 W/m2), all years:

| allowance rule | covers the law's error | 95% CI |
|---|---:|---:|
| C - ceiling theory-distance (behind the capillary headlines) | 0.247 | [0.234, 0.261] |
| P - paper Eq. 5, short-hop kappa' | 0.899 | [0.889, 0.908] |
| **E1 - long-hop kappa', the unit's own calibration labels** | **0.955** | **[0.948, 0.961]** |

E1 covered at least 90% on every one of the 24 combiners. With the full
certificate it held on **100%** of rows in 2019 and **95.7%** in 2018.

The original rule failed for the third time in three systems, exactly as its
mechanism predicts: the fitted slope sits near the theory value 1, so its rate
collapses. That failure is structural and no dataset will fix it.

## The full certificate

| | 2019 (declared) | | 2018 (added) | |
|---|---:|---:|---:|---:|
| rule, below clipping | bound held | median S/e | bound held | median S/e |
| C | 0.750 | 0.95 | 0.737 | 0.85 |
| P | 0.946 | 0.32 | 0.958 | 0.28 |
| **E1** | **1.000** | 0.36 | **0.957** | 0.23 |
| E3, previous year | 0.975 | 0.66 | 0.983 | 0.41 |

**Zero bound failures in 124,524 row-rule pairs where the premise held.** With
the wind results, Proposition 1 has now been at risk on three physical systems
and has never failed when its premise was met.

**The price is informativeness.** A valid allowance makes the certificate
honest and conservative: under E1 it proves a median 23-36% of the error and is
silent on about 40% of rows. The 70% the capillary deck quotes came from rule C,
which is not a valid allowance; S/e should never be read without the validity
beside it.

## Why it worked here and failed on wind: one condition across all three systems

How the law's error grows with extrapolation distance delta decides it:

| system | how ||zeta|| grows with delta | zeta / delta across the test band | calibration-fitted rate |
|---|---|---|---|
| PV (this audit) | **slower than linear** - mostly an offset | falls 0.69 → 0.42 | over-covers longer hops: **works** |
| capillary (proposal §6.5) | roughly linear, ζ ≈ 11.0δ − 0.48 | rises slightly | biased 10-15% low |
| wind | **faster than linear** - the rotor-speed kink | rises ~0.45 → 1.0 | under-covers: **fails** |

A rate fitted on short hops covers long ones exactly when the residual grows no
faster than linearly. That is a precise, checkable scope for the method, and a
far better claim than "holds every time": **SASES with a calibration-only
allowance is valid when the law's departure grows at most linearly over the
extrapolation range; when the system has a regime change inside that range, the
allowance needs outside information.**

## Verdicts on the predeclared expectations

| | expectation | result |
|---|---|---|
| H1 | rule C fails below clipping | **Holds** (0.247) |
| H2 | P and E1 reach 0.90 below clipping | **E1 holds** (0.955); **P misses by 0.001** (0.899, CI includes 0.90) |
| H3 | P and E1 fail above clipping; spec-sheet rule S reaches 0.90 | **First half falsified** (P 0.951, E1 0.992); S holds (1.000) but by over-covering |
| H4 | fleet rule E3 reaches 0.90 in both scenarios | **Holds where it commits** (0.940 and 1.000), but it abstains on 26% and 56% of bins for lack of a previous year; leave-year-out 0.910 and 0.897 |
| H5 | zero bound failures where the premise held | **Holds**, 0 of 124,524 |

**Why H3 failed.** The clipping break is much weaker than the spec sheet
suggested. Beyond the ceiling the realised current slope only falls from 1.03 at
925 W/m2 to 0.76 at 1075 W/m2. Hot cells lose enough power to push clipping
onset well past the 823 W/m2 computed at reference temperature, so the expected
plateau mostly never arrives in this band, and the spec-sheet rule over-covers
(median S/e 0).

**Why the fleet rule is weaker here than on wind.** Across years this plant
shifts — soiling, degradation, sensor recalibration — so last year's residuals
are not exchangeable with this year's (2019 coverage from 2018: 0.773 on the
scored units). The fleet idea needs units that are genuinely comparable, which
neighbouring turbines in the same year were and consecutive PV years are not.

## Two things this dataset taught that apply everywhere

1. **The cleanest laws are often built into the measurement.** Exoplanet
   semi-major axes are derived from periods via Kepler's law, and radiosonde
   heights via the hypsometric equation; testing those laws on that data is
   circular. A fair test needs the law's two sides measured by separate
   instruments, as here.
2. **"Clean physics" is not "clean data".** The law here is exact in principle,
   yet its residual has a median of 11% — clouds crossing a 4.7 MW plant, so
   pyranometers on two pads do not see what each combiner's strings see. What
   rescued the allowance was not the absence of residual but its shape.

## Scope

One plant; units share 24 combiners, two inverters and one site. 2019 is sparse
(96 units), 2018 is the main scored year (288 units). The raw files are not
committed; `build_pv.py` rebuilds `pv/records.npz` from the OEDI release.

Reproduce: download `data/9068_irradiance_data.csv` and
`data/9068_dc_combiner_data.csv` from
s3://oedi-data-lake/pvdaq/2023-solar-data-prize/9068_OEDI/ into
`external_data/pvdaq_9068/`, then run `build_pv.py`, `pv_audit.py premise`,
`pv_audit.py cert 2018`, `pv_audit.py cert 2019` and `report_pv.py`.
