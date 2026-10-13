# Independent replication on a different physical system: wind-turbine power

Everything so far rests on four test trials from one capillary-wave apparatus,
and with four trials no comparison can reach p < 0.05. This audit replicates the
certificate on an unrelated system, chosen for three properties: a textbook
scaling law that holds only approximately, a regime break where it fails, and
many independent operating periods.

Fixed before any certificate is computed on these data. Column names and file
structure were inspected; no power curve, error or certificate was.

## Data

Kelmarsh wind farm, UK: 6 Senvion MM92 turbines (2050 kW rated, 92 m rotor),
10-minute SCADA, 2016. Kelmarsh wind farm dataset, released by Cubico
Sustainable Investments Ltd, Zenodo record 16807551 (v4),
https://zenodo.org/records/16807551, CC-BY-4.0. The raw archive is not
committed; `build_wind.py` reads it from `external_data/kelmarsh/`.

Records kept: wind speed, active power and rotor speed all finite, power above
10 kW, rotor speed above 0. Nothing else is filtered; curtailment, air-density
variation and turbulence stay in the data as law residual, where they belong.

## The law

In the variable-speed region of a pitch-regulated turbine,
P = 0.5 rho A Cp U^3 and rotor speed = lambda_opt U / R, so in logs, with
u = ln(U):

    ln P     = 3 u + const
    ln omega = 1 u + const

The output is y = (ln P, ln omega). The theory exponent vector q_th = (3, 1)
plays the role the KZ exponent 0.5 plays on the capillary corpus: the growth
radius is ||q_cal - q_th|| x delta. Affine, A = I, Proposition 1 unchanged.

## Units of independence

A unit is one turbine in one calendar month, May to December 2016 (commercial
operation began 15 April): up to 6 x 8 = 48 units. Each unit is a self-contained
replication with its own surrogate, its own law calibration and its own tests.
Units share turbines and months, so results are also reported clustered by
turbine (6) and by month (8). Nothing is pooled across units before scoring.

## Bins and bands (from the MM92 specification, not from these data)

Within a unit, records are binned by wind speed in 0.5 m/s bins. A bin is the
analogue of a capillary trial (its mean is the target); its records are the
analogue of windows. A bin needs at least 6 records (one hour).

  TRAIN    4.5 - 6.5 m/s   4 bins   surrogate training
  LAWCAL   6.5 - 8.5 m/s   4 bins   law slope q_cal and the ceiling label
  TEST A   8.5 - 10.5 m/s  4 bins   below rated: the law is approximately right
  TEST B   11.5 - 14.5 m/s 6 bins   rated region: power saturates, the law fails

A unit enters a scenario if all its TRAIN and LAWCAL bins are present and at
least two of that scenario's test bins are.

## Surrogates

The nine families of MULTIMODEL_PROTOCOL.md (multimodel_audit.fit_model), seed
0 only, input ln(U) per record, output (ln P, ln omega) per record, fitted per
unit on its TRAIN records only.

## Scored, per unit, surrogate and test bin

The ceiling certificate and the multi-subset consensus bound, imported. Premise
coverage (bin mean inside the growth ball). Competitors exactly as in
fair_baselines_audit.py: raw defect, calibration maximum (max surrogate error
over the LAWCAL bins) and OLS error predictor (those errors regressed on u).

## Predeclared expectations

  H1  Scenario A: the certificate holds on every row where its premise holds,
      and the premise holds on most units.
  H2  Scenario B: the premise fails often, because the true power plateau sits
      far below the cubic law. Any failure of the bound occurs only on rows
      where the premise failed. This is the test the capillary corpus could not
      run: whether the guarantee is conditional in the way it claims.
  H3  Scenario A: the certificate's below-error rate exceeds each competitor's,
      with paired sign tests significant at p < 0.05 at the turbine (n = 6) and
      month (n = 8) levels, where significance is attainable.
  H4  Scenario A: the certificate's rank correlation with e across the nine
      surrogates is positive.

Every outcome is reported, including ones that contradict these. Intervals are
two-sided 95% Clopper-Pearson at the unit, turbine and month levels.
