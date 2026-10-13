# Expanding the allowance from data: calibration labels are not enough, a fleet is

The wind replication failed because the law allowance was 4.4x to 11.6x too
small. This audit tried three data-driven expansions, under one rule: beta may
use only labels available at deployment, never the scored unit's own test bins.
Protocol `ALLOWANCE_PROTOCOL.md`.

**Design.** The rules were designed after the 2016 failure, with its residuals
in view, so 2016 is development only. They were then fixed and **confirmed on
Kelmarsh 2017**, a year not opened until the protocol was written: 72
turbine-months, 5,184 rows, run through the unchanged pipeline
(`run_wind_year.py` reuses `build_wind.py` and `wind_audit.py` as they are).

## The confirmation year, 2017

Below rated (8.5-10.5 m/s), 288 unit-bins:

| allowance rule | premise held | 95% CI | bound held | median S/e |
|---|---:|---:|---:|---:|
| C - ceiling theory-distance (all headline numbers) | 0.000 | [0.000, 0.013] | 0.206 | 1.04 |
| P - paper Eq. 5, 2 x short-hop kappa' | 0.517 | [0.458, 0.576] | 0.676 | 0.98 |
| E1 - long-hop kappa', calibration labels | 0.681 | [0.623, 0.734] | 0.835 | 0.95 |
| E2 - E1 + extrapolated curvature | 0.684 | [0.627, 0.737] | 0.836 | 0.95 |
| **E3 - fleet-calibrated, conformal 90%** | **0.962** | **[0.933, 0.981]** | **0.992** | **0.94** |

Rated region (11.5-14.5 m/s), 288 unit-bins:

| allowance rule | premise held | bound held | median S/e | silent | abstained |
|---|---:|---:|---:|---:|---:|
| C | 0.000 | 0.174 | 1.50 | 0.008 | 0 |
| P | 0.045 | 0.216 | 1.25 | 0.097 | 0 |
| E1 | 0.024 | 0.204 | 1.22 | 0.117 | 0 |
| E2 | 0.024 | 0.204 | 1.21 | 0.117 | 0 |
| **E3** | **0.997** | **0.997** | 0.68 | 0.360 | 0.243 |

Median S/e above 1 means the median row is an invalid bound.

E3 abstains (beta infinite) where fewer than 9 calibration units reach that
wind speed. That does not inflate its coverage: on the 218 rated-region bins
where it committed to a finite allowance, coverage was 0.995.

## Verdicts on the predeclared expectations, judged on 2017

| | expectation | result |
|---|---|---|
| A1 | zero bound failures where the premise held, every rule | **Holds.** 0 failures in 14,508 row-rule pairs, both years |
| A2 | E1/E2 beat P below rated but stay under 90% | **Holds.** 0.517 → 0.681 / 0.684 |
| A3 | neither E1 nor E2 covers the rated region | **Holds.** 0.024 |
| A4 | E3 reaches >= 0.90 coverage in both scenarios, validity as high | **Holds.** 0.962 and 0.997; validity 0.992 and 0.997 |
| A5 | E3 pays in informativeness, more in the rated region | **Holds**, mildly below rated (0.94 vs 0.98), strongly at rated (silent 36%, abstained 24%) |

The 2016 development numbers point the same way (E3 0.917 and 0.887 on
committed bins) and are in `allowance.txt`.

## What the ladder says

**Calibration labels alone cannot rescue the bound.** Longer hops help: E1
lifts coverage 16 points over the paper's rule, because it measures how the
law's error grows at distances like the ones it is used at. But it tops out at
68%, and the curvature term adds nothing — the dominant failure is the rotor
reaching its speed limit near 9 m/s, a kink that appears nowhere in the 4.5-8.5
m/s calibration data. Across the rated break no calibration-only rule covers
more than 5%: a plateau cannot be extrapolated from below it.

**Labelled residuals from comparable systems can.** E3 learns the law's error at
each wind speed from *last year's fleet* and applies the conformal quantile.
That turns beta from a declared number with no guarantee into one with a real
one: coverage at least 90% for an exchangeable new unit. It delivered 96% and
99.7% on a year it had never seen, with validity 99.2% below rated — while
still proving a median 94% of the error there.

**The informativeness has a caveat.** That 0.94 is high because these
surrogates extrapolate badly (median error 0.85 in log units, roughly a factor
of 2.3 in power): beside an error that large, the law's own error is small. An
accurate surrogate would mostly get a silent certificate, as on the capillary
corpus.

## What this changes in the method's claim

E3 works by spending a resource the original method was designed not to need:
**labelled outcomes in the extrapolation range, gathered on other units.** For
a wind farm that is free — every turbine logs its own power. For the capillary
corpus it does not exist: one apparatus, and the high-power data are the very
thing missing. So the honest statement of what SASES needs is:

> The bound is as reliable as its law allowance, and a reliable allowance needs
> either an external physical source (theory or a solver sweep, as Section 7
> already says) or exchangeable labelled residuals from comparable systems in
> the extrapolation range. Calibration data from the deployed system alone does
> not suffice, on either physical system tested.

And the theorem itself has now held in every one of 14,508 row-rule pairs where
its premise was met, on two unrelated physical systems.

## Scope

Turbine-months share six turbines; E3 in 2017 calibrates on 2016 data from the
same six turbines, a realistic deployment but not an out-of-site test. A
different wind farm - for example the Hill of Towie open dataset on Zenodo
(record 14870023) - would test transfer across sites. One seed per surrogate family, as declared.

Reproduce: place `Kelmarsh_SCADA_2017_3083.zip` (Zenodo 16807551) in
`external_data/kelmarsh/`, run `python run_wind_year.py 2017`, then
`python allowance_audit.py`.
