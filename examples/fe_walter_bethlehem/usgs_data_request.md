# Draft request: historical Lehigh ratings and Bethlehem discharge convention

**Draft only; not sent.** Contact: Pennsylvania Water Science Center,
`GS-W-PA_is@usgs.gov`, as listed on the
[official contact page](https://www.usgs.gov/centers/pennsylvania-water-science-center/connect).

Subject: Historical rating/shift records for 01449000, 01451000 and 01453000

We are preparing a research model of F.E. Walter operations and the downstream
Lehigh River through Bethlehem. Our retrospective study period is calendar
2021–2025. We also need earlier overlapping years for stage calibration and
validation, preferably from October 2007 onward where stage is available.
The exact C/V periods will be chosen after data availability is established.

For stations 01449000 (Lehighton), 01451000 (Walnutport) and 01453000 (Bethlehem),
could you identify or provide:

1. The approved historical base stage–discharge rating versions and their exact
   effective start/end timestamps, timezone interpretation and revision status.
2. Complete time-dependent and stage-dependent shifts, stage corrections and
   any other adjustments used to compute historical discharge, including ice
   periods, extrapolated ranges and limitations during rising/falling floods.
3. Changes in local gage zero, physical location or instrumentation, together
   with geodetic datum histories and conversions. We understand the published
   Pennsylvania NAVD88 conversion notice states that these geodetic updates do
   not change local gage height or discharge; we wish to distinguish those
   changes from any separate local-zero or site changes.
4. The meaning of fixed `BZONE=-05:00` with station `TIME_ZONE=EST` and
   `DST_FLAG=Y` in rating-effective-date headers, to preserve the correct UTC
   chronology through daylight saving time.

The currently retrieved base assets identify rating 12.0 at Lehighton beginning
`20250506231500`, 26.0 at Walnutport beginning `20250507171500`, and 43.0 at
Bethlehem beginning `20260317150700`. We are retaining these snapshots but are
not assuming they represent the complete study-period rating/shift histories.

For Bethlehem specifically, the water-year 2000 station description places the
gage about 1,800 ft upstream of Monocacy Creek but states that published flow and
drainage area include Monocacy. For 2021–2025 and the earlier candidate C/V years:

- Does published 00060 still include Monocacy, and how is that contribution
  constructed or adjusted in daily and instantaneous discharge products?
- Does the distributed Bethlehem base/shifted rating relate the local gage
  height to flow at the physical gage, or to an adjusted published-flow quantity?
- Which physical location, upstream area, Monocacy flow source and travel-time
  alignment should be used when separately evaluating modeled stage and flow?

Our aim is to compare simulated physical gage height with local 00065 stage and
simulated flow with the corresponding published quantity without double-counting
Monocacy or applying an incompatible inverse rating. We would appreciate any
existing station analysis, public archive or data-service route that resolves
these questions. We are not requesting interpretation of model performance.
