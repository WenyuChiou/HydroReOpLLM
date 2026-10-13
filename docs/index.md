# HydroOpsLM

[English](index.md) | [繁體中文](index.zh-TW.md)

HydroOpsLM provides a configurable environment for studying LLM reservoir
operations in coupled hydrological simulations. It extends HydroCNHS through
the Dam API while retaining the original hydrological models and river routing.

![HydroOpsLM concept](figures/hydrocnhs-coupling-framework-en.png)

Each reservoir selects one operation method. HydroCNHS supplies hydrology and
routing; HydroOpsLM adds decisions, shared reservoir calculations, response checks
and audit/trace records. Blue arrows show water movement; black arrows show
information and decisions.

## Start with one reservoir

Begin with [Getting started](GETTING_STARTED.md), then choose one of the three
FE Walter examples below. Each follows the same sequence:
**input → YAML → prompt or rule → check → run → verify → audit/trace**.

## Three examples

::::{container} example-links

| ![Rule-based benchmark](_static/icons/rule.png) | ![Zero-shot](_static/icons/language-model.png) | ![DKP](_static/icons/prompt.png) |
|---|---|---|
| **[1. Rule-based benchmark](../examples/fe_walter/benchmark/README.md)** | **[2. Zero-shot](../examples/fe_walter/zero_shot/README.md)** | **[3. DKP](../examples/fe_walter/dkp/README.md)** |
| Hanasaki-based flood-control rule | Prompt + available information | Prompt + retrieved operating knowledge |

::::

The benchmark uses a daily adaptation of the flood-control formulation described
by [Abeshu et al. (2023), Section 2.3.3](https://gmd.copernicus.org/articles/16/5449/2023/).
Its [sources and adaptation](../examples/fe_walter/benchmark/README.md#sources-and-adaptation)
identify Hanasaki et al. (2006) and the pinned implementation.

## Follow a decision, then read the result

The [main tutorial](../tutorials/main.ipynb) shows the first day's information,
rendered prompt, complete model reply, response checks, actual release and
next-day history. Its tables and figures use saved experiment records.

![Three-day FE Walter results](../tutorials/assets/fe_walter_three_method.png)

These three-day trajectories share inflow and initial conditions. They illustrate
implemented outflow and storage; they do not establish policy performance.
Operating-audit verdicts remain visible in the tutorial.

- {download}`Download the main notebook <_notebook_downloads/main.ipynb>`

Use [Simulation settings](USER_GUIDE.md) to change inputs and agents,
[LLM decision workflow](LLM_MODULES.md) to follow the information exchange, and
[Results, audit and troubleshooting](RESULTS_GUIDE.md) to inspect a run.

## Extend to a river network

The [multiple-reservoir tutorial](../tutorials/advanced.ipynb) adds controlled
reservoirs, passive outlets and routing. Each controlled reservoir has its own
decision history; the river network determines downstream effects.

- {download}`Download the advanced notebook <_notebook_downloads/advanced.ipynb>`

See [Reference and citation](REFERENCE.md) for detailed settings, method sources
and reproducibility guidance.

For watershed parameters, hydrological modeling and calibration/validation,
continue with the [original HydroCNHS documentation](https://cylin928.github.io/HydroCNHS/).
