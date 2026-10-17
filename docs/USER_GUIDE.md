# User guide

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

Start with an accepted HydroCNHS model. HydroOpsLLM adds a reservoir network,
an operator for each controlled reservoir, and records of each decision.

## Check, run and verify

1. [Install](GETTING_STARTED.md) the package.
2. [Separate the inputs](INPUT_OUTPUT.md): experiment, hydrology, reservoirs and agents.
3. [Connect your simulation](BUILD_SIMULATION.md): map hydrological outlets to reservoir inlets.
4. [Configure agents](CONFIGURATION.md): choose Rule-based or LLM for each reservoir.
5. Follow the [FE Walter tutorial](../tutorials/fe_walter.md), starting with its actual `experiment.yaml`.
6. [Run and verify](RUNNING.md), then [read the results](RESULTS_GUIDE.md).

You can read the tutorial and saved results without starting a model. **Offline**
means no live provider request. A **baseline** is a comparison run, such as the
Rule-based method; it is not a third agent type.

## Understand the execution boundary

HydroCNHS calculates upstream inflow over the continuous model period, including
warm-up. HydroOpsLLM selects the operation dates and uses that saved inflow in
the daily reservoir loop. Changing the operator does not change this upstream
hydrological calculation.

Each agent requests controlled release. Reservoir physics applies available-water
and release limits, calculates spill and ending storage, and sends actual outflow
to downstream routing. The next decision uses the updated state.

## Choose the decision method

| Method | Agent settings | What makes the decision? |
|---|---|---|
| Rule-based | `type: rule_based`, `rule`, `rule_parameters` | Your registered rule module. Hanasaki is one supplied example. |
| LLM | `type: llm`, `model_profile`, `prompt_file` | The selected model receives your rendered prompt. |

An LLM extension can supply its own message format instead of `prompt_file`.
FE Walter uses this option to preserve the Anik case design. Its prompts and
seasonal rules remain in `examples/`; they are not defaults for other reservoirs.

## Use v2 and explicit study inputs

`experiment.yaml` holds the dates, output directory and references to the other
settings. A **profile** is a named group of settings, such as one provider/model
configuration. Each agent selects the profiles it needs. Sharing a profile does
not share reservoir state or history.

Use `hydroops-coupled-simulation.v2` for new experiments. Each relative path starts
from the file that contains it. The [configuration reference](PARAMETER_REFERENCE.md)
lists every supported field and default.

## Add advanced context and recovery later

Start with the required agent settings. Add a system prompt, fixed variables,
time-stamped [information](INFORMATION.md), or a retrieval callback only when your
study needs them. The framework does not add a shared system prompt.

Use [run and resume](RUNNING.md) for interrupted work and
[decision records](RECORDS.md) for provider attempts, audit and physical evidence.

## Troubleshooting

The [troubleshooting chapter](TROUBLESHOOTING.md) explains input errors, invalid
replies, operation-target misses and interrupted runs in one place.
