# HydroReOpLLM

[![User manual](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/) · [繁體中文](README.zh-TW.md)

![Reservoirs and rivers with LLM reservoir operators](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM builds on HydroCNHS to simulate reservoir operations with prepared inflows and prescribed or LLM-based release decisions.

## Quick start

Run the generic prepared-inflow template from this checkout without an API key. Python 3.12 or newer is required.

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

Choose a fresh `run_id` and `output` before repeating the template. See the [installation and first-run guide](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.html) and [results guide](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.html).

## Public examples

| Entry point | Purpose | Network use |
| --- | --- | --- |
| [`examples/template/experiment.yaml`](examples/template/README.md) | Generic synthetic prepared-inflow workflow | None |
| [`examples/fe_walter/seasonal_target.yaml`](examples/fe_walter/README.md) | F.E. Walter seasonal-target operator with its named system prompt | Local Ollama only when `run --allow-network` is requested |
| [`examples/fe_walter/dkp.yaml`](examples/fe_walter/README.md) | F.E. Walter Decision Knowledge Package (DKP) operator with its named system prompt | Local Ollama only when `run --allow-network` is requested |

[Open the hosted F.E. Walter tutorial](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html).

Run `reservoir-experiment check` first. It validates either F.E. Walter configuration without contacting Ollama. The included inflows are synthetic teaching inputs; model outputs and article results are not bundled.

## Tests and license

From a clone, install the test extra with `python -m pip install -c environment/requirements-bundled.txt ".[test]"` and run `python -m pytest -q`.

[BSD 3-Clause License](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [Third-party notices](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
