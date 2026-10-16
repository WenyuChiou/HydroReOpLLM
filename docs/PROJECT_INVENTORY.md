# HydroOpsLLM project inventory

Cleanup baseline: **1,026 tracked files**, commit
`fbd9a993731ce979835dcc46f7a9cbad6aa7387b`.
The [complete inventory](../archive/inventory.csv) records classification,
dependencies, original bytes/hash and destination. The
[recovery index](../archive/README.md) documents the verified external archive.

| Layer | Preserved capability | Responsibility |
|---|---|---|
| Native HydroCNHS | GWLF/ABCD, Hamon PET, Lohmann routing, Dam/RiverDiv/Conveying/InSitu APIs | Hydrology and native coupling |
| Native tools | ModelBuilder, calibration, converters, indicators, data collector, sediment | Native APIs; see upstream tutorials |
| Added reservoir operations | Observation/action, physical limits, release, spill, storage, balance | Shared rule/LLM execution |
| Added LLM modules | Prompt/context, providers, parsing, checker, reservoir-local audit | Configurable proposals and trace |
| Networks | DAG, split/merge, delays, isolated agents, passive outlets | Physical/routing coupling; no central joint planner |
| Examples | F.E. Walter rule benchmark and two named LLM information designs | Main tutorial and advanced tutorial |
| Historical sources | Accepted inputs, old configs, vendor helpers, results | Reproducibility dependencies; old launchers/docs restored externally |

## Data flow

`run_experiment.py` → validate YAML/input/source pins → reservoir-local backend
→ requested release → checker → common physics → native Dam API/routing
→ implemented outcome → next observation and audit/trace.

The operations runner supplies fixed daily local inflows. It does not recompute
catchment runoff. Release can change storage and downstream routed inflow; it
does not alter hydrological equations or calibrated parameters.

HydroCNHS v1.2.1 is pinned at `fdd5097a3fcabb312c6c3739efc71da2d67c47da`.
Core/source/license hashes remain preserved. Configuration and C&V use the
[original APIs](HYDROLOGY_SETUP.md). Existing calibration is 1990–2010 and
validation is 2011–2020; no recalibration is part of this cleanup.

## Evidence and limits

Saved Ollama results contain three requests per LLM method, `gemma3:4b`,
temperature 0.7. LLM operation with available information has **2 PASS / 1 FAIL**;
LLM operation with retrieved knowledge has **3 FAIL**.
Execution and water balance do not certify an operating policy. Initial
storage, identity downstream routing and zero losses are teaching assumptions.

The three real reservoirs lie on separate branches. Their saved January test
models reservoir contributions, not complete downstream river discharge.
Historical 2016–2020 results, audit failures, 13 known failed requests and
attempt 1289's unknown result/cost remain intact. Source license boundaries
and private-repository status are unchanged.
