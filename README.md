# HydroOpsLLM

[![User manual](docs/_static/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroOpsLLM/)
![Python 3.12 setup](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)

[English](README.md) | [繁體中文](README.zh-TW.md) · [User manual](https://wenyuchiou.github.io/HydroOpsLLM/) · [Quick start](#installation)

HydroOpsLLM is a HydroCNHS-based Python package for coupling LLM-driven decision-making with hydrological simulation, with applications to reservoir operations and water management.

![HydroOpsLLM cover](docs/figures/hydroopslm-cover.png)

## Installation

Use Python 3.12. Repository access is required while this project is private.

```sh
git clone https://github.com/WenyuChiou/HydroOpsLLM.git
cd HydroOpsLLM
```

On Linux/macOS, with Python 3.12 installed:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, with Python 3.12 available through the Python launcher:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

Confirm that the activated interpreter reports Python 3.12 before installing:

```sh
python --version
python -m pip install -e . -c environment/requirements-bundled.txt
```

## Quick start: daily reservoir operation

HydroOpsLLM advances the coupled system **one day at a time**: read inflow and state → request release → update storage and route outflow → feed the implemented result into the next decision. The simulation period is configured separately from this daily timestep.

Run the F.E. Walter rule-based example without a language model or API key:

```sh
python run_experiment.py check examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-benchmark --require-offline
```

This example computes daily releases for January 1–3, 2016; it uses an operating rule, not fixed actions. Start with a fresh output location; see the [run guide](docs/USER_GUIDE.md) for configuration, longer periods and repeat runs.

### Explore Rule-based, Zero-shot and DKP

The [F.E. Walter tutorial](examples/fe_walter/README.md) follows three methods through the same daily coupling workflow:

| Method | Daily decision | Example |
|---|---|---|
| Rule-based | Flood-control rule using inflow, storage and historical statistics | [Run and inspect](examples/fe_walter/benchmark/README.md) |
| Zero-shot | LLM uses instructions and available reservoir information | [Prompt, reply and operation](examples/fe_walter/zero_shot/README.md) |
| DKP | LLM also uses retrieved document knowledge | [Retrieval, reply and operation](examples/fe_walter/dkp/README.md) |

The LLM examples preserve the Anik V3.7 reference-method integration. Inspect actual saved daily prompts, replies, release and storage in the [main notebook](tutorials/main.ipynb), without making a model request. Check both LLM configurations before execution:

```sh
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py check examples/fe_walter/dkp/experiment.ollama.yaml
```

`check` makes no provider request. New LLM runs need local Ollama with `gemma3:4b` available and explicit `--allow-network`; these examples need no API key. Other providers may require credentials and incur charges. Follow the method links for execution commands. The saved tutorial illustrates decisions; it is not a controlled performance ranking.

## Capabilities

- Configure decision information, prompts and model providers for each controlled reservoir.
- Exchange rule-based and LLM policies through a shared reservoir-action interface.
- Couple reservoir operations to HydroCNHS routing, with implemented outcomes feeding later decisions.
- Record information, proposals, audits and physical outcomes for reproducible analysis.
- Build multi-reservoir experiments; see the [advanced tutorial](tutorials/advanced.ipynb).

## Architecture and information flow

Three flows remain distinct:

1. **Water and physical state:** inflow → HydroCNHS routing → reservoir transition → downstream routing and updated storage.
2. **Decision information:** selected state and eligible external information → prompt/backend → requested action.
3. **Feedback and evidence:** implemented transition → subsequent decision history; decision and physical records → audit and saved-run verification.

The LLM sees the information in its messages; storage and routing remain under host control.

| Component | Current modules | Responsibility |
|---|---|---|
| Setup and orchestration | `workflow`, `case`, `experiment` | Validate inputs, assemble methods, enforce execution gates and coordinate runs |
| Native simulation coupling | `network`, `agent` | Bind policies to HydroCNHS Dam agents, routing and committed feedback |
| Physical accounting | `physics`, `passive`, `balance` | Implement release, spill, storage and reservoir/network accounting |
| Decision information | `information`, `information_runtime` | Select timestamp-eligible data and bind simulation information |
| Policies and providers | `configured_backend`, `benchmark`, `reference_backend`, `policy_adapter` | Generate and normalize proposals; preserve method-specific behavior |
| Audits and evidence | `auditor`, `configured_audit`, `outcome`, `trace`, `verification` | Assess configured criteria, diagnose routed outcomes and verify saved records |

These modules belong to `llm_reservoir_agent`. The bundled `hydrocnhs` namespace retains upstream APIs. `delaware_operations` preserves historical and compatibility code, including adapters still used by reference methods. See [LLM modules](docs/LLM_MODULES.md) for interfaces and extension boundaries.

## Documentation and research use

[User manual](https://wenyuchiou.github.io/HydroOpsLLM/) · [Design a simulation](docs/BUILD_SIMULATION.md) · [Model configuration](docs/USER_GUIDE.md) · [Read results](docs/RESULTS_GUIDE.md)

The current CLI uses supplied daily inflows and native HydroCNHS routing/Dam coupling. The F.E. Walter examples read frozen hydrological outputs. Weather-driven integration requires explicit native model and policy wiring; see [hydrological setup](docs/HYDROLOGY_SETUP.md) and [daily coupling](examples/fe_walter/coupling.md).

Record the code commit, environment, inputs, prompts, model settings and complete run evidence. Physical assumptions, audit interpretation and extension requirements are documented in the [case guide](examples/fe_walter/README.md), [module guide](docs/LLM_MODULES.md) and [running guide](docs/RUNNING.md). This is research software; operating audits do not certify dam safety.

## License

Project license: pending; no MIT license is currently supplied. HydroCNHS retains its [BSD 3-Clause license](licenses/HydroCNHS-BSD-3-Clause.txt). Review the [third-party notices](THIRD_PARTY_NOTICES.md), including unresolved Anik redistribution permissions, before public distribution.

## References and citation

HydroOpsLLM builds on [HydroCNHS](https://github.com/cylin928/HydroCNHS), bundled at commit `fdd5097a3fcabb312c6c3739efc71da2d67c47da` ([source provenance](third_party/hydrocnhs/SOURCE.json)). Please cite the original framework:

Lin, C.-Y., Yang, Y.-C. E., and Wi, S. (2022). “HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems.” *Journal of Water Resources Planning and Management*, 148(12), 06022005. [doi:10.1061/(ASCE)WR.1943-5452.0001630](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).

See the [reference guide](docs/REFERENCE.md) for operation-method sources. Record the HydroOpsLLM commit separately; a dedicated software citation/DOI has not yet been specified.
