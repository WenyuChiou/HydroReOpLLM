# FE Walter with HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md) · [All examples](../README.md)

This single-reservoir example demonstrates a rule-based benchmark and two LLM
information designs: available information and retrieved knowledge. All three use the same three-day F.E. Walter
input, physical case, zero-loss assumption, and `UH=[1.0]` routing. They illustrate
how to use HydroOpsLM; these saved diagnostic runs do not establish policy performance.

| Example | Complete configuration | Decision evidence | Saved result |
|---|---|---|---|
| [Rule-based benchmark](benchmark/README.md) | [`tutorials/config/fe_walter_tutorial_benchmark.yaml`](../../tutorials/config/fe_walter_tutorial_benchmark.yaml) | Daily rule; no model call | [3 PASS; acceptance `null`](../../results/fe_walter_tutorial_benchmark_2016_01/) |
| [LLM operation with available information](zero_shot/README.md) | [`zero_shot/experiment.ollama.yaml`](zero_shot/experiment.ollama.yaml) | Saved prompt and full Ollama reply | [2 PASS / 1 FAIL; acceptance `null`](../../results/fe_walter_ollama_2016_01/zero_shot/) |
| [LLM operation with retrieved knowledge](dkp/README.md) | [`dkp/experiment.ollama.yaml`](dkp/experiment.ollama.yaml) | Saved prompt, retrieved sources and full Ollama reply | [3 FAIL; acceptance `null`](../../results/fe_walter_ollama_2016_01/dkp/) |

Each guide follows **input → YAML → prompt or rule → check → run → verify →
audit/trace**. The guides read existing results first and show how to configure
a separate run without overwriting them.

First follow [one complete decision](../../docs/FIRST_DECISION.md). After the
request, implemented release, spill, storage and audits are defined, the
[results chapter](../../docs/RESULTS_GUIDE.md) explains the three-day figure.
The [main notebook](../../tutorials/main.ipynb) preserves the full saved prompts,
replies, tables and plot as a companion artifact.

Initial storage **2,457,848.279729185 m³ (1,992.61 acre-ft)** is an integration
assumption rather than an observed 2016 state. Identity routing is not calibrated.
The saved model used `gemma3:4b`, temperature 0.7, three calls per method, and no
retry. The available-information method retained 2 PASS / 1 FAIL audits; the
retrieved-knowledge method retained 3 FAIL; strategy
acceptance is `null`.

## Rule-based benchmark

The benchmark follows [Hanasaki et al. (2006)](https://doi.org/10.1016/j.jhydrol.2005.11.011)
and the flood-control formulation in [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/),
adapted to daily steps. The [sources and adaptation](benchmark/README.md#sources-and-adaptation)
identify the pinned implementation.

The [three-day benchmark YAML](../../tutorials/config/fe_walter_tutorial_benchmark.yaml)
selects the Hanasaki-based flood-control policy with frozen 1996–2015 statistics.
It uses the same case and common simulation driver as the two LLM methods.
No model request is needed. The [benchmark specification](benchmark/README.md)
describes the equations and differential tests.

The three individual guides provide verification commands. The site directly
embeds saved notebook outputs and preserves the original notebook downloads.

For an optional local rerun, copy an Ollama YAML beside the original and edit
its `run_id` and `output` to new values. Run `check` on the copy, then explicitly
run it with `--allow-network`.
Existing outputs must not be overwritten.

## Continue

Adapt [simulation settings](../../docs/USER_GUIDE.md) after completing one example.
The [advanced notebook](../../tutorials/advanced.ipynb) then adds multiple
reservoirs and reads the accepted 31-day network evidence. See
[results and troubleshooting](../../docs/RESULTS_GUIDE.md) for audit and trace.

[Generic settings](../../docs/USER_GUIDE.md) ·
[Native hydrology and C&V](../../docs/HYDROLOGY_SETUP.md) ·
[Saved Ollama provenance](../../results/fe_walter_ollama_2016_01/README.md)
