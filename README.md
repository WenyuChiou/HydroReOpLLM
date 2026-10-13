# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

![HydroOpsLM cover](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** is a Python framework for studying language-model reservoir
decisions inside coupled hydrological simulations. It connects configurable
decision methods to the existing Dam API in
[HydroCNHS](https://github.com/cylin928/HydroCNHS), which remains the native
hydrology, routing, parameter, calibration and validation foundation.

![HydroCNHS coupling framework with HydroOpsLM](docs/figures/hydrocnhs-coupling-framework-en.png)

Each reservoir selects one decision method through HydroCNHS's Dam API.
HydroOpsLM adds common storage, release and spill calculations. Response checks
and operating-rule audits are separate; diagnostic runs retain failed audits.

## Install

Use Python 3.12 and a complete checkout:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

For the local LLM walkthrough, also install
[Ollama](https://ollama.com/) and make `gemma3:4b` available locally. The
repository does not download or start the model for you.

## Examples

Start with the [FE Walter walkthrough](examples/fe_walter/README.md).
All three methods use the same reservoir operation and routing interfaces.

| Method | Decision source | Start here |
|---|---|---|
| Rule-based benchmark | Hanasaki-based flood-control rule | [Rule and matched three-day case](examples/fe_walter/README.md#rule-based-benchmark) |
| Zero-shot | Prompt with available reservoir information | [Prompt and Ollama settings](examples/fe_walter/zero_shot/README.md) |
| DKP | Same LLM interface with retrieved operating knowledge | [Knowledge and Ollama settings](examples/fe_walter/dkp/README.md) |

The [main tutorial](tutorials/main.ipynb) follows input, YAML, prompt/rule,
check, run, verify and audit/trace. The [advanced tutorial](tutorials/advanced.ipynb)
covers multiple reservoirs, passive outlets, routing and your own data.

## Documentation and citation

[User manual](docs/README.md) · [Tutorials](tutorials/README.md) ·
[Native HydroCNHS setup](docs/HYDROLOGY_SETUP.md) ·
[**cylin928.github.io/HydroCNHS/**](https://cylin928.github.io/HydroCNHS/)

Build this project's [HTML manual](docs/BUILDING.md) for module settings,
single/multiple-reservoir setup, audit/trace and troubleshooting.

HydroOpsLM adds reservoir-decision integration to HydroCNHS. Please credit the
original project separately:

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 06022005.

[Project inventory](docs/PROJECT_INVENTORY.md) ·
[Technical note](paper/technical_note.md) ·
[HTML documentation build](docs/BUILDING.md) ·
[Upstream source and license](third_party/hydrocnhs/SOURCE.json)
