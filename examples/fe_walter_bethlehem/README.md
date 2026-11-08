# F.E. Walter to Bethlehem: downstream-stage preparation

[English](README.md) | [繁體中文](README.zh-TW.md)

This independent example prepares an extension of the existing F.E. Walter study
from Lehighton to Walnutport and Bethlehem. **It is a data-preparation example,
not a runnable or calibrated Bethlehem simulation.** The existing
[F.E. Walter example](https://wenyuchiou.github.io/HydroReOpLLM/docs/CASE_STUDIES.html) remains unchanged.

F.E. Walter is the only controlled reservoir. Observed flow below Beltzville is
a common external boundary for all policies. The eventual comparison will use
Rule-based MOSART-Urban, LLM without operational knowledge, and LLM with
operational knowledge with the same physical profile and forcing.

## Files and starting point

| File | Purpose |
|---|---|
| [preparation.json](preparation.json) | Scope, station/node distinctions, boundary ownership and unresolved requirements. This is a preparation record, not an experiment-CLI configuration. |
| [ratings_inventory.csv](ratings_inventory.csv) | Three current rating IDs, effective-date headers, source hashes and missing historical coverage. |
| [data_requirements.csv](data_requirements.csv) | Data to obtain and the C&V stage that needs each item. |
| [usgs_data_request.md](usgs_data_request.md) | An unsent request for historical rating/shift records and Bethlehem discharge conventions. |

Read the station findings below, obtain the missing records, and then follow the
C&V sequence. There is no `reservoir-experiment run` command for this example yet:
new catchment inputs, river routing and a stage provider must first be built.
Store retrieved data and generated outputs in your own study directory; preserve
source URLs, retrieval timestamps, bytes, hashes and quality flags.

## Station and rating findings

The public STAC assets were retrieved on 2026-11-08 UTC. Base tables and currently
shifted `exsa` tables were available for all three stations:

| Station | Current rating ID | `RATING_DATETIME BEGIN` in the base file | Complete 2021–2025 rating/shift history? |
|---|---|---|---|
| Lehighton 01449000 | 12.0 | `20250506231500`, `BZONE=-05:00` | No; earlier versions and shifts remain missing. |
| Walnutport 01451000 | 26.0 | `20250507171500`, `BZONE=-05:00` | No; earlier versions and shifts remain missing. |
| Bethlehem 01453000 | 43.0 | `20260317150700`, `BZONE=-05:00` | No; this version begins after the study period. |

These timestamps preserve the source headers; their clock interpretation must
be verified before constructing UTC validity intervals. A file's retrieval time
or STAC item timestamp does not establish when a rating was effective. The
downloaded files also mark the ratings provisional/working. The current shifted
table does not supply the complete historical sequence of shifts and corrections.
[USGS guidance explicitly cautions against applying current ratings to historical
data](https://www.usgs.gov/centers/pennsylvania-water-science-center/science/surface-water-monitoring-pennsylvania).
Obtain applicable approved rating versions, effective intervals, shifts,
corrections and revision histories before historical Q-to-stage evaluation.
Field discharge measurements support that work but do not replace these records.

The [USGS STAC service](https://api.waterdata.usgs.gov/docs/stac/) exposes file
assets, including the base and `exsa` URLs in `ratings_inventory.csv`. A successful
download is evidence of availability of that snapshot, not historical coverage.

### Stage and elevation are different quantities

Use **00065 gage height**, in feet above each station's local zero, for local
stage comparisons. Keep absolute water-surface elevation, including parameter
63160 where supplied, separate. The
[USGS Pennsylvania datum notice](https://www.usgs.gov/centers/pennsylvania-water-science-center/updating-pennsylvania-streamgage-datums)
states that its geodetic-datum updates do not change observed local stage or
discharge. Its table reports updates for Walnutport in October 2022, Bethlehem
in August 2023, and two listed dates for Lehighton in 2022/2023. Do not add the
NGVD29-to-NAVD88 elevation difference to the 9/7/12-ft WCM stage thresholds.
Other historical gage relocations or changes in local zero still need checking.
Those three WCM action stages alone are not a complete A/B/C/D decision rule.

### Bethlehem needs two explicit comparison definitions

The [USGS water-year 2000 station description](https://pubs.usgs.gov/wdr/2000/dela-00/wdr_del-2000/pdfs/01453000.pdf)
places the physical gage about 1,800 ft upstream of Monocacy Creek while stating
that published discharge and the 1,279-mi² drainage area include Monocacy flow.
This establishes the historical convention; it does not independently establish
the 2021–2025 computation or the exact study-period geometry.

Keep two provisional node definitions until USGS confirms the study-period
convention:

- `bethlehem_stage_gage`: flow and stage at the physical gage location.
- `bethlehem_published_discharge`: the flow quantity used for comparison with
  published 01453000 discharge, including any documented Monocacy adjustment.

Do not invert the Bethlehem rating using an assumed upstream-only discharge,
or assume subtraction of Monocacy observations resolves the issue. Confirm what
discharge quantity the rating itself represents, travel alignment and any
published adjustment first. If confirmed, use a separately specified adjustment
or measurement operator. A future physical-stage model must not route Monocacy
upstream of its actual confluence. The two definitions are comparison contracts,
not an implemented hydraulic connection.

## Common Beltzville boundary

Use observed **00060 streamflow at 01449800** as a common external boundary,
subject to numerical completeness and quality checks. It is a creek gage below
the dam, not a direct gate-release measurement; the
[USGS description](https://pubs.usgs.gov/wdr/2001/del-01-1/pdfs/01449800.pdf)
also identifies upstream Wild Creek/Penn Forest regulation and a diversion.

Route this flow from the gage to the Lehigh, adding only runoff below the
boundary. Exclude its already represented upstream catchment from additional
GWLF runoff and other overlapping observed boundaries. Inspect tributary mouths,
nested gages, diversions and intervening drainage before closing the water budget.
Pool elevation at 01449790 is a separate boundary-information dataset if required
by the selected joint-operation rules; it does not make Beltzville controlled.

All policies receive the same external boundary time series. Its use as hindcast
forcing does not make a full day's eventual mean available to the LLM at the
start of that day. Expose only completed or explicitly published information.

## Data preparation and C&V sequence

1. **Resolve sources and geometry.** Obtain the three historical rating/shift
   histories and study-period datum/local-zero records. Resolve Bethlehem's
   published-Q versus physical-stage convention, delineate mutually exclusive
   areas and fix station and tributary locations.
2. **Assemble the numerical inputs.** Audit discharge, stage, Beltzville boundary,
   precipitation, temperature, PET, land/soil and reach geometry. Retain missing,
   estimated, ice-affected and revised values explicitly. Select C/V periods
   using common data coverage, not model scores.
3. **Run new runoff and routing C&V.** Retain the accepted FEW upstream parameters
   initially and regression-check their behavior. Fit necessary new-area
   parameter groups and Lehighton–Walnutport–Bethlehem routing using observed
   upstream boundaries to isolate new-reach errors. Compare volume, KGE, RMSE,
   peak magnitude, peak time and recession. Register acceptance criteria before
   fitting; individual ungaged units remain regionally inferred.
4. **Validate Q-to-stage and the complete chain.** For all three stations,
   including Lehighton, evaluate stage bias/RMSE and threshold-crossing time,
   duration, false alarms and missed crossings. If applicable ratings do not
   adequately reproduce flood-stage behavior, assess cross sections, roughness
   and backwater/hysteresis before choosing a hydraulic alternative. Published
   Q may derive from stage/rating, so Q and H scores are not independent truth.
   Then verify the free-running FEW-to-Bethlehem chain, feasible release pulses,
   routing tails and whole-system water balance.
5. **Connect decision information.** Each policy's own actual controlled release
   plus spill must generate its own routed Q and stage history. Only completed
   prior results inform the next decision. Historical observed main-stem stages
   are C&V targets, not replacements for simulated counterfactual feedback.
   Missing stage/trend stays unknown. Review the minimal information/prompt diff
   and rule-auditor behavior before starting a new LLM experiment.

Daily discharge C/V candidates retain the original 1990–2010/2011–2020 split
(1989 warmup) only if the new-area inputs support it. Archived instantaneous-H
catalogs begin in October 2007; **stage C/V dates are unassigned** until matching
H, ratings and boundary coverage are established. They need not equal the long
discharge C/V interval. The already examined 2021–2025 period is retrospective,
not a new blind test.

Daily mean flow does not determine instantaneous flood stage. Specify whether
an information item is an instantaneous, completed-interval or averaged value.
A study claiming complete subdaily A/B/C/D flood-control timing needs compatible
hydrology/routing and decision intervals; this preparation example makes no
such validation claim.

The shared [MOSART-Urban rule](../rules/mosart_urban/README.md) remains the
source-aligned benchmark. Operational knowledge and station-stage audits do not
silently change its release equation. If a safety controller changes actual
release, identify the constrained variant separately. Use the same physical
profile, starting state and inputs across all future comparison arms.
