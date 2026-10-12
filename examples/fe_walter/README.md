# FE Walter with HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md) · [All examples](../README.md)

This walkthrough sends the same three-day FE Walter inflow through native
HydroCNHS Dam coupling and downstream routing, with HydroOpsLM's added shared
reservoir physics and audit/trace. Only the decision method changes.

| Method | Decision context | Configuration |
|---|---|---|
| [Rule-based](benchmark/README.md) | A custom Hanasaki-style rule called through the native Dam API | [offline YAML](benchmark/experiment.hydroopslm.offline.yaml) |
| [Zero-shot](zero_shot/README.md) | The LLM receives the prompt and current information | [Ollama YAML](zero_shot/experiment.ollama.yaml) |
| [DKP](dkp/README.md) | The same LLM interface plus conditionally retrieved decision knowledge | [Ollama YAML](dkp/experiment.ollama.yaml) |

The Hanasaki-style policy is custom example logic; it is not a built-in
HydroCNHS rule or reservoir-physics model. “Shallow” zero-shot and “deep” DKP
describe how much context is assembled for the model. They do not rank accuracy,
safety or operating performance.

## Step by step

1. **Input:** inspect the frozen [inflow CSV](../../cases/fe_walter_reference/inflows.csv),
   the [benchmark case](../../cases/fe_walter_reference/case.json), and the
   [bounded Ollama case](../../cases/fe_walter_ollama_demo/case.json).
2. **YAML:** choose one configuration from the table. The two LLM examples use
   local Ollama `gemma3:4b`, temperature `0.7`, daily 2016-01-01 through
   2016-01-03, three requests and no retries.
3. **Rules or prompt:** read the chosen method page. Zero-shot uses prompt plus
   current information; DKP adds conditional knowledge retrieval.
4. **Check:** run `check` on the YAML. This validates locally and performs no
   inference or provider request.
5. **Run:** the rule-based example stays offline. For either local Ollama YAML,
   explicitly add `--allow-network`; the flag permits the configured local
   provider request.
6. **Verify:** verify the configured output. Ollama outputs are verified without
   `--require-offline`.
7. **Audit trace:** use `tutorials/inspect_decision_flow.py` to inspect information,
   prompts, reply, proposal, physical outcome and audit evidence from the actual run.

Before any commands, treat initial storage **1,992.61 acre-ft** and downstream
`UH=[1.0]` identity routing as bounded integration assumptions. They are not
field validation or acceptance of any operating strategy. The new Ollama case is
an explicit diagnostic; the original case readiness remains `false`.

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.ollama.yaml --allow-network
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
```

Follow the method pages for the benchmark and DKP commands. Existing outputs are
not overwritten; choose a new `run_id` and output path for a repeat. The saved
trace distinguishes checker validity, strategy audit and physical feasibility.

[Ollama notebook](../../tutorials/08_ollama_workflow.ipynb) ·
[Formal settings](../../docs/USER_GUIDE.md) ·
[Native hydrology setup](../../docs/HYDROLOGY_SETUP.md)

[Saved local Ollama diagnostic and audit results](../../results/fe_walter_ollama_2016_01/README.md)
