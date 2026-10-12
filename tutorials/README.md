# HydroOpsLM tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Install from the [framework README](../README.md). The lessons follow the same
path from information and configuration to decisions, physics and saved evidence.
Runtime prompts retain their original English text.

| Order | Notebook | Focus |
|---|---|---|
| 00 | [LLM architecture](00_overview.ipynb) | Information → prompt → proposal → checker → execution → feedback |
| 01 | [Input and map](01_input_and_map.ipynb) | Inflow, units, initial state and GIS |
| 02 | [Agent settings](02_yaml.ipynb) | YAML, model, prompt, knowledge and auditors |
| 03 | [Rule benchmark](03_benchmark.ipynb) | Custom rule through native Dam coupling |
| 04 | [Zero-shot fixture](04_zero_shot.ipynb) | Synthetic response and decision chain |
| 05 | [DKP fixture](05_dkp.ipynb) | Synthetic response with knowledge retrieval |
| 06 | [Audit and trace](06_audit_trace.ipynb) | Verdicts, bound physics and next-day information |
| 07 | [Multiple reservoirs / own data](07_multi_and_custom.ipynb) | Topology, state isolation and passive outlets |
| 08 | [Local Ollama workflow](08_ollama_workflow.ipynb) | Check, run, verify and inspect an actual local model run |

## Local Ollama walkthrough

Install Ollama and make `gemma3:4b` available locally. The zero-shot and DKP
configurations use temperature `0.7`, daily 2016-01-01 through 2016-01-03,
three requests each and no retries.

Before commands, treat initial storage **1,992.61 acre-ft** and downstream
`UH=[1.0]` identity routing as bounded integration assumptions. They are not
field validation or strategy acceptance. The Ollama case is an explicit
diagnostic; original case readiness remains `false`.

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.ollama.yaml --allow-network
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
```

For DKP, substitute `dkp` in the YAML and use output
`runs/hydroopslm-fe-walter-dkp-ollama-gemma3-4b-20261012`. `check` makes no
inference or provider request. `run --allow-network` explicitly permits the local
Ollama request. `verify` and the inspector omit `--require-offline` because they
read an actual model run.

The inspector shows information, full prompts, model reply, normalized proposal,
checker result, committed physics, next-day information, audit and trace paths.
For DKP it also shows the conditionally retrieved knowledge. Checker validity,
strategy audit and physical feasibility remain separate outcomes.

## Developer validation fixtures

Lessons 04/05, the `experiment.hydroopslm.offline.yaml` files and saved response
fixtures remain available for deterministic developer checks. They are not the
default user path and cannot assess model quality. Run the existing offline
notebook suite with:

```powershell
python tutorials/build_notebooks.py --execute
```

For native runoff, parameters, routing, calibration and validation, combine the
local [hydrology setup](../docs/HYDROLOGY_SETUP.md) with the
[official HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/).

[Formal settings](../docs/USER_GUIDE.md) · [FE Walter walkthrough](../examples/fe_walter/README.md)
