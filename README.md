# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

[![Documentation — Open manual](https://wenyuchiou.github.io/LLM_reservoir_agent/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/LLM_reservoir_agent/)

![HydroOpsLM cover](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** is a Python framework for studying language-model reservoir
decisions inside coupled hydrological simulations. It connects configurable
decision methods to the existing Dam API in
[HydroCNHS](https://github.com/cylin928/HydroCNHS), which remains the native
hydrology, routing, parameter, calibration and validation foundation.

![HydroCNHS coupling framework with HydroOpsLM](docs/figures/hydrocnhs-coupling-framework-en.png)

Blue arrows show water flow; black arrows show information and release proposals.
Gray cards supply external data or optional knowledge. The native Dam API is
retained; HydroOpsLM adds the common storage, release and spill calculations.
Downstream simulation information comes from completed days. GWLF and ABCD are
runoff-model alternatives; Lohmann is the routing method; the Dam API couples
reservoir operation to that water pathway.

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
| LLM operation with available information | Prompt with available reservoir information | [Prompt and Ollama settings](examples/fe_walter/zero_shot/README.md) |
| LLM operation with retrieved knowledge | Same LLM interface with source-bound retrieved knowledge | [Knowledge and Ollama settings](examples/fe_walter/dkp/README.md) |

The [main tutorial](tutorials/main.ipynb) follows input, YAML, prompt/rule,
check, run, verify and audit/trace. The [advanced tutorial](tutorials/advanced.ipynb)
covers multiple reservoirs, passive outlets, routing and your own data.

## Documentation and citation

[User manual](docs/index.md) · [Decision information](docs/INFORMATION.md) · [Tutorials](tutorials/README.md) ·
[Native HydroCNHS setup](docs/HYDROLOGY_SETUP.md) ·
[**cylin928.github.io/HydroCNHS/**](https://cylin928.github.io/HydroCNHS/)

Read the [online manual](https://wenyuchiou.github.io/LLM_reservoir_agent/) for chapter navigation, three methods,
single/multiple-reservoir setup, audit/trace and downloadable tutorial notebooks.
You can also [build the site locally](docs/BUILDING.md).

HydroOpsLM adds reservoir-decision integration to HydroCNHS. Please credit the
original project separately:

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 06022005.

[Project inventory](docs/PROJECT_INVENTORY.md) ·
[Technical note](paper/technical_note.md) ·
[HTML documentation build](docs/BUILDING.md) ·
[Upstream source and license](third_party/hydrocnhs/SOURCE.json)
