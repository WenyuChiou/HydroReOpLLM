# HydroOpsLM user manual

[English](index.md) | [繁體中文](index.zh-TW.md)

HydroOpsLM connects configurable reservoir decisions to the native HydroCNHS
Dam API. HydroCNHS supplies the hydrological model and river routing; HydroOpsLM
adds LLM prompts, response checks, reservoir calculations, and audit/trace records.

![HydroOpsLM concept](figures/hydrocnhs-coupling-framework-en.png)

Each reservoir selects one operation method. Blue shows water movement; black
shows information and decisions. Checks validate responses; an operating audit
reports whether configured rules are met. Its verdict is preserved in the trace.

## Start here

| Step | Read | What you will prepare |
|---|---|---|
| 1 | [Install](../README.md#install) | Python environment and model requirements |
| 2 | [FE Walter walkthrough](../examples/fe_walter/README.md) | Input, initial storage and three methods |
| 3 | [Module settings](USER_GUIDE.md) | YAML, reservoir agents, prompt and optional knowledge |
| 4 | [LLM decision flow](LLM_MODULES.md) | Info → prompt → proposal → checks → actual release → next-step info |
| 5 | [Inspect audit and trace](USER_GUIDE.md#troubleshooting) | Results, failed checks and reproducibility records |

## Three examples

| Method | Decision source | Example |
|---|---|---|
| Rule-based benchmark | Hanasaki-based flood-control rule | [Rule-based](../examples/fe_walter/benchmark/README.md) |
| Zero-shot | Prompt and available reservoir information | [Zero-shot](../examples/fe_walter/zero_shot/README.md) |
| DKP | The same LLM interface with operating knowledge | [DKP](../examples/fe_walter/dkp/README.md) |

## Tutorials and notebooks

Read the [single-reservoir tutorial](../tutorials/main.ipynb) or the
[multiple-reservoir tutorial](../tutorials/advanced.ipynb) in this site. Their
tables, figures and model replies use saved experiment records. Building the
site makes no model request.

- {download}`Download the main notebook <_notebook_downloads/main.ipynb>`
- {download}`Download the advanced notebook <_notebook_downloads/advanced.ipynb>`

## Native hydrology and citation

For watershed parameters, hydrological modeling and calibration/validation, use
the [HydroCNHS user manual](https://cylin928.github.io/HydroCNHS/) and
[native setup guidance](HYDROLOGY_SETUP.md). Cite the
[original HydroCNHS paper](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630)
separately from the HydroOpsLM extension.
