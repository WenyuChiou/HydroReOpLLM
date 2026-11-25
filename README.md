# HydroReOpLLM

[![User manual](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/) · [繁體中文](README.zh-TW.md)

![Reservoirs and rivers with LLM reservoir operators](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM builds on HydroCNHS to simulate reservoir operations with prepared inflows and prescribed or LLM-based release decisions.

## Quick start

Run the generic two-agent prepared-inflow template from this checkout without an API key. Python 3.12 or newer is required.

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
| [`examples/fe_walter/rule_based.yaml`](examples/fe_walter/README.md) | F.E. Walter offline Hanasaki rule | None |
| [`examples/fe_walter/seasonal_target.yaml`](examples/fe_walter/README.md) | F.E. Walter **Without operational knowledge** (Seasonal Target) | Local Ollama only when `run --allow-network` is requested |
| [`examples/fe_walter/dkp.yaml`](examples/fe_walter/README.md) | F.E. Walter **With operational knowledge** (DKP) | Local Ollama only when `run --allow-network` is requested |

[Open the hosted F.E. Walter tutorial](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html).

Run `reservoir-experiment check` first. It validates all three F.E. Walter configurations without contacting Ollama. The three F.E. Walter configurations use the study's prepared 2021–2025 inflows and start with a seven-day tutorial run. The [case guide](examples/fe_walter/README.md) explains how to run the full period with the public prompts and simulator.

## Tests and license

From a clone, install the test extra with `python -m pip install -c environment/requirements-bundled.txt ".[test]"` and run `python -m pytest -q`.

[BSD 3-Clause License](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [Third-party notices](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
