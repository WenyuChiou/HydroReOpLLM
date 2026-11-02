# Configuration files

One experiment file connects the settings for your study. Start with
[the configuration template](../templates/coupled/experiment.yaml), then follow
the chapters from global settings to individual reservoir operators.

## Input layers

| Configure in this order | File | What you set |
|---|---|---|
| [Global settings](GLOBAL_SETTINGS.md) | `experiment.yaml` | Dates, run name, output and references to the other files. |
| [Hydrology](HYDROLOGY_SETUP.md) | `hydrology.yaml` | The hydrological model, weather and inflow connections. |
| [Reservoirs and network](BUILD_SIMULATION.md) | `reservoirs.yaml` | Storage, release limits and water connections. |
| [Operators and prompts](CONFIGURATION.md) | `agents.rule.yaml` or `agents.llm.yaml` | The operator for each reservoir and its prompt. |
| [Models](MODEL_PROVIDERS.md) | `models.yaml` | Provider, model and request options for LLM operators. |
| [Available information](INFORMATION.md) | `information.yaml` and local knowledge files | Observations, forecasts or operational knowledge available to each operator. |

`auditors.yaml` selects operation checks. `extensions/` holds optional custom
rules, response parsers or information sources. Keep study-specific code there
rather than editing the core package.

## The experiment file

The example below points to separate files. A **key**, such as `run_id`, is a
setting within the file; a **path**, such as `hydrology.yaml`, locates another file.

```{literalinclude} ../templates/coupled/experiment.yaml
:language: yaml
```

Paths are relative to the file that declares them. For example,
`agents: {file: agents.rule.yaml}` loads that complete section from
`agents.rule.yaml`; it does not combine it with another inline agents section.

The [template file list](TEMPLATES.md) provides all starting files together.

## From settings to results

![Check configuration, prepare inflow, run reservoir operations and verify records](figures/simulation-stages.svg)

*Configuration files connect the hydrology preparation, reservoir operation and saved results.*

The hydrology stage calculates and saves inflow. Reservoir operation then uses
that inflow to update storage, release and downstream flow. Changing an operator
does not rerun upstream hydrology.

Continue to [global settings](GLOBAL_SETTINGS.md). After configuring each layer,
follow [Run the simulation](RUNNING.md) and [Read the results](RESULTS_GUIDE.md).
Python functions and full field details are in the [API](API_REFERENCE.md) and
[configuration reference](PARAMETER_REFERENCE.md).
