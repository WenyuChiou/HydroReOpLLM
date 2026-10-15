# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

[![Read the user manual](docs/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroOpsLM/)

![HydroOpsLM cover](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** connects configurable language-model reservoir operations to
[HydroCNHS](https://github.com/cylin928/HydroCNHS). Researchers choose the
information, prompts and operating checks for each reservoir. HydroCNHS provides
the hydrology and river routing; HydroOpsLM adds reservoir accounting and records
each proposal, audit and implemented release.

![HydroOpsLM concept](docs/figures/hydrocnhs-coupling-framework-en.png)

Blue arrows carry water; black arrows carry information and proposals. Each
reservoir uses one operation method through the native Dam API. HydroOpsLM adds
the common storage, release and spill calculations.

## Install

Use Python 3.12. From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

Follow [Installation](docs/GETTING_STARTED.md) to check the setup without inference.
The three-day LLM setup examples use local Ollama `gemma3:4b`, temperature **0.7**. Reading saved
results requires no model; the framework does not download or start one.

## FE Walter: one case, three methods

Start with [Build a simulation](docs/BUILD_SIMULATION.md), then follow
the [FE Walter case study](examples/fe_walter/README.md).

| Method | Decision source | Step-by-step guide |
|---|---|---|
| Rule-based benchmark | Published reservoir rules adapted to daily flood control | [Rule-based](examples/fe_walter/benchmark/README.md) |
| LLM with available information | Prompt and available reservoir information | [Available information](examples/fe_walter/zero_shot/README.md) |
| LLM with retrieved knowledge | Same interface with sourced operating knowledge | [Retrieved knowledge](examples/fe_walter/dkp/README.md) |

The case shares its physical setup across methods. Follow configuration, the operation method, execution and saved decisions.
The results chapter includes the full historical 2016–2020 retrieved-knowledge trajectory.

## Research and citation

Hydrological setup, catchment parameters and calibration/validation follow the
[original HydroCNHS manual](https://cylin928.github.io/HydroCNHS/).
Please credit its authors:

Lin, C. Y., Yang, Y. C. E., and Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 06022005.

[Method sources and citation](docs/REFERENCE.md) · [Technical Note draft](paper/technical_note.md)

## Project

[Repository](https://github.com/WenyuChiou/HydroOpsLM) ·
[Source and licensing](third_party/hydrocnhs/SOURCE.json)
