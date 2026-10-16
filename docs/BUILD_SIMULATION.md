# Build a coupled simulation

Prepare a trusted hydrological model, define the reservoirs, then choose how each
operator makes decisions. HydroOpsLLM focuses on the decision layer: what the
operator knows, how a release is proposed, and how that proposal affects the
reservoir and downstream river.

**Current entry point.** The experiment CLI accepts supplied daily inflow and
executes native HydroCNHS Dam operations and routing. A single weather-driven
entry point is being designed; the native integration recipe below still needs
explicit Python binding. There is no weather-mode YAML switch in the current CLI.

## 1. Establish the hydrological boundary

For a new catchment, prepare the native HydroCNHS model, subcatchment weather,
parameters and river routing. Declare the warm-up and independent calibration /
validation periods. Fix the accepted hydrological parameters before comparing
operation methods.

Users with an accepted model can start from its verified configuration and data.
HydroOpsLLM does not require a new calibration when only the decision method changes.
Follow [HydroCNHS setup and C&V](HYDROLOGY_SETUP.md) for input units and native APIs.
The [FE Walter hydrology chapter](../examples/fe_walter/hydrology.md) records this
case's subcatchments, parameter derivation and gauge-scale evidence.

## 2. Define the shared reservoir case

Set capacity, dead storage, initial reservoir storage, controlled-release limits
and river connections. Keep hydrological warm-up separate from reservoir
initialization. A chosen operation start date must have explicit starting
conditions and consistent routing history.

Use **m³/s** for flow, **m³** for storage and ISO dates. For supplied inflow, provide
local/incremental flow at each routing node. Water released upstream is routed by
the host; including it again in a downstream local-flow file would count it twice.
See [case files and physical settings](USER_GUIDE.md#1-prepare-your-files).

When comparing methods, reuse the physical case, forcing, routing and initial
conditions. Each method then develops its own storage and release history.

## 3. Choose an operation method for each reservoir

The experiment YAML assigns one independent decision unit to each controlled
reservoir through `agents.<id>.reservoir`. It also selects that unit's strategy.
Passive outlets use physical discharge calculations and have no decision agent.

| Choice | Current configuration | What changes |
|---|---|---|
| Published rule-based benchmark | `strategy: benchmark`, `mode: offline` | Rule coefficients and reference inflow statistics |
| Your LLM instructions | `strategy: configured`, `mode: llm` | Prompt, selected information, optional knowledge and model profile |
| Preserved reference example | `strategy: reference_v3_7` | The example's own prompt/retrieval settings and live or fixture mode |

`offline` describes execution without model requests; it is not a synonym for
rule-based operation. The benchmark is one implemented rule, not a loader for
arbitrary operating rules. Another rule can implement the common
`decide(observation)` Python interface and be bound as a policy.

Both rule-based and LLM methods request controlled release. The common reservoir
calculation determines implemented release, spill and ending storage. Selecting
an LLM does not replace hydrology, routing or physical limits.

## 4. Define what the operator knows and is asked to do

Keep the fixed operating instructions in a prompt file. Select changing
information separately: current inlet and beginning storage, prior implemented
releases, and any eligible downstream observations, forecasts or demands.
An input must state its unit and when it becomes available. A simulated downstream
result from today's release can inform a later decision, not that same decision.

| Setting group | Owner and purpose |
|---|---|
| Native hydrological model | Subcatchment properties, GWLF / ABCD parameters and physical routing |
| Case JSON | Reservoir physics, initial storage, node connections and supplied-inflow source |
| Agent strategy | Rule parameters or the selected LLM decision implementation |
| `models` | Provider, model ID, sampling settings, timeout and output-token limit |
| Prompt and information profile | Operating instructions, response fields and selected decision-time data |
| Optional knowledge | Identified source documents; retrieval depends on the selected strategy |
| Auditors and outcome checks | Explicit operating criteria and completed downstream-flow checks |

The LLM receives information; it cannot overwrite the host's inlet, storage or
physical parameters. A rule uses only the fields its code implements. Adding a
field to a data file does not make an existing rule use it.

Continue with [prompt and model configuration](USER_GUIDE.md),
[decision information](INFORMATION.md) and [replaceable LLM modules](LLM_MODULES.md).

## 5. Verify the interfaces before requesting model decisions

First check file paths, units, dates, reservoir IDs and configuration. Use a
deterministic policy or saved response to test the connection without inference.
For LLM methods, inspect the rendered prompt, raw reply, parsed requested release
and response-validation outcome.

Check operating criteria separately from response format. A structurally valid
reply can still receive an audit FAIL, WARN or UNKNOWN. These diagnostic verdicts
remain in the trace; physical limits are applied by the reservoir calculation.
Use a new run ID and output directory for each new experiment.

## 6. Follow one daily coupled clock

| At day t | Passed to the next step |
|---|---|
| Route upstream water to the reservoir | Inlet flow and beginning storage |
| Assemble information and apply the selected method | Requested controlled release; LLM methods may retain rationale and other fields |
| Validate the proposal and calculate reservoir operation | Implemented controlled release, spill and ending storage |
| Route total outflow and retain evidence | Controlled release + spill enters the river once |
| Advance to day t + 1 | Ending storage and implemented-release history; eligible completed downstream results |

The bundled HydroCNHS core computes the runoff series before advancing routing
and agents daily. Daily coupling refers to the shared clock and causal exchanges.
Hydrological setup, decision-interface checks and coupled acceptance are separate
verification steps; none alone establishes success of the complete application.

For weather-driven native execution, follow the
[model, Dam-policy and trace binding recipe](../examples/fe_walter/coupling.md#3-connect-a-weather-driven-native-run).
Treat it as integration work until the configured host, warm-up boundary and
output evidence have passed the checks below.

## 7. Accept the coupled connection, then assess the policy

Before a larger study, verify:

- **Water and time:** one storage update per day, one outflow injection, closed
  reservoir/network balances, and no skipped or duplicated dates.
- **Decision continuity:** the next beginning storage equals the committed ending
  storage, and histories contain implemented flow rather than an unexecuted request.
- **Information and evidence:** no future downstream data; prompt, reply, action,
  audit and physical result remain linked, including rejected decisions and errors.

Then assess operating performance over the intended study period. A coupling test
does not establish that an LLM follows the operating criteria.

Start the [FE Walter shared case](../examples/fe_walter/README.md), then compare
rule-based operation, LLM operation with available information, and operation with
retrieved guidance. The [settings guide](USER_GUIDE.md#6-check-run-and-verify)
provides the supported check, run and verify commands.

For a complete calendar-year exercise, follow
[Run a full year](../examples/fe_walter/annual/README.md). It walks through data,
C&V evidence, annual preparation, method selection, execution and the source code
responsible for each connection.
