# HydroReOpLLM User Manual

![HydroReOpLLM reservoir operators and their catchments](assets/branding/cover.png)

Build a reservoir experiment with prepared inflows or a HydroCNHS catchment model. Start with a prescribed release, inspect its water balance, then choose the operating policy for your own case.

[Install and run your first case](GETTING_STARTED.md) · [Browse the daily examples](../examples/daily_offline/README.md) · [繁體中文手冊](README.zh-TW.md)

## How it works

A prepared file supplies local inflow directly. In a coupled case, HydroCNHS runs first and saves inflow for the operating period. At each step, an operator requests a release. The physical model applies the available water and outlet limits, updates storage and spill, and routes flow through the reservoir network. Verification reads the saved decisions and water balance. Assess agreement with observations separately when interpreting a real study.

![HydroReOpLLM coupled architecture linking HydroCNHS hydrology, rule or LLM operators, audits, and trace records](assets/diagrams/framework.png)

## Read in order

| Chapter | What you will do |
| --- | --- |
| [Installation](GETTING_STARTED.md) and [first tutorial](../tutorials/README.md) | Install the software, run four synthetic days and inspect the final storage. |
| [Configuration files](CONFIGURATION.md) | Set the experiment window, input files, operator and output directory. |
| [Prepared inflows](../templates/prepared/README.md) or [hydrology](HYDROLOGY_SETUP.md) | Supply local flows, or generate them from weather and a native model using the [coupled template](../templates/coupled/README.md). |
| [Reservoir networks](MULTI_RESERVOIR.md) and [time scales](TIME_SCALES.md) | Assign an operator to each reservoir, connect the flow paths and choose the step length. |
| [Model providers](MODEL_PROVIDERS.md) and [available information](INFORMATION.md) | Decide what an LLM can see and record the identity of the model used. |
| [Run and verify](RUNNING.md) | Check the configuration, prepare inputs, complete operations and verify the saved run. |
| [Read the results](RESULTS_GUIDE.md) | Compare requested and actual releases, storage and downstream flow. |

## Choose an example

| Example | Input and question |
| --- | --- |
| [One reservoir and a cascade](../examples/daily_offline/README.md) | How does a prescribed release affect downstream storage when reservoirs are connected? |
| [Two reservoirs with separate outlets](../examples/multiple_reservoirs/README.md) | How do weather-driven inflows reach two reservoirs with separate operators? |
| [Daily, hourly and fixed intervals](../examples/time_scales/README.md) | How do timestamps, average flow and interval volumes change with step length? |
| [MOSART-Urban rule](../examples/rules/mosart_urban/README.md) | How do you replace the operating rule while keeping the physical case? |

Each example uses synthetic inputs. For a new basin, start with the [coupled case template](../templates/coupled/README.md). For unexpected run behavior, see [troubleshooting](TROUBLESHOOTING.md).

## Read the manual offline

From an installed Git checkout, build the site and open `site/index.html` in a browser. For full-text search, serve that folder over local HTTP and open `http://127.0.0.1:8000/`.

```sh
python -m pip install -r requirements-docs.txt
python scripts/build_docs.py
python -m http.server 8000 --directory site --bind 127.0.0.1
```
