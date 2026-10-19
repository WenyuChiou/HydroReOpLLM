# Template index

The canonical files under `templates/coupled/` are the single source for the
configuration shown in this guide. Copy the whole folder, then replace every
`YOUR_` value with a study input. Comments explain optional fields and paths.

{download}`Download the complete template bundle <../_template_downloads/coupled-configuration.zip>`

The archive preserves the folder structure. Unpack it before editing paths;
the native hydrology model and forcing are external inputs you must supply.

| Download | Edit when |
|---|---|
| [experiment.yaml](../templates/coupled/experiment.yaml) | Starting every study |
| [hydrology.yaml](../templates/coupled/hydrology.yaml) | Connecting the accepted native model and forcing |
| [reservoirs.yaml](../templates/coupled/reservoirs.yaml) | Defining physical values and the water network |
| [agents.rule.yaml](../templates/coupled/agents.rule.yaml) | Starting with a Rule-based operator |
| [agents.llm.yaml](../templates/coupled/agents.llm.yaml) | Switching a verified setup to an LLM |
| [models.yaml](../templates/coupled/models.yaml) | Selecting a provider and model |
| [auditors.yaml](../templates/coupled/auditors.yaml) | Enabling diagnostic checks |
| [information.yaml](../templates/coupled/information.yaml) | Supplying optional decision-time data |
| [system.txt](../templates/coupled/prompts/system.txt) | Adding an explicit system message |
| [operator.txt](../templates/coupled/prompts/operator.txt) | Defining the LLM task and placeholders |
| [user rule](../templates/coupled/extensions/user_registered_rule/__init__.py) | Replacing or extending the minimal Rule-based controller |

The template YAML parses before replacement so editors can lint it. Runtime
validation deliberately rejects unresolved physical and date placeholders.
