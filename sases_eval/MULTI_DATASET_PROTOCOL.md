# The break-law certificate on seven datasets

Written before any certificate, law fit or power curve was computed on the four new
datasets (only file headers, turbine/inverter metadata and published specifications
were read). The method is the one confirmed on Kelmarsh 2020 (saturating/FINDINGS.md).

## The certificate: a sum of three things

Anchor a = the top LAWCAL bin, x = a test bin, f = the surrogate, c(.) = the law.

  D  = || f(x) - [ f(a) + c(x) - c(a) ] ||        original defect (surrogate vs its own transported anchor)
  b  = || f(a) - y(a) ||                          anchor allowance; exact, because y(a) is a measured label
  beta                                            law allowance (rules below)
  S  = max(D - b - beta, 0)                       the total bound, reported as the headline

Proposition 1: if ||y(x) - y(a) - (c(x) - c(a))|| <= beta, then e = ||f(x) - y(x)|| >= S.
The ceiling form S_c = max(||f(x) - y(a) - c(x) + c(a)|| - beta, 0) used in earlier audits
satisfies S_c >= S by the triangle inequality and is reported alongside.

## Law and allowance

Law: ln y = ln y(a) + q (ln x - ln x_a), q fitted on the LAWCAL bins, then capped at the
published operating limit of each output: c_j(x) = min(line_j, ln cap_j).
  L     straight line, beta = 2 kappa delta (reference)
  K-L   capped law, beta = 2 kappa delta
  K-S1  capped law, beta = 2 kappa min(delta, delta*), delta* where the last capped output
        reaches its cap. PRIMARY.
kappa: largest ||zeta||/delta over long hops across TRAIN + LAWCAL (rule E1); capillary uses the
short hops within LAWCAL (a regime break separates its TRAIN and LAWCAL).

## Datasets, caps (published, not fitted) and bands

| # | dataset | output(s) | cap(s) | unit | TRAIN / LAWCAL / A / B |
|---|---|---|---|---|---|
| 1 | Capillary waves (b200) | 12-band ln PSD | none published: K-L = K-S1 = L | corpus | 12-54 / 106-146 or 106-192 / above ceiling (mW) |
| 2 | Kelmarsh wind 2020 | power, rotor speed | 2,050 kW; 15.0 rpm | turbine-month | 4.5-6.5 / 6.5-8.5 / 8.5-10.5 / 11.5-14.5 m/s |
| 3 | PVDAQ 9068 solar 2018-19 | DC current | irradiance 823 W/m2 (inverter rating) | combiner-month | 150-350 / 350-550 / 550-800 / 900-1100 W/m2 |
| 4 | Penmanshiel wind 2017, WT11-15 | power, rotor speed | 2,050 kW (static csv); 17.1 rpm (MM82 spec) | turbine-month | as Kelmarsh |
| 5 | La Haute Borne wind 2014-15 | power | 2,050 kW (asset table) | turbine-month | as Kelmarsh |
| 6 | Hill of Towie wind 2019 | power | 2,300 kW (metadata); rotor speed excluded, published maxima disagree (17 vs 18 rpm) | turbine-month | as Kelmarsh |
| 7 | PVDAQ 2107 solar | inverter AC power | 27.6 kW nominal (ABB TRIO-27.6); 30 kW reported as sensitivity | inverter-month | as 9068 |

Bins: 0.5 m/s (wind), 50 W/m2 (solar), at least 6 records; a unit needs all TRAIN and LAWCAL
bins and at least 2 bins in a test band. Wind records: wind speed, power and (if used) rotor
speed finite, power > 10 kW, rotor speed > 0. Solar: 150 <= G < 1100 W/m2, output > 0.
Surrogates: the nine families of wind_audit (linear, poly3, knn5, krr_rbf, rf200, gbrt, mlp8,
mlp16x16, mlp32x32), seed 0, fitted per unit on TRAIN records; capillary uses its 19 fits.
Hill of Towie's AeroUp retrofit dates are recorded but not used to filter.

## Expectations

  H1  Zero bound failures where the premise held, every dataset and rule.
  H2  On the four new datasets with an output cap (4-7), K-S1 premise coverage >= 0.90 in B.
  H3  On those, K-S1 median S/e in B above K-L's.
  H4  Below the cap (A), K-S1 coverage >= 0.85 on datasets 4-7.
  H5  Datasets 1 and 3 have no cap in output units; no gain over L is expected there.
  Every outcome is reported, including those against these expectations.
