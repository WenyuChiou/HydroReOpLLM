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
checks and verifies, change the `agents.file` reference to `agents.llm.yaml` to
use the LLM operator. The commands are documented in `docs/RUNNING.md`.
