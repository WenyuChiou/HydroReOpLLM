<img src="docs/figures/assets/branding/hydroopslm-logo.png" align="right" width="64" height="64" alt="HydroOpsLM logo">

# HydroOpsLM

**Hydrological Simulation with Large Language Model Reservoir Operations**

[English](README.md) | [繁體中文](README.zh-TW.md)

[![Read the user manual](docs/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroOpsLM/)

![HydroOpsLM cover](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** is a framework for large language model (LLM) reservoir operations coupled
with [HydroCNHS](https://github.com/cylin928/HydroCNHS). Configure each reservoir's
decision information, prompt, operation method and checks. HydroCNHS provides
hydrology and river routing; HydroOpsLM adds reservoir accounting and links
proposals, audits and implemented releases.

![HydroOpsLM concept](docs/figures/hydrocnhs-coupling-framework-en.png)

## Install

Use Python 3.12. Clone the repository, create a virtual environment, then install:

```powershell
git clone https://github.com/WenyuChiou/HydroOpsLM.git
cd HydroOpsLM
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

The [User Manual](https://wenyuchiou.github.io/HydroOpsLM/) covers installation on
other platforms, case setup, operation methods, examples, audit/trace and references.
