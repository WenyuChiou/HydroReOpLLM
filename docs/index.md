# HydroOpsLM User Manual

HydroOpsLM connects reservoir operating decisions to HydroCNHS hydrology and
river routing. Configure the information, prompt and checks for each reservoir;
inspect how a proposal becomes an implemented release.

![HydroOpsLM concept](figures/hydrocnhs-coupling-framework-en.png)

[View the concept at full size](https://wenyuchiou.github.io/LLM_reservoir_agent/_images/hydrocnhs-coupling-framework-en.png).

Blue arrows carry water; black arrows carry information and proposals. Both
operation methods use the native Dam API. HydroOpsLM adds common storage,
release and spill calculations. A response check and an operation audit answer
different questions; their records remain separate.

## Start here

[Install HydroOpsLM](GETTING_STARTED.md), then follow
[your first reservoir decision](FIRST_DECISION.md). This walkthrough opens a
saved real Ollama reply and follows it through checks, audit, actual release and
the next day's information. Reading this manual makes no model request.

## Three worked examples

Use the same FE Walter input and initial conditions to learn each method.
The [case overview](../examples/fe_walter/README.md) explains the common setup.

::: {container} method-list

### [Rule-based benchmark](../examples/fe_walter/benchmark/README.md)

Published reservoir rules adapted to daily flood control.

### [LLM with available information](../examples/fe_walter/zero_shot/README.md)

An independent prompt, reservoir information and a local model.

### [LLM with retrieved knowledge](../examples/fe_walter/dkp/README.md)

The same decision interface with sourced operating knowledge.

:::

Each guide follows **input → YAML → prompt/rule → check → run → verify → results**.
The three-day records demonstrate integration, not policy superiority.

## Build your own experiment

Continue with [inputs and YAML](USER_GUIDE.md), [decision information](INFORMATION.md)
and [prompts and modules](LLM_MODULES.md). Then read
[multiple reservoirs](../tutorials/advanced.ipynb),
[results and audit/trace](RESULTS_GUIDE.md), and
[running and maintenance](RUNNING.md).

## Notebooks and sources

{download}`Main notebook <_notebook_downloads/main.ipynb>` ·
{download}`Advanced notebook <_notebook_downloads/advanced.ipynb>`

These are the original notebooks with saved outputs.
For catchment setup, hydrological parameters and calibration/validation, use the
[HydroCNHS manual](https://cylin928.github.io/HydroCNHS/).
See [sources and citation](REFERENCE.md) for the framework and benchmark.

[繁體中文](index.zh-TW.md) ·
[Repository](https://github.com/WenyuChiou/LLM_reservoir_agent)
