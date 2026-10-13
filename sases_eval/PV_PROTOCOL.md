# A clean-law test: photovoltaic current against irradiance

On wind, every calibration-only allowance failed, and the diagnosis was that the
turbine's control system breaks the law just past the calibration band (rotor
speed cap, rated plateau). The open question: on a system whose law holds
smoothly across the extrapolation range, do calibration-only allowances work?
This audit asks it on a utility PV plant, where the law follows directly from
the physics and the one regime break is predictable from the spec sheet.

Written before the data files were opened. Only file headers, time span (Aug
2017 to Nov 2023), sampling interval (5 min) and system metadata were read.

## Data

NREL PVDAQ system 9068, "SR_CO", Kersey, Colorado: 4,738 kW DC, single-axis
tracker, CdTe modules (117.5 W, Isc 1.83 A, power temperature coefficient
-0.28 %/C), two string inverters. 2023 Solar Data Prize release on the Open
Energy Data Initiative, s3://oedi-data-lake/pvdaq/2023-solar-data-prize/9068_OEDI/.
Raw files are not committed; `build_pv.py` reads them from external_data/pvdaq_9068/.

Irradiance G: mean of the two temperature-compensated plane-of-array class-A
pyranometers. Current I: DC current of each of the 24 combiners. Separate
instruments, so the law is not built into either measurement.

Records kept: G and I finite and matched on timestamp, both pyranometers
positive and agreeing within 5%, I > 0.5 A. Nothing else is filtered; soiling,
snow, partial outages and temperature stay in the data as law residual.

## The law

Photocurrent is proportional to photon flux, so I = k G and, with u = ln G,

    ln I = 1 u + const,      q_th = 1.

Scalar output y = ln I. Affine, A = I, Proposition 1 unchanged. Voltage is not
used: its dependence on irradiance runs through temperature and is not clean.

## The predictable break, from the metadata alone

Each inverter: 1,344 strings x 15 modules x 117.5 W = 2,368.8 kW DC against an
AC capacity of 1,910 kW. At an assumed 98% conversion efficiency the inverter
limits DC power at 1,949 kW, reached at

    G_clip = 1000 W/m2 x 1949 / 2368.8 = 823 W/m2

at reference cell temperature (hot cells lose power and push onset higher; 823
is the earliest onset). Above it the inverter leaves the maximum-power point and
the current stops tracking irradiance.

## Units, bins, bands

A unit is one combiner in one calendar month. Within a unit, records are binned
by G in 50 W/m2 bins; a bin needs at least 6 records (30 minutes).

  TRAIN    150 - 350 W/m2   4 bins
  LAWCAL   350 - 550 W/m2   4 bins
  TEST A   550 - 800 W/m2   5 bins   below G_clip: the law should hold
  TEST B   900 - 1100 W/m2  4 bins   above G_clip: clipping

A unit enters a scenario if all TRAIN and LAWCAL bins are present and at least
two of that scenario's test bins are.

## Allowance rules (all fixed on wind, before these data; S fixed here)

  C   ||q_cal - q_th|| x delta, the ceiling theory-distance rule
  P   2 x kappa'_fit x delta, kappa' from short hops on LAWCAL (paper Eq. 5)
  E1  2 x kappa'_fit x delta, kappa' from long hops over TRAIN + LAWCAL
  S   spec-sheet rule: E1 + 2 x max(0, ln(G / G_clip)), the departure if the
      current stopped rising at G_clip, doubled because a power-limited inverter
      raises voltage and so can push current below flat
  E3  split-conformal 90% quantile of the law residual at the same bin over all
      units of the previous calendar year (all combiners)

## Two analyses

1. Premise coverage, label-only, needing no surrogate: for every unit in
   2018-2023, does each rule's beta cover the law residual ||zeta|| at each test
   bin? (2017 serves only as E3's calibration year for 2018.)
2. The full certificate in calendar year 2019: the nine surrogate families of
   MULTIMODEL_PROTOCOL.md, seed 0, fitted per unit on TRAIN records; validity,
   S/e and silent rate under each rule, S = max(D - beta, 0) with the LAWCAL
   ceiling as centre.

## Predeclared expectations

  H1  C fails below clipping (premise coverage < 0.5): the fitted slope will sit
      near 1, so its rate collapses. This is the structural prediction.
  H2  The question this audit exists for: below clipping, the calibration-only
      rules P and E1 reach premise coverage >= 0.90. If so, the wind failure was
      the law's kinks; if not, calibration-only allowances fail even on a clean
      law.
  H3  Above clipping, P and E1 fall below 0.5 coverage, and the spec-sheet rule
      S reaches >= 0.90.
  H4  E3 reaches >= 0.90 in both scenarios.
  H5  Zero bound failures on rows where the premise held, for every rule.

Every outcome is reported, including those that contradict these. Intervals are
two-sided 95% Clopper-Pearson, at the unit-bin level and clustered by combiner.
