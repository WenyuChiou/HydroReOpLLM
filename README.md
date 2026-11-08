# HydroReOpLLM

[English](README.md) | [繁體中文](README.zh-TW.md)

[![User manual](docs/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)

![HydroReOpLLM: coupled human–water modeling with LLM reservoir decision agents](docs/figures/hydroopslm-cover.png)

HydroReOpLLM is a Python package for studying reservoir operations with large
language models (LLMs). It connects configurable reservoir operators to
[HydroCNHS](https://github.com/cylin928/HydroCNHS) hydrological simulations.
Use YAML files to describe your basin, a single reservoir or connected network,
and the information available to each operator.

Hydrology supplies inflow; operators request release; reservoir physics applies
physical limits, updates storage and spill, and routes total outflow downstream.
Each reservoir keeps its own state and decision history.

## What it provides

- **Single reservoirs and connected networks:** compare Rule-based and LLM
  operators while sharing hydrological inputs and reservoir physics.
- **Configurable model interfaces:** Ollama, OpenAI-compatible services, OpenAI,
  Anthropic and Gemini, with explicit model settings and retry/fallback choices.
- **Study-specific decisions:** supply your own system/user prompts, operational
  knowledge, observations and other information available at decision time.
- **Inspectable results:** save requested and actual release, spill, storage,
  downstream flow, reasons, raw replies, runtime and reported token usage.
  Configuration checks, response validation, water-balance verification and
  operating-rule audits address different parts of the experiment.

The main workflow is Daily. [Time-scale examples](examples/time_scales/README.md)
also demonstrate Hourly and explicit interval settings. A new basin still needs
appropriate input data, reservoir properties and hydrological calibration/validation.

## Install

Use **Python 3.12**. Clone the repository and create a virtual environment:

```bash
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in Windows PowerShell, or
`source .venv/bin/activate` on Linux/macOS. Then install from the repository root:

```bash
python -m pip install -e . -c environment/requirements-bundled.txt
reservoir-experiment --help
```

See [installation](https://wenyuchiou.github.io/HydroReOpLLM/docs/GETTING_STARTED.html)
for optional dependencies. Installation does not download or start an LLM.
This is a research candidate; installation from PyPI is not available.

## Run your first example

From the repository root, run the small single-reservoir example. Its supplied
inflows and deterministic operator require no API key or model service:

```bash
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single
```

Inspect `summary.json`, `reservoir_trajectory.csv` and `network_flows.csv` under
`runs/daily-single`. See [results and decision records](https://wenyuchiou.github.io/HydroReOpLLM/docs/RESULTS_GUIDE.html)
for the remaining logs. Use a new run name and output path for another experiment.

## Examples

| Example | What it demonstrates | Inputs and operators |
|---|---|---|
| [Single reservoir and cascade](examples/daily_offline/README.md) | A first run, then a three-reservoir chain | Small supplied inflows; no model service |
| [Multiple reservoirs](examples/multiple_reservoirs/README.md) | Weather-driven hydrology and independent reservoir operators | Rule-based default; an optional LLM configuration |
| [Time scales](examples/time_scales/README.md) | Daily, Hourly and explicit interval settings | Small configurations with non-LLM operators |
| [F.E. Walter](examples/fe_walter/README.md) | A worked research case with Rule-based and LLM methods | Choose prepared 2021–2025 inflows or the 2016 weather-driven setup in the [case guide](https://wenyuchiou.github.io/HydroReOpLLM/docs/CASE_STUDIES.html) |
| [F.E. Walter to Bethlehem](examples/fe_walter_bethlehem/README.md) | A separate downstream-stage preparation example | Historical ratings, station conventions and C&V requirements; simulation not yet available |

See the [example directory](examples/README.md) and [Notebook walkthroughs](tutorials/README.md).
`examples/` contains runnable studies and explicitly marked preparation examples;
`templates/` contains starting configurations.

## Configure your own study

The [user manual](https://wenyuchiou.github.io/HydroReOpLLM/) walks through
the settings in this order:

1. Set simulation dates, the run name and output directory.
2. Connect prepared inflows or your hydrological model and weather.
3. Define reservoir curves, initial states, outlet limits and river connections.
4. Choose each operator, model, prompt, available information and audit criteria.
5. Check, run and inspect the saved results.

Begin with the [configuration guide](https://wenyuchiou.github.io/HydroReOpLLM/docs/INPUT_OUTPUT.html)
and [coupled templates](templates/coupled/README.md). The weather-driven workflow
uses `check → prepare → run → verify`; prepared inflows use `check → run → verify`.
Case-specific rules, station names and knowledge stay in your study files or
extensions. Most study settings do not require changes to the core modules.

For code navigation, see the [project structure](docs/CODE_STRUCTURE.md) and
[API reference](https://wenyuchiou.github.io/HydroReOpLLM/docs/API_REFERENCE.html).
The package checks software and numerical consistency; the validity of a new
basin model or operating strategy requires its own evaluation.

## Citation and license

Record the project revision when reporting an experiment. Follow the
[citation guide](docs/REFERENCE.md), including the original HydroCNHS reference.
The main project license is pending; bundled dependencies retain their
[licenses and attribution](THIRD_PARTY_NOTICES.md).
