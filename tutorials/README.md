# HydroOpsLLM tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Start with the English [F.E. Walter configuration tutorial](fe_walter.md) for
the current split weather-to-operation entry, model settings and daily decision
contract. It is the single maintained source for that walkthrough.

Use the [latest 2016 Gemma 4 results](../examples/fe_walter/coupled/README.md#verified-2016-results)
as the main annual example. The companion notebooks below preserve older,
shorter teaching snapshots.

The two companion English notebooks execute from tracked, accepted
snapshots and save rich table and figure outputs for GitHub and MyST-NB. Their
default path makes no model, network, download, recalibration, or new simulation
call.

| Notebook | Purpose | Saved evidence |
|---|---|---|
| [Main walkthrough](main.ipynb) | Input → YAML → rule/prompt → check → saved run → verify → audit/trace | Same three-day FE Walter case for deterministic rule, zero-shot, and DKP |
| [Advanced workflow](advanced.ipynb) | Topology, passive outlets, state isolation, routing limits, and own-data settings | Accepted 31-day, three-reservoir snapshot |

The main comparison uses initial storage **2,457,848.279729185 m³
(1,992.61 acre-ft)**, zero losses, and downstream `UH=[1.0]` identity routing.
These are bounded integration assumptions. Saved zero-shot audit results are
2 PASS / 1 FAIL; saved DKP results are 3 FAIL; strategy acceptance remains
`null` for all methods.

## Build and check

From the repository root, use the project environment with pandas and
matplotlib installed:

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
```

The builder executes ordered cells without a Jupyter kernel, blocks socket and
urllib access, and embeds pandas HTML plus matplotlib PNG output. It reads
`examples/fe_walter/reference_outputs/ollama_three_day`,
`examples/fe_walter/reference_outputs/rule_three_day`, and
`examples/fe_walter/reference_outputs/multi_reservoir_month`; it has no dependency on ignored `runs/`.

## Optional local Ollama rerun

The notebooks only document this path. With the named model already available locally,
choose a new `run_id` and output path. The supplied YAMLs are bounded to three
calls and no retry. `--allow-network` must be explicit.

```powershell
Copy-Item examples/fe_walter/zero_shot/experiment.ollama.yaml examples/fe_walter/zero_shot/my-run.yaml
# Edit my-run.yaml: choose a new run_id and output before continuing.
python run_experiment.py check examples/fe_walter/zero_shot/my-run.yaml
python run_experiment.py run examples/fe_walter/zero_shot/my-run.yaml --allow-network
```

[FE Walter example guide](../examples/fe_walter/README.md) ·
[Generic YAML/module manual](../docs/USER_GUIDE.md) ·
[Native HydroCNHS hydrology and C&V](../docs/HYDROLOGY_SETUP.md)
