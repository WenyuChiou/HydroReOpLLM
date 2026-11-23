# HydroReOpLLM

[User manual](https://wenyuchiou.github.io/HydroReOpLLM/) · [繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html) · [繁體中文首頁](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/README.zh-TW.md)

HydroReOpLLM simulates reservoir operations from time series of local inflow or weather forcing. A reservoir operator proposes a release. The physical model applies storage and release limits, routes water downstream, and records the decision and water balance for each time step. Operators can use a rule, a prescribed action, or an LLM with local operating guidance.

## Install the Python package

In an active Python 3.12 virtual environment, install the published package from PyPI.

```sh
python -m pip install hydroreopllm
```

From an empty working directory, copy the bundled examples, then run and verify the four-day reservoir simulation.

```sh
python -c "import shutil, sysconfig; from pathlib import Path; shutil.copytree(Path(sysconfig.get_path('data')) / 'share/llm-reservoir-agent/examples', 'examples')"
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

## Install from a clone

Clone the default branch for the latest source, tutorials, and case templates. The first installation downloads the Python dependencies.

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt .
```

On macOS or Linux:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -c environment/requirements-bundled.txt .
```

## Run a reservoir and check the output

From the repository root, use the Python executable in the environment you just created. On Windows:

```powershell
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow check examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow run examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow verify runs/daily-single --require-offline
```

On macOS or Linux, use `.venv/bin/python` in those three commands. This example simulates one synthetic reservoir for four days with a prescribed release of 1 m³/s. It needs no model service or API key. The run creates `runs/daily-single/` on your machine. Choose a fresh `output` directory in the YAML before repeating a run.

## Examples and tests in the Git checkout

- [Documentation index on GitHub](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/docs/README.md)
- [Runnable notebook for the four-day example](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/offline_synthetic.ipynb)
- [Daily reservoir and cascade](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/examples/daily_offline/README.md)
- [Two independently operated reservoirs with weather-driven inflows](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/examples/multiple_reservoirs/README.md)
- [Daily, hourly and fixed time steps](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/examples/time_scales/README.md)
- [Starting a case from a template](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/templates/prepared/README.md)

To run the tests, use the same virtual environment and install the test extra. On Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

## License

HydroReOpLLM is distributed under the [BSD 3-Clause License](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE). The bundled HydroCNHS source retains the [BSD 3-Clause notice from Chung-Yi Lin](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/licenses/HydroCNHS-BSD-3-Clause.txt). See the [source attribution and patch history](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md).
