# HydroReOpLLM

[User manual](docs/README.md) · [繁體中文使用手冊](docs/README.zh-TW.md) · [繁體中文首頁](README.zh-TW.md)

HydroReOpLLM simulates reservoir operations from time series of local inflow or weather forcing. A reservoir operator proposes a release. The physical model applies storage and release limits, routes water downstream, and records the decision and water balance for each time step. Operators can use a rule, a prescribed action, or an LLM with local operating guidance.

## Install from a clone

Use Git and Python 3.12. The first installation downloads the Python dependencies.

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

## Examples and tests

- [Documentation index on GitHub](docs/README.md)
- [Runnable notebook for the four-day example](tutorials/offline_synthetic.ipynb)
- [Daily reservoir and cascade](examples/daily_offline/README.md)
- [Two independently operated reservoirs with weather-driven inflows](examples/multiple_reservoirs/README.md)
- [Daily, hourly and fixed time steps](examples/time_scales/README.md)
- [Starting a case from a template](templates/prepared/README.md)

To run the tests, use the same virtual environment and install the test extra. On Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

The checkout includes the bundled HydroCNHS source, upstream license, version information and patches. [Source attribution](THIRD_PARTY_NOTICES.md)
