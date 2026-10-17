# Connect your simulation

Keep your accepted HydroCNHS model. Add the physical reservoir network, then
assign an operator to each controlled reservoir. This page explains the common
sequence; the [FE Walter tutorial](../tutorials/fe_walter.md) shows every actual file.

Steps: [inputs](#2-accept-the-hydrocnhs-model-first) →
[water connections](#3-bind-hydrology-to-the-reservoir-network) →
[agents](#4-choose-an-agent-for-every-controlled-reservoir) →
[execution](#5-check-without-running-anything).

## 1. Install the project

Follow [Installation](GETTING_STARTED.md), then check `reservoir-experiment --help`.

## 2. Accept the HydroCNHS model first

Prepare basin boundaries, model parameters and calibration/validation with the
[HydroCNHS tutorials](https://github.com/cylin928/HydroCNHS/tree/main/tutorials).
This entry accepts an agent-free GWLF or ABCD model with Lohmann routing.

Supply complete precipitation, temperature and PET data for its continuous
period, including warm-up. The reservoir-operation dates select a period within
that model record. Initial reservoir storage is a separate physical setting;
hydrological warm-up does not determine it.

See [input formats and units](INPUT_OUTPUT.md) and the detailed
[weather reference](WEATHER_INPUTS.md).

## 3. Bind hydrology to the reservoir network

![Map water sources and agents](figures/reservoir-agent-mapping.svg)

*Figure 2. Blue arrows carry water; orange arrows carry the current reservoir
state and requested release. Explicit IDs connect the files.*

| Setting | Meaning |
|---|---|
| `hydrology.model`, `hydrology.forcing` | Paths to the native model and complete weather table. |
| `hydrology.inflow_bindings` | Which native runoff or routed outlet supplies each operation inlet. |
| Reservoir `inflow_node` | The inlet supplying this reservoir. |
| `network.connections` | Directed water paths between reservoirs, inlets and downstream nodes. |
| `network.outlets` | Terminal nodes, including separate outlets for independent river systems. |

For reservoirs in series, downstream local input contains only additional runoff.
Upstream release and spill arrive through the network connection. Binding that
same upstream water again would count it twice. Information sources describe
what an operator can see; they do not create water paths.

The physical case also sets capacity, initial/dead storage, release limits and
the daily interval. The current reservoir kernel assumes zero evaporation and
seepage. Full field definitions are in the [parameter reference](PARAMETER_REFERENCE.md).

## 4. Choose an agent for every controlled reservoir

An agent's `reservoir_id` must match its physical reservoir. Choose `type:
rule_based` with your registered rule and its parameters, or `type: llm` with
a model profile and explicit prompt. Hanasaki is a supplied example rule, not
the definition of Rule-based operation. Passive outlets have no decision agent.

Read [Configure agents](CONFIGURATION.md) for the minimal LLM settings, optional
knowledge and custom prompt variables. Shared model settings do not share state
or history between reservoirs.

## 5. Check without running anything

```powershell
reservoir-experiment check examples/fe_walter/coupled/current/experiment.yaml
```

`check` validates referenced files, dates, IDs, model settings and prompt inputs.
It runs neither hydrology nor a model request. Paths are relative to the file
that declares them.

## 6. Prepare hydrology

`prepare` runs HydroCNHS over its full continuous period and saves daily inflow
for the operation dates. It makes no model request. A verified matching
preparation can be reused when comparing operation methods; see
[reuse a preparation](WEATHER_INPUTS.md#reuse-a-preparation).

## 7. Run the rule-based case

`run` repeats this daily loop: read inflow and state, request release, apply
reservoir physics, route actual outflow downstream, save the completed day.
The next day uses the updated storage and history. Upstream rainfall–runoff
remains the saved input.

Start with a rule when checking a new network. To select an LLM, change the
agent method and model/prompt references while retaining the physical inputs.
Only an LLM `run` needs `--allow-network`. The [run chapter](RUNNING.md) gives
the complete commands and output paths.

## 8. Verify and read the result

`verify` checks saved records, water balance and routing. Read the
[water-level and release results](RESULTS_GUIDE.md) first. Provider attempts and
audits are explained separately in the [records reference](RECORDS.md).
Completion and balanced water do not establish that an operation target was met.

## 9. Resume after an interruption

Preserve the partial run and continue into a new directory with `resume`.
Follow [Run and resume](RUNNING.md#resume-an-interrupted-run) for the exact
output-path convention and the limits of request recovery.

Next: [FE Walter step by step](../tutorials/fe_walter.md), or
[multiple-reservoir configuration](MULTI_RESERVOIR.md).
