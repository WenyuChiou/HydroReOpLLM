# Global settings

The experiment file is the entry point for one coupled run. It names the run,
sets the inclusive operation dates, chooses an unused output directory, and
points to each complete configuration section.

Download [experiment.yaml](../templates/coupled/experiment.yaml) or browse the
[template file list](TEMPLATES.md).

```{literalinclude} ../templates/coupled/experiment.yaml
:language: yaml
```

| Field | Purpose and units | Required? | User-filled or referenced value |
|---|---|---|---|
| `schema_version` | Selects the public split-file loader format | Required | Keep `hydroops-coupled-simulation.v2` |
| `run_id` | Stable label written into provenance | Required | Replace `YOUR_RUN_ID` |
| `output` | Destination directory | Required | Replace with an unused path |
| `case` | Physical reservoir/network document | Required | Path to `reservoirs.yaml` or equivalent |
| `start_date`, `end_date` | First and last operation day, inclusive | Required | Quoted `YYYY-MM-DD` inside the hydrology period |
| `max_calls` | Total provider-attempt ceiling, including retries | Optional | Nonnegative integer or `null`; zero permits no provider attempts |
| `hydrology.file` | Complete hydrology section | Required | Path relative to `experiment.yaml` |
| `agents.file` | Complete operator section | Required | Select the Rule-based or LLM file |
| `models.file` | Shared model profiles | Required for the template | Used only by LLM operators |
| `information.file` | Optional decision information catalog | Optional | Remove when no agent uses information |
| `auditors.file` | Diagnostic check catalog | Optional | IDs are selected in agent files |
| `extensions` | IDs mapped to trusted Python package entry files | Required for the included user rule | Paths must end at package `__init__.py` |

The loader resolves each relative resource from the file that declares it and
pins the bytes used by a validated run. A section file reference must contain
only `file`; place all section values in the referenced file.
