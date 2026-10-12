# HydroOpsLM FE Walter — zero-shot with local Ollama

[English](README.md) | [繁體中文](README.zh-TW.md) · [Three-method walkthrough](../README.md)

Zero-shot uses the HydroOpsLM LLM interface with the operating prompt and current
reservoir information. It does not retrieve DKP excerpts. “Shallow” refers to this
context design; it is not a performance or quality claim.

## Workflow

1. Inspect the bounded Ollama [case](../../../cases/fe_walter_ollama_demo/case.json) and
   [daily inflow](../../../cases/fe_walter_reference/inflows.csv).
2. Open [experiment.ollama.yaml](experiment.ollama.yaml). It configures local
   Ollama `gemma3:4b`, temperature `0.7`, daily 2016-01-01 through 2016-01-03,
   three requests and no retries.
3. Review the [system prompt](../../../prompts/fe_walter_reference/zeroshot_system.txt)
   and [reading preview](prompt_preview.txt). Runtime information and history are
   assembled for each day; editing the preview does not change execution.
4. Run the local check, simulation and verification below.
5. Inspect the actual saved decision trace.

Before running commands, note two bounded integration assumptions: initial storage
is **1,992.61 acre-ft**, and the downstream `UH=[1.0]` is identity routing. Neither
is field validation or strategy acceptance. The Ollama case is an explicit
diagnostic; it does not change the original case readiness from `false`.

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.ollama.yaml --allow-network
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
```

`check` performs no inference or provider request. `run --allow-network` explicitly
permits the configured request to local Ollama. Because this is an actual model
run, `verify` and the inspector omit `--require-offline`.

Inspect `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`,
`audit.jsonl` and `raw/`. The trace links daily information and full prompts to the
model reply, normalized requested release, checker result, implemented release,
storage, routed flow and strategy audit. A parsed action, a passing audit and a
physically feasible release are separate findings.

The synthetic [offline YAML](experiment.hydroopslm.offline.yaml), saved response
fixtures and lessons 04/05 remain developer-validation assets. They are not the
default user path and cannot measure real model behavior.

[Ollama notebook](../../../tutorials/08_ollama_workflow.ipynb) ·
[Formal module guide](../../../docs/LLM_MODULES.md)
