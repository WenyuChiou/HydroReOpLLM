# HydroOpsLLM tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Start with the [F.E. Walter configuration walkthrough](fe_walter.md) and
[main notebook](main.ipynb). Both follow the current 366-day 2016 example:
**Rule-based**, **LLM with available information**, and **LLM with retrieved
knowledge**. Choose the method's experiment in
[`coupled/current/`](../examples/fe_walter/coupled/current/) and configure the
model inside [`models.yaml`](../examples/fe_walter/coupled/current/models.yaml).

The notebooks read committed evidence and save table and figure outputs for
GitHub and MyST-NB. Their default path makes no model request, network request,
download, recalibration or new simulation.

| Notebook | Purpose | Saved evidence |
|---|---|---|
| [Main walkthrough](main.ipynb) | Shared inputs → experiment and model settings → actual prompts/replies → annual trajectories → outcomes | Annual Rule-based baseline and current Gemma 4 comparison, including independent Anik runs |
| [Advanced workflow](advanced.ipynb) | Topology, passive outlets, state isolation, routing limits and own-data settings | Accepted 31-day, three-reservoir snapshot |

The main example assumes initial storage **2,457,848.279729185 m³
(1,992.61 acre-ft)**, zero reservoir losses and downstream `UH=[1.0]` identity
routing. Each current LLM arm completed 366 days with 366 recorded HTTP attempts.
Completion and water balance do not establish acceptable operation; inspect the
seasonal checks in the [current annual results](../examples/fe_walter/coupled/README.md#verified-2016-results).

## Build and check

From the repository root, use the project environment with pandas and
matplotlib installed:

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
```

The builder executes ordered cells without a Jupyter kernel, blocks socket and
urllib access, and embeds pandas HTML plus matplotlib PNG output. It reads the
committed `coupled/outputs/gemma4_2016_comparison` export, the Rule-based rows of
`coupled/outputs/2016`, and `reference_outputs/multi_reservoir_month` under
`examples/fe_walter/`; it does not depend on ignored `runs/` directories.
Earlier short teaching snapshots remain preserved in `reference_outputs/`.

## Optional new execution

The notebook documents this path without executing it. Use a new `run_id` and
output path, keep an experiment copy beside its source and review
`current/models.yaml`. The current LLM entries have no total call cap and allow
at most two attempts for each daily decision. `--allow-network` is explicit.

```powershell
Copy-Item examples/fe_walter/coupled/current/llm_available.yaml examples/fe_walter/coupled/current/my-run.yaml
# Edit my-run.yaml: choose a new run_id and output before continuing.
reservoir-experiment check examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment prepare examples/fe_walter/coupled/current/my-run.yaml
reservoir-experiment run examples/fe_walter/coupled/current/my-run.yaml --allow-network
reservoir-experiment verify <new-output-path>/operation
```

[FE Walter example guide](../examples/fe_walter/README.md) ·
[Generic YAML/module manual](../docs/USER_GUIDE.md) ·
[Native HydroCNHS hydrology and C&V](../docs/HYDROLOGY_SETUP.md)
