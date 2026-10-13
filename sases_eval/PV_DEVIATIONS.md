# Deviations from PV_PROTOCOL.md - recorded before any result was computed

Decided after counting usable records per year, and before computing any law
residual, power curve, certificate or error. The predeclared analyses are run
exactly as written; the items below are ADDED alongside them, never in place of
them.

Usable irradiance timestamps (both pyranometers positive, within 5%, 150-1100
W/m2): 2017 5,184 (Aug-Dec); 2018 30,081; 2019 8,626; 2020 91; 2021 649;
2022 1,874; 2023 24,796. The plant's pyranometers were largely offline
2020-2022. The 5% agreement filter, as declared, rejects 28% of in-range rows.

1. Surrogate scoring year. The protocol named 2019, which turned out to be
   sparse. It is still run. 2018, the year with the most data, is ADDED.

2. E3 calibration pool. The protocol named the previous calendar year; for 2021
   to 2023 that pool is nearly empty, which forces abstention. It is still run.
   A leave-one-year-out pool (every other calendar year, all combiners) is
   ADDED. It keeps the scored unit's own year out of its calibration, so no
   label from the scored unit reaches beta; it is less realistic than learning
   only from the past, and is reported as such.

Nothing else changes: bands, bins, filters, the law, G_clip, rules and
hypotheses are as in PV_PROTOCOL.md.
