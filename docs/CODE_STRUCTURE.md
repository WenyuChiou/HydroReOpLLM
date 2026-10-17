# Code structure and execution flow

Users normally enter through `reservoir-experiment`. The modules below explain
where configuration, model requests, physics and evidence remain separated.

## Reusable installed modules

```text
src/
  hydrocnhs/                         GWLF/ABCD, Lohmann routing and Dam API
  llm_reservoir_agent/
    configuration.py                v1/v2 sections, declaring-file paths and pins
    agent_configuration.py          public agent keys normalized into the existing engine
    rule_based.py                   source-pinned rule wrapper and generic rule provenance
    weather.py                      full-period forcing validation and simulation
    coupled.py                      check and compile the two-stage simulation
    workflow.py                     check / prepare / run / verify / resume CLI
    network.py                      daily reservoir and downstream routing host
    physics.py                      release bounds, storage balance and spill
    prompt.py                       explicit PromptSpec system/user artifacts
    context.py                      immutable DecisionContext and ContextValue
    information.py                  causal information sources and profiles
    providers.py                    five native request/response adapters
    configured_backend.py           prompt rendering, attempts and fallback profiles
    extensions.py                   explicit source-pinned extension registry
    audit.py / auditor.py           normalized diagnostic checks
    experiment.py                   durable decision and provider evidence
    recovery.py                     verified interrupted-prefix reconstruction
```

Regional calibration evidence, prompts, statistics and extension code live under
`examples/` and `data/`. They are study inputs, not defaults for another basin.

## Stage 1: prepare hydrological boundaries

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

## Stage 2: decide, implement and route

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

`recovery.py` verifies the durable prefix, reconstructs committed state and writes
continuation to a new directory. It skips committed decisions and can reuse
captured replies. It cannot guarantee exactly-once delivery at an external
service across every crash boundary.

[Build a simulation](BUILD_SIMULATION.md) · [LLM modules](LLM_MODULES.md) ·
[Parameter reference](PARAMETER_REFERENCE.md)
