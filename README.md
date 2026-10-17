# HydroOpsLLM

[![User manual](docs/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroOpsLLM/)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM couples large language model decisions with HydroCNHS hydrological simulation for reservoir operations.

![HydroOpsLLM cover](docs/figures/hydroopslm-cover.png)

HydroCNHS computes streamflow. Each reservoir agent requests a release; the physical model implements it, updates storage and routes outflow downstream. The implemented result informs the next daily decision. In YAML, set each agent's `reservoir_id` and `type: rule_based` or `type: llm`.

## Installation

Use Python 3.12. Repository access is required while the project is private.

```sh
git clone https://github.com/WenyuChiou/HydroOpsLLM.git
cd HydroOpsLLM
```

Create and activate an environment:

```sh
# Linux / macOS
python3.12 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

```sh
python --version
python -m pip install -e . -c environment/requirements-bundled.txt
```

## Run a small example

This four-day synthetic example has two independent reservoirs and separate river outlets. It uses rule-based operation and needs no model or API key.

```sh
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule/operation --require-offline
```

`prepare` computes weather-derived inflow over the hydrological model's full initialization period. `run` then advances reservoir operations and downstream routing each day. Upstream runoff is currently prepared before the operation loop.

Follow [Build a simulation](docs/BUILD_SIMULATION.md) to set hydrology, reservoir parameters and agents. The [F.E. Walter case](examples/fe_walter/README.md) uses one physical case with three operation methods: Rule-based, LLM with available information, and LLM with retrieved knowledge.

## Configure an LLM

Each LLM agent selects `model_profile` and `prompt_file`, with optional knowledge or context under `customization`. No common system prompt is automatically added. Native interfaces support **OpenAI, Anthropic Claude, Google Gemini and Ollama**, with an additional OpenAI-compatible interface.

`check` previews configuration and prompts without calling a model. New LLM execution requires explicit `--allow-network`. See [Model configuration](docs/USER_GUIDE.md) for credentials, parameters, retry and fallback settings.

The [user manual](https://wenyuchiou.github.io/HydroOpsLLM/) explains input preparation, code structure, saved raw replies, audits and interrupted-run recovery. Notebooks and teaching results can be inspected without new inference.

## License and attribution

Project license: pending. HydroCNHS retains its [BSD 3-Clause license](licenses/HydroCNHS-BSD-3-Clause.txt). See [third-party notices](THIRD_PARTY_NOTICES.md) and [sources and citation](docs/REFERENCE.md).
