# HydroReOpLLM project inventory

## Current code and inputs

| Location | Purpose |
|---|---|
| `src/llm_reservoir_agent/` | Generic configuration, providers, decisions, physics, routing and records |
| `src/hydrocnhs/` | Bundled upstream hydrology, calibration and routing modules |
| `templates/coupled/` | Commented configuration templates for a new study |
| `examples/fe_walter/extensions/` | Case formatting, response interpretation and optional compatibility helpers |
| `examples/fe_walter/coupled/` | One maintained set of experiment, method, model and physical settings |
| `examples/fe_walter/legacy/` | Compatibility code used by regression tests; excluded from the installed package |
| `examples/fe_walter/prompts/` | One current system prompt for each LLM method |
| `examples/fe_walter/knowledge/` | The operating text retrieved by the knowledge method |
| `examples/synthetic/` | Invented inputs for older demonstration configurations |
| `archive/fe_walter/` | Historical source hashes and external recovery instructions |
| `tests/fixtures/` | Synthetic inputs for tests, separate from research results |

The former root `knowledge/` contained only invented R1/R2/R3 guidance; it now
lives with the synthetic example. The former root `prompts/` contained compatibility
templates, now stored with their example or under `templates/legacy/`.
The supplied original Anik Python files are excluded from the current tree;
[optional reference checks](../archive/fe_walter/README.md) use a verified external artifact.
Historical record paths remain as originally recorded.

The case's canonical entry is `coupled/experiment.yaml`. The two LLM entries
share `coupled/models.yaml`; duplicate version-named entries and the extra
`current/` directory have been removed. Earlier configurations can be recovered
from their recorded Git revision, without changing a completed experiment.

Installed wheels contain only the current generic package and bundled HydroCNHS
modules. Wheel builds use private temporary staging, so modules left in an old
local `build/lib` directory cannot enter a new distribution.

The project is named **HydroReOpLLM** and its distribution is `hydroreopllm`.
Python imports (`llm_reservoir_agent`, `hydrocnhs`), command names and schema IDs
remain stable. Installed support files retain the `share/llm-reservoir-agent/`
path used by the runtime. Historical record keys and recovery artifact names
retain their original spelling.

## Earlier inventory

Cleanup baseline: **1,026 tracked files**, commit
`fbd9a993731ce979835dcc46f7a9cbad6aa7387b`.
The historical CSV is retained at Git revision `f6eff89:archive/inventory.csv`;
it records that earlier tree, not the current package. The
[recovery index](../archive/README.md) documents the verified external archive.
For the current repository, use [project structure and file index](CODE_STRUCTURE.md).

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

`reservoir-experiment` → read settings and prepare upstream inflow → reservoir-local backend
→ requested release → checker → common physics → native Dam API/routing
→ implemented outcome → next observation and audit/trace.

The operations runner supplies fixed daily local inflows. It does not recompute
catchment runoff. Release can change storage and downstream routed inflow; it
does not alter hydrological equations or calibrated parameters.

HydroCNHS v1.2.1 is pinned at `fdd5097a3fcabb312c6c3739efc71da2d67c47da`.
The source manifest preserves the upstream identity and records one versioned
local patch for `Visual.plot_reg` metric calls. Hydrology and license bytes
remain unchanged. Configuration and C&V use the
[original APIs](HYDROLOGY_SETUP.md). Existing calibration is 1990–2010 and
validation is 2011–2020; no recalibration is part of this cleanup.

## Evidence and limits

The current tutorial uses the saved 2016 Rule-based baseline and the two current
framework LLM trajectories, each with 366 daily records. Model settings and
source hashes are retained with the result provenance. Read the
[current results](../examples/fe_walter/results.md) for water level and controlled release.

The historical three-day, three-reservoir and 2016–2020 studies remain separate
evidence. Their old model settings, failed requests and unknown costs are
preserved; they are not the inputs to the current tutorial.
