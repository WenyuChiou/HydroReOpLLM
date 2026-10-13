# FE Walter with HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md) · [All examples](../README.md)

This single-reservoir example demonstrates a rule-based benchmark and two LLM
information designs: zero-shot and DKP. All three use the same three-day FE Walter
input, physical case, zero-loss assumption, and `UH=[1.0]` routing. They illustrate
how to use HydroOpsLM; these saved diagnostic runs do not establish policy performance.

| Method | Decision source | Default tutorial evidence |
|---|---|---|
| Rule | Hanasaki-based flood-control rule with frozen 1996–2015 statistics | [Tracked deterministic snapshot](../../results/fe_walter_tutorial_benchmark_2016_01/) |
| Zero-shot | Saved local Ollama prompt and reply | [Tracked zero-shot snapshot](../../results/fe_walter_ollama_2016_01/zero_shot/) |
| DKP | Saved local Ollama prompt, retrieved knowledge, and reply | [Tracked DKP snapshot](../../results/fe_walter_ollama_2016_01/dkp/) |

Start with the [main notebook](../../tutorials/main.ipynb). It shows the input
with units, complete saved prompts, rule/model outputs, current contract recheck,
implemented release, next information, audit verdicts, and a three-method plot.
The [advanced notebook](../../tutorials/advanced.ipynb) reads the accepted
31-day, three-reservoir evidence.

Initial storage **2,457,848.279729185 m³ (1,992.61 acre-ft)** is an integration
assumption rather than an observed 2016 state. Identity routing is not calibrated.
The saved model used `gemma3:4b`, temperature 0.7, three calls per method, and no
retry. Zero-shot retained 2 PASS / 1 FAIL audits; DKP retained 3 FAIL; strategy
acceptance is `null`.

## Rule-based benchmark

The [three-day benchmark YAML](../../tutorials/config/fe_walter_tutorial_benchmark.yaml)
selects the Hanasaki-based flood-control policy with frozen 1996–2015 statistics.
It uses the same case and common simulation driver as the two LLM methods.
No model request is needed. The [benchmark specification](benchmark/README.md)
describes the equations and differential tests.

Build and validate the saved-evidence notebooks without a provider call:

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
python run_experiment.py verify results/fe_walter_tutorial_benchmark_2016_01 --require-offline
```

For an optional local rerun, copy an Ollama YAML beside the original and edit
its `run_id` and `output` to new values. Run `check` on the copy, then explicitly
run it with `--allow-network`.
Existing outputs must not be overwritten.

[Generic settings](../../docs/USER_GUIDE.md) ·
[Native hydrology and C&V](../../docs/HYDROLOGY_SETUP.md) ·
[Saved Ollama provenance](../../results/fe_walter_ollama_2016_01/README.md)
