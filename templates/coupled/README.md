# Coupled simulation templates

Copy this whole folder for a new study. Start with `experiment.yaml`, then edit
the files in the order listed below. Values beginning with `YOUR_` are required
user inputs. The files are valid YAML before replacement, but `check` will reject
placeholder values that do not satisfy the runtime contract.

| File | Purpose |
|---|---|
| `experiment.yaml` | Global run identity, dates, output, and section references |
| `hydrology.yaml` | Native HydroCNHS model, forcing, and operation flow bindings |
| `reservoirs.yaml` | Reservoir physics and directed water network |
| `agents.rule.yaml` | Rule-based operator using a registered user rule |
| `agents.llm.yaml` | Alternate LLM operator |
| `models.yaml` | Model provider profiles used by LLM operators |
| `auditors.yaml` | Diagnostic checks selected by operators |
| `information.yaml` | Optional decision-time data catalog |
| `prompts/*.txt` | Explicit LLM system and operator messages |
| `extensions/user_registered_rule/__init__.py` | Minimal user rule package |

The default `experiment.yaml` selects `agents.rule.yaml`. After that path
checks, runs, and verifies, change the `agents.file` reference to `agents.llm.yaml` to
use the LLM operator. The commands are documented in
[`docs/RUNNING.md`](../../docs/RUNNING.md).
The starter contains `YOUR_` placeholders, so it is a copy-and-fill template;
it is not a runnable case until every placeholder is replaced with a real study
value or path. The rule-based branch is the default validation path and requires
no provider access. `information.yaml` is optional operator context; read the
[decision-time information guide](../../docs/INFORMATION.md) before binding its
profile to an agent.
If you already have prepared inflow series instead of a HydroCNHS model, use
[`../prepared/README.md`](../prepared/README.md).
