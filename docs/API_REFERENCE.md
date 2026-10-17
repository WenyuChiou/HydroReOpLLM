# Python API documentation

Start with the [F.E. Walter tutorial](../tutorials/fe_walter.md)
when configuring a study. This reference explains the selected Python interfaces
behind the CLI and the contracts needed to add a rule, parser or context source.
The [code structure](CODE_STRUCTURE.md) maps the remaining implementation modules.

Use the [HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/index.html)
for native model building, rainfall–runoff, routing, calibration and data collection.
The added package does not replace those APIs.

## Experiment entry points

Import these functions from `llm_reservoir_agent.coupled`:

| Function | Inputs | Returns/effect |
|---|---|---|
| `load_coupled_settings(path, *, runtime_root=PROJECT_ROOT)` | Experiment YAML path; runtime assets root | `CoupledSettings` containing resolved data, physical case, weather, pins and report. Validates only; no hydrology/model call. |
| `prepare_coupled(settings, *, runtime_root=PROJECT_ROOT)` | Validated `CoupledSettings` | Preparation manifest dictionary; computes/reuses hydrology and writes a new output. No model call. |
| `prepared_experiment(settings)` | Current coupled settings | Path to the generated operation YAML, after checking preparation hashes and settings. |
| `run_coupled(settings, *, allow_network=False, runtime_root=PROJECT_ROOT, transport=None)` | Coupled settings; explicit network gate; optional injected transport | Two-item tuple `(records, trace_summary)`, returned by the operation runner. `records` maps reservoir graph keys to daily observation/transition records; `trace_summary` is the finalized trace document, including `status` and nested `summary`. Prepares if necessary, then runs decisions, physics and routing. |

`runtime_root` locates the accepted runtime manifests and supporting assets.
Repository runs use the project root. An installed-wheel application must provide
those assets explicitly, as in the external-wheel acceptance example.
`transport` is an advanced testing injection, not another operating method.

Read a plan without executing a model:

```python
from llm_reservoir_agent.coupled import load_coupled_settings

settings = load_coupled_settings("examples/fe_walter/coupled/llm_available.yaml")
print(settings.report["days"])             # 366 operation days
print(settings.report["llm_agent_count"])  # 1
print(settings.report["network_calls"])    # 0 during this check
```

Configuration, date, mapping and input-change validation errors raise `ValueError`;
invalid field types can raise `TypeError`. Missing/unreadable resources propagate
file errors. `prepare_coupled()` raises `FileExistsError` for an existing output.
`prepared_experiment()` raises `ValueError` for incomplete, changed or checksum-mismatched
preparation. `run_coupled()` also raises `ValueError` when LLM execution lacks the
network/live-readiness gate; provider, evidence and physical errors propagate.

For an already prepared/supplied-inflow study,
`workflow.load_settings(path, *, runtime_root=PROJECT_ROOT, information_providers=None)`
returns `ExperimentSettings`.
`workflow.run_settings(settings, *, allow_network=False, runtime_root=PROJECT_ROOT,
transport=None, information_providers=None, recovery=None, output=None, run_id=None)`
returns the same `(records, trace_summary)` tuple. Recovery arguments serve the
resume machinery. Use the coupled entry for weather-driven studies.

For an intentional rule run into a new output (this example performs hydrology
preparation if necessary):

```python
from llm_reservoir_agent.coupled import load_coupled_settings, run_coupled

settings = load_coupled_settings("examples/fe_walter/coupled/experiment.yaml")
records, trace_summary = run_coupled(settings)
print(len(records["FEWalter"]), trace_summary["status"])
```

## Decision contracts

Import `ReservoirObservation`, `ReservoirAction` and `parse_action` from
`llm_reservoir_agent`:

| Interface | Parameters | Result |
|---|---|---|
| `ReservoirObservation` | `timestep`, `timestamp`, `inflow_cms`, `release_upper_bound_cms`; optional `state`, `context`, `schema_version` | Detached decision state shared by rules and LLM backends. |
| `ReservoirAction` | `release_cms`; optional `schema_version` | Requested mean controlled release; does not calculate spill. |
| `parse_action(candidate)` | Action object or exact normalized mapping | Validated `ReservoirAction`; rejects unsupported fields/types and invalid flow. |

These constructors/parser raise `TypeError` for coercive/nonnumeric inputs and
`ValueError` for invalid schema versions, missing/extra fields, negative or
nonfinite flow. Observation state/context must contain finite JSON values.
`parse_action()` accepts an omitted schema version as the current schema;
provider response schemas can require the explicit version.

```python
from llm_reservoir_agent import parse_action

action = parse_action({"schema_version": "reservoir-action.v1", "release_cms": 5.0})
print(action.release_cms)  # 5.0 m3/s; illustrative value
```

See [Inputs and outputs](INPUT_OUTPUT.md) for observation fields, provider-specific
raw replies and the distinction between requested and implemented release.

## Prompt and context

`prompt.PromptSpec(strategy_id, version, template, knowledge_package_ids=(),
knowledge_package_sha256={}, system_template="")`
identifies explicit user/system templates and optional pinned knowledge sources.
`prompt.PromptRequest(messages, metadata={})` holds the rendered role/content
messages and provenance; it is not the raw provider reply.

`context.DecisionContext(agent_id, observation, previous_transition)` is the
immutable input to a custom context callback. `previous_transition` is `None`
on the first step. Return `context.ContextValue(value=None, provenance={}, available=True)`.
Use provenance to identify source bytes, query/document IDs and availability time.
The mapping defaults shown here are fresh per instance. Prompt identities/content
must be nonempty; knowledge IDs and hash keys must agree. Invalid message shape,
provenance or nonfinite context raises `TypeError` or `ValueError`. An unavailable
required context binding stops prompt rendering.

```python
from llm_reservoir_agent.context import ContextValue

def build_context(config):
    """Extension hook; replace this fixed example with your own retrieval."""
    def retrieve(context):
        return ContextValue(
            value=config["text"],
            provenance={"source": "explicit-study-guidance"},
        )
    return retrieve
```

Register the module under `extensions`, select it in `customization.context_providers`,
and place its alias in the prompt. This example performs no retrieval or model call.
`check` uses the configured preview rather than executing the callback.
See [prompt/context settings](CONFIGURATION.md#add-dynamic-context-with-an-extension).

## Rule extension contract

A `rule` value names an explicitly registered extension module, not a built-in
list of operating algorithms. The module supplies:

| Hook | Responsibility |
|---|---|
| `validate_backend(spec, *, base_path, runtime_root, physical, mode, days, model, auditor_settings, ...)` | Interpret and validate its own `rule_parameters`; return normalized settings and source pins. An optional declared `simulation_start` receives the start date. |
| `build_backend(settings, *, physical, runtime_root, mode, model, transport)` | Return a controller with `decide(observation)`, `policy_id` and `network_calls=0`. Rules receive no working model transport. |
| Optional `rebase_agent(spec, *, base_path)` | Resolve the module's declared resource paths relative to the declaring YAML. |

Validation failures from rule hooks propagate; an invalid hook result or missing
controller interface stops loading/execution. Rule code cannot use the provided
transport to contact a model. A minimal controller method is:

```python
from llm_reservoir_agent import ReservoirAction

class ExampleController:
    policy_id = "study-rule.v1"
    network_calls = 0

    def decide(self, observation):
        return ReservoirAction(release_cms=min(5.0, observation.release_upper_bound_cms))
```

This illustrates the return contract only. Supply the extension hooks, settings
validation and scientific rule required by the study before using it.
The generic `rule_based.RuleBasedBackend` records rule provenance and delegates
decisions. Physics/routing remain shared. The [Hanasaki example](../examples/rules/hanasaki/__init__.py)
shows concrete validation, relative file handling and controller construction.
It is an example implementation, not the generic algorithm definition.

## Model, audit and recorder modules

| Module/interface | Role |
|---|---|
| `configured_backend.validate_model_settings(mapping)` | Validate provider settings; omitted generation options stay omitted and unsupported options raise errors. |
| `configured_backend.ConfiguredBackend` | Render explicit prompts, call provider adapters, parse actions, retain attempts and apply explicitly configured fallbacks. Normally constructed by the loader. |
| `providers.py` | Native OpenAI, Anthropic, Gemini, Ollama and OpenAI-compatible request/response adapters. |
| `AuditSpec`, `AuditPlugin`, `AuditedBackend` | Versioned diagnostic checks and composition; audits do not override physics or resample target failures. |
| `experiment.record_provider_attempt(path, value)` | Durable attempt evidence. Write/flush failure raises `ProviderEvidenceError`. Normally called by the experiment runner. |
| `recovery.py` | Verify and reconstruct a committed prefix through the `resume` CLI. |

Use [auditor plugins](auditor_plugins.md) for custom check hooks and
[provider settings](MODEL_PROVIDERS.md) for supported profile fields.
Secrets belong in the selected environment variables, not settings or raw logs.

## Physical calculation and verification

`PhysicalConfig`, `Transition` and `apply_transition` are exported from
`llm_reservoir_agent`. Use the physical model separately from decision-making;
the normal CLI supplies the configuration and observation automatically.

`PhysicalConfig(reservoir_id, capacity_m3, dead_storage_m3, initial_storage_m3,
minimum_release_cms, maximum_release_cms, dt_seconds=86400.0)` defines volumes
in m³, controlled-flow bounds in m³/s and interval seconds.
`apply_transition(config, storage_start_m3, inflow_cms, target_release_cms)`
returns a `Transition` with requested/implemented controlled release, spill, total
outflow, ending storage, residual, minimum-release shortfall and adjustments.
Evaporation and seepage are zero. Invalid numeric inputs/limits raise
`TypeError`/`ValueError`; impossible or nonfinite computed balances raise
`ArithmeticError`.

```python
from llm_reservoir_agent import PhysicalConfig, apply_transition

physical = PhysicalConfig("demo", 1_000_000, 0, 500_000, 0, 20)
step = apply_transition(physical, 500_000, 2.0, 3.0)
print(step.storage_end_m3)  # 413600.0 m3
print(step.total_outflow_cms)  # 3.0 m3/s; no spill in this illustration
```

`verification.verify_run(output, *, require_offline=False, expected_audit_suites=None)`
returns a verification report for saved files. `require_offline=True` rejects a
record containing actual provider calls. It does not turn a live run into replay.
The returned dictionary includes `status`, `days`, `reservoir_count`,
`reservoir_days`, dates, audit counts, balance/routing differences and observed
calls. Invalid or incomplete evidence raises `ValueError`; missing files propagate
file errors. Audit FAIL/WARN/UNKNOWN values remain diagnostic results in the report.

```python
from llm_reservoir_agent.verification import verify_run

report = verify_run("runs/fe-walter-coupled-rule/operation", require_offline=True)
print(report["status"], report["days"])
```

Run that verification example only after the named run completes. Read-only
verification makes no model request and cannot replace missing execution evidence.

The supported user sequence remains `check → prepare → run → verify`, with
`resume` after interruption. See [the walkthrough](BUILD_SIMULATION.md) for CLI
arguments, [parameter reference](PARAMETER_REFERENCE.md) for YAML fields and
[code structure](CODE_STRUCTURE.md) for module relationships.
