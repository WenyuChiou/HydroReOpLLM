# FE Walter with HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md) · [All examples](../README.md)

This single-reservoir example demonstrates a rule-based benchmark and two LLM
information designs: zero-shot and DKP. All three use the same three-day FE Walter
input, physical case, zero-loss assumption, and `UH=[1.0]` routing. They illustrate
how to use HydroOpsLM; these saved diagnostic runs do not establish policy performance.

| Example | Decision source | Step-by-step guide | Saved evidence |
|---|---|---|---|
| Rule-based benchmark | Flood-control rule with frozen 1996–2015 statistics | [Rule-based](benchmark/README.md) | [Deterministic snapshot](../../results/fe_walter_tutorial_benchmark_2016_01/) |
| Zero-shot | Local Ollama prompt and reply | [Zero-shot](zero_shot/README.md) | [Zero-shot snapshot](../../results/fe_walter_ollama_2016_01/zero_shot/) |
| DKP | The same LLM interface with retrieved operating knowledge | [DKP](dkp/README.md) | [DKP snapshot](../../results/fe_walter_ollama_2016_01/dkp/) |

Each guide follows **input → YAML → prompt or rule → check → run → verify →
audit/trace**. The guides read existing results first and show how to configure
a separate run without overwriting them.

Open the [main notebook](../../tutorials/main.ipynb) for the full comparison. It shows the input
with units, complete saved prompts, rule/model outputs, current contract recheck,
implemented release, next information, audit verdicts, and a three-method plot.

![Three-day FE Walter results](../../tutorials/assets/fe_walter_three_method.png)

Implemented outflow and storage under shared demonstration conditions. These
short trajectories illustrate integration, not operational-policy performance.

Initial storage **2,457,848.279729185 m³ (1,992.61 acre-ft)** is an integration
assumption rather than an observed 2016 state. Identity routing is not calibrated.
The saved model used `gemma3:4b`, temperature 0.7, three calls per method, and no
retry. Zero-shot retained 2 PASS / 1 FAIL audits; DKP retained 3 FAIL; strategy
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
