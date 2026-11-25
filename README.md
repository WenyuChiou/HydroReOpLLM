# HydroReOpLLM

[![User manual](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/) · [繁體中文](README.zh-TW.md)

![Reservoirs and rivers with LLM reservoir operators](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM builds on HydroCNHS to simulate reservoir operations using prepared inflows or weather data, with rule-based, prescribed, or LLM-based release decisions.

## Quick start

Run a four-day synthetic single-reservoir case with a prescribed release. The simulation requires no API key. Start in an empty working directory with an active Python 3.12 or newer virtual environment. [Create a virtual environment](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.html#install-from-pypi).

```sh
python -m pip install hydroreopllm
reservoir-experiment init-examples
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

Look for `PASS`, 4 days, and `observed_network_calls: 0` in the verification output. Open `runs/daily-single/summary.json` to confirm the run is `COMPLETED` and the final storage of `Lake_1` is **1,345,600 m³**. To repeat the case, [set a new run ID and output path](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.html#repeat-a-run).

## Clone and run the notebook

The PyPI package includes ready-to-run examples. Clone the repository for the notebook and the full collection of examples and templates. [Clone and install HydroReOpLLM](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.html#install-from-a-clone) · [Open the notebook tutorial](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.html)

## Choose an example

| What you want to do | Where to start |
| --- | --- |
| Trace releases through one reservoir or a connected cascade | [Single-reservoir and cascade examples](https://wenyuchiou.github.io/HydroReOpLLM/examples/daily_offline/index.html) |
| Run two independent reservoirs driven by weather data, each draining to its own outlet | [Two reservoirs with separate outlets](https://wenyuchiou.github.io/HydroReOpLLM/examples/multiple_reservoirs/index.html) |
| Run daily, hourly, or fixed-interval simulations | [Time-step examples](https://wenyuchiou.github.io/HydroReOpLLM/examples/time_scales/index.html) |
| Set up your own case and inspect decisions, storage, and water balance | [Configuration](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.html) · [Results guide](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.html) |

## Tests and license

From a clone, install the test extra with `python -m pip install -c environment/requirements-bundled.txt ".[test]"` and run `python -m pytest -q`.

[BSD 3-Clause License](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [Third-party notices](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
