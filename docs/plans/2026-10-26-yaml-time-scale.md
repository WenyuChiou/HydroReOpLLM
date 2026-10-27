# YAML daily/hourly simulation and monthly output implementation plan

**Goal:** Integrate time-scale configuration into existing coupled YAML preparation and execution, retaining raw results and keeping LLM stopped.

**Architecture:** An optional strict top-level time mapping selects simulation_step daily/hourly and output_step daily/hourly/monthly. Existing documents without time retain old behavior. Hourly coupled preparation uses the already reviewed GWLF-derived kernel with a declared hourly model and per-hour forcing, then the existing v3 interval network. Monthly output is aggregation only; no native monthly hydrology and no implicit forcing/UH resampling.

**Tech stack:** Python, existing YAML validators, NumPy, CSV, pytest. Base local commit 62eef6a2c9e5e13a3307602ca963d679308d6c28. Native Codex execution is already authorized; no legacy executors or execution-choice question.

## Public contract
- time: {simulation_step: hourly|daily, output_step: hourly|daily|monthly}; output cannot be finer than simulation. If provided, both fields are required; unknown/mixed time fields fail.
- Explicit settings must match network dt_seconds and every reservoir physical dt_seconds. Legacy daily source/behavior remains unchanged.
- Hourly hydrology: engine gwlf_hourly (or selected by time hourly), forcing_step hourly, model and forcing paths, inflow_bindings. No prepared_from hydrology cache can bypass input/source/interval hash checks.
- Hourly model schema hourly-gwlf-model.v1: start_time UTC, dt_seconds 3600, steps positive int, catchments mapping. Each catchment has parameters, initial (including explicit B0), optional dry_gap_hours, and routing {dt_seconds:3600, unit_hydrograph: nonnegative normalized weights}.
- Hourly forcing CSV: timestamp,subbasin_id,precipitation_mm,temperature_c,pet_cm,seasonal_temperature_c. Depths are accumulated per interval, temperature is interval mean; seasonal temperature is declared aligned source input. Complete unique clock/catchment coverage required, no interpolation/disaggregation.
- Each local binding is exactly runoff:catchment, routed:catchment, or constant:0. No catchment used twice. Routed flows use explicit hourly UH, retain end-period channel water in balance.
- start_time/end_time operation bounds are UTC and end exclusive for hourly. Daily start_date/end_date remains inclusive.
- Monthly/daily derived summaries retain full native CSV/trace files, report covered duration and incomplete periods, integrate cms to m3 with real seconds, and distinguish end storage from mean storage. UTC calendar boundaries including leap years; no fixed 30-day months.
- No network generation/download/calibration, live campaign/config/source-pin changes, automatic LLM resume, merge/push or release.

## Lane ownership
| Lane | Scope | Acceptance |
| --- | --- | --- |
| Parent | time_config.py; coupled.py/configuration.py/workflow.py/experiment.py wiring; docs/examples; end-to-end tests | Offline CLI check/prepare/run/verify and existing daily regression |
| Hourly worker | interval_weather.py and tests/test_interval_weather.py only | Real hourly GWLF input+UH run, conservation, rejection of gaps/units/step conflicts |
| Output worker | temporal_output.py and tests/test_temporal_output.py only | Leap February/partial months/cross-boundary duration, flow volumes, storage summaries |
| Independent reviewer | final stable staged diff only | Single general review, targeted corrections only if needed |

Workers share the checkout and must preserve each other's files. Parent integrates after both APIs are stable, runs combined targeted suite, stages explicit paths/count, gets independent review and saves a local commit. No multi-locale/catalog/frontier benchmark acceptance presets apply.

## Tasks
1. Validate existing YAML, daily weather and v3 network contracts; save baseline hashes.
2. Implement strict simulation/output policy and forcing/model/routing consistency checks.
3. In parallel implement hourly weather driver and pure output aggregators with independent component tests.
4. Wire preparation, hashes/cache provenance, runtime and output-verification paths without altering legacy daily defaults.
5. Add runnable synthetic daily/hourly YAML examples; offline tests include mismatch-before-execution, complete hourly chain, zero HTTP and monthly volume reconciliation.
6. Run targeted original and new tests and actual offline CLI demonstrations, preserving all logs.
7. Review final stable diff, fix verified issues, preserve review evidence and commit locally. Hourly empirical C&V remains a distinct future gate.
