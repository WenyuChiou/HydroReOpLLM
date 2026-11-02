# Code structure and execution flow

Start with the [user guide](USER_GUIDE.md) to configure a study. This page shows
where the implementation and its supporting files live. You do not need to edit
the core Python modules to change a reservoir, network, model or prompt.

## Repository map

```text
HydroReOpLLM/
├── src/
│   ├── llm_reservoir_agent/     Reusable operations framework
│   └── hydrocnhs/               Bundled, attributed hydrology and routing engine
├── templates/                  Commented configuration starting points
├── examples/
│   ├── daily_offline/          Four-day single-reservoir and cascade examples
│   ├── multiple_reservoirs/    Network, local prompts and information examples
│   ├── fe_walter/              Worked study, extensions, inputs and saved examples
│   ├── fixed_interval/         Supplied fixed-interval inflow example
│   ├── time_scales/            Time-axis configuration examples
│   └── hydrology/, rules/, synthetic/
├── tutorials/                  Saved notebooks and their local configurations
├── cases/                      Case/response inputs used by example configurations
├── experiments/                Existing YAML entries for those example cases
├── data/                       Shared, pinned example inputs and geographic sources
├── docs/                       User manual, API reference and current figure sources
├── tests/                      Regression, failure, provider and physical checks
├── scripts/                    Build, installation and verification helpers
├── environment/                Constraints and bundled-engine source/runtime pins
├── third_party/, licenses/     Upstream attribution, source pins and patch records
├── archive/                    Small historical-source and recovery index
├── .github/workflows/          Automated tests and manual build
├── pyproject.toml              Dependencies, package data and CLI entrypoints
├── MANIFEST.in                 Source-distribution build-helper inclusion
└── run_experiment.py           Existing convenience launcher
```

{download}`Download the complete maintained file index <FILE_INDEX.txt>`.
The index lists repository files, not local environments, generated runs or Git
internals. Historical study outputs are retained only where the maintained
examples, notebooks, provenance or regression checks still consume them.

## From a configuration to a result

1. `workflow.py` reads YAML and selects the configured execution path.
2. `coupled.py` and `weather.py` prepare Daily HydroCNHS inflows when hydrology is
   configured. `network.py` validates the reservoir graph and routes releases.
3. `agent_configuration.py` creates independent operators for each reservoir.
   `configured_backend.py` assembles configured messages and invokes the selected
   adapter in `providers.py`; offline operators require no service.
4. `contracts.py` validates the proposed action. `physics.py` applies storage,
   release and spill constraints; the implemented outcome enters routing and
   the next completed-history observation.
5. `trace.py` writes decision, physical, audit and backend records.
   `verification.py` independently checks the saved run. `recovery.py` verifies
   and replays an interrupted prefix before any explicitly allowed continuation.

Operational reasoning and audit verdicts are separate from physical validity.
A completed simulation does not establish that a policy improved operation.

## Framework files by responsibility

| Responsibility | Files in `src/llm_reservoir_agent/` |
| --- | --- |
| Public interface and contracts | `__init__.py`, `plugins/__init__.py`, `contracts.py`, `runtime.py` |
| Configuration and execution | `configuration.py`, `workflow.py`, `experiment.py`, `case.py`, `agent_configuration.py`, `extensions.py` |
| Hydrology and reservoir network | `coupled.py`, `weather.py`, `network.py`, `agent.py`, `physics.py`, `balance.py`, `passive.py` |
| Prompts, providers and decision adapters | `prompt.py`, `context.py`, `configured_backend.py`, `providers.py`, `policy_adapter.py`, `policies.py` |
| Available information | `information.py`, `information_runtime.py`, `information_verification.py` |
| Audit and result checking | `audit.py`, `auditor.py`, `configured_audit.py`, `outcome.py`, `verification.py` |
| Rule benchmark and downstream evaluation | `rule_based.py`, `benchmark.py`, `benchmark_config.py`, `downstream.py`, `reach_validation.py` |
| Time axes and experimental interval paths | `time_axis.py`, `time_config.py`, `interval_network.py`, `interval_weather.py`, `temporal_output.py` |
| Durable records and recovery | `trace.py`, `recovery.py` |

The [module inventory](MODULE_INVENTORY.md) gives each module's purpose,
inputs/outputs, units, dependencies and test references. The [API reference](API_REFERENCE.md)
explains the public interfaces. The bundled `src/hydrocnhs/` tree retains its
separate upstream attribution and documented local patches.

## What a study author changes

| Goal | Files to configure | Guide |
| --- | --- | --- |
| Dates, warm-up, time step and output location | Experiment YAML | [Simulation settings](GLOBAL_SETTINGS.md) |
| Catchments, weather and routing parameters | Hydrology YAML and weather input files | [Hydrology](HYDROLOGY_SETUP.md) |
| Reservoir curves, storage, limits and graph | Reservoir/case YAML or JSON and local tables | [Reservoirs and networks](BUILD_SIMULATION.md) |
| Provider, model and explicit retry/fallback | Model settings referenced by the experiment | [LLM settings](MODEL_PROVIDERS.md) |
| System/user messages and extra information | Local prompt text, information settings and knowledge files | [Prompt and information](INFORMATION.md) |
| Custom response fields or policy checks | Explicit parser/auditor extension and its settings | [LLM interfaces](LLM_MODULES.md) |
| Inspect release, spill, storage and reasoning | New output directory created by the configured CLI | [Inputs and outputs](INPUT_OUTPUT.md) |

Start from `examples/daily_offline/`, then use `templates/coupled/` or the worked
`examples/fe_walter/coupled/` settings. Case-specific measurements, station IDs,
operating rules and prompts belong with the study, not in shared framework code.

## Source checkout versus installed package

The wheel installs the reusable `llm_reservoir_agent` and `hydrocnhs` packages,
plus explicitly declared notices/runtime pins and small offline examples.
Full teaching datasets, notebooks and editable figure sources stay in the
repository or research candidate bundle. They are not imported into the core
package. `scripts/package_build.py` builds through temporary staging so old
`build/lib` files cannot accidentally enter a wheel.

Temporary runs, QA command logs, developer caches, model weights and credentials
do not belong in tracked source. Keep them in separate working/output locations.
The small `archive/` index is retained for third-party source identity and optional
historical comparisons, not as another normal launch path. Superseded files remain
recoverable through Git history; cleaning this tree does not rewrite that history.


## Stage 1: calculate and save daily inflow

`configuration.read_configuration()` resolves explicit section files and calls
`agent_configuration.normalize_agent(spec)` before resource rebasing. That
function translates `reservoir_id`, `type`, rule/model/prompt selections and
`customization` into the existing engine configuration. It rejects a mixture of
public and legacy keys in one agent. Every
resource path is rebased against the file that declares it. Section references
replace the whole section and are pinned by hash.

`coupled.load_coupled_settings()` then validates all hydrology, physical network,
agent, prompt, information, extension and provider settings. `check` performs no
hydrology simulation, retrieval callback or provider request.

`weather.simulate_weather()` runs the accepted agent-free HydroCNHS model across
its complete continuous period. `coupled.prepare_coupled()` selects operation
dates and writes an ordinary pinned reservoir experiment with daily local inlet
boundaries. Preparation makes zero model requests.

## Stage 2: decide, apply release and route downstream

For each operation day:

1. `network.py` supplies prepared incremental local flows.
2. The agent receives its current immutable observation and committed history.
3. The registered rule backend returns a requested release, or
   `configured_backend.py` renders explicit
   system/user templates and calls the selected adapter in `providers.py`.
4. Response checking yields a requested controlled release or stops the step.
5. Auditors record diagnostic results without changing the proposal.
6. `physics.py` applies water availability and release limits, then computes
   spill and ending storage.
7. `network.py` routes implemented release plus spill downstream once.
8. `experiment.py` commits provider, decision, audit, physics and routing evidence
   before the next day can use the transition.

Hydrology is precomputed before daily operation. Same-day downstream flow is not
returned to the decision that produced it.

## Extension boundary

Top-level `extensions` maps an ID to an explicit package `__init__.py`. The
registry pins source and exposes only declared contracts.

The two-reservoir example uses `build_context(config)` for local retrieval. It
returns a callback on immutable `DecisionContext`. The F.E. Walter example uses a
backend extension that preserves its native Anik message formatting and response
contract through the common configured provider transport.

Extensions can also provide auditors, information sources and response schemas.
Rule modules implement `validate_backend`, `build_backend` and `rebase_agent`;
`type: rule_based` selects their registry ID with `rule` and passes the opaque
`rule_parameters` mapping. Hanasaki is an example-local wrapper; the retained
internal `BenchmarkBackend` also supports old configurations.
`rule_based.RuleBasedBackend` wraps the selected backend, requires
`decide(observation)`, `policy_id` and `network_calls=0`, and records `rule_id`
provenance. It supplies no model transport. Offline verification of new public
rules uses this generic contract rather than recognizing an algorithm name.
Changing physics or routing is outside these decision-extension contracts and
requires separate physical acceptance.

## Failure and recovery

Provider attempts do not advance physics until a checked action exists. Each
attempt records the actual provider, model, request, response and failure class.
Authentication and configuration errors are terminal. Audit FAIL and physical
failure do not rerun the model. Evidence-write failure stops execution.

On Windows, only the atomic replacement of already-fsynced metadata receives a
short, bounded retry for sharing/permission errors. No model request, decision
or physical transition is repeated. A secondary ledger-read failure is retained
without replacing the original exception or preventing the failure summary.

Configured prompt history retains only the selected completed-step window.
Hydrology arrays, output records and journal bookkeeping still grow with the
simulation length; the whole simulator is not a constant-memory stream. Journal
finalization scans log bytes in fixed chunks instead of loading each full log
into memory.

`recovery.py` verifies the durable prefix, reconstructs committed state and writes
continuation to a new directory. It skips committed decisions and can reuse
captured replies. It cannot guarantee exactly-once delivery at an external
service across every crash boundary.

[Build a simulation](BUILD_SIMULATION.md) · [LLM modules](LLM_MODULES.md) ·
[Parameter reference](PARAMETER_REFERENCE.md)
