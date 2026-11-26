# HydroReOpLLM

[![User manual](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/) · [繁體中文](README.zh-TW.md)

![Reservoirs and rivers with LLM reservoir operators](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM builds on HydroCNHS to simulate reservoir operations with prepared inflows and rule-based or LLM-driven release decisions.

## Quick start

Run the generic two-agent template offline without an API key (Python 3.12+ required).

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

Set a new `run_id` and `output` before repeating a run. See [Installation and first run](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.html) and [Read your results](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.html).

## Public examples

| Entry point | Study condition / purpose | Network use |
| --- | --- | --- |
| [`examples/template/experiment.yaml`](examples/template/README.md) | Generic two-reservoir prepared-inflow cascade | None |
| [`examples/fe_walter/rule_based.yaml`](examples/fe_walter/README.md) | **Rule-based** (Hanasaki flood-control baseline) | None |
| [`examples/fe_walter/seasonal_target.yaml`](examples/fe_walter/README.md) | **Without operational knowledge** (`seasonal_target.yaml`) | Local Ollama via study launcher |
| [`examples/fe_walter/dkp.yaml`](examples/fe_walter/README.md) | **With operational knowledge** (`dkp.yaml`) | Local Ollama via study launcher |

Walk through the cases in the [F.E. Walter tutorial](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html) or read the [F.E. Walter case guide](examples/fe_walter/README.md) to replay published scores offline.

## Tests and license

Install test dependencies with `python -m pip install -c environment/requirements-bundled.txt ".[test]"` and run `python -m pytest -q`.

[BSD 3-Clause License](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [Third-party notices](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
