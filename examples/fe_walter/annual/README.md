# Run a full year, step by step

This walkthrough connects the accepted FE Walter hydrology to reservoir decisions
and downstream flow. Begin here after [installation](../../../docs/GETTING_STARTED.md)
and the [shared case](../README.md). Run commands from the repository root.

**Observed test:** the rule-based method completed all 366 days. The real LLM
attempt committed 169 days, then stopped on June 18 because its reply was invalid
JSON. No automatic retry was made. Read the [results and stopping point](results.md)
before launching another inference run; this is not a passed annual LLM example.

The same case supports a rule-based method, an LLM with available information,
and an LLM with retrieved guidance. Choose one method to run; do not launch all
LLM configurations just to check the files.

## 1. Understand the inputs

| You need to understand | FE Walter choice | Where to inspect it |
|---|---|---|
| Weather | Daymet V4 R1 precipitation and Tmin/Tmax; mean temperature and Hamon PET | [Data and preparation](../hydrology.md#2-data-and-periods) |
| Catchments and soil | Seven units; NHDPlus HR routes, Annual NLCD 2021, SSURGO/SDA attributes | [Subcatchments and parameter derivation](../hydrology.md#3-seven-subcatchments) |
| Hydrological parameters | Accepted semi-distributed GWLF and Lohmann settings | [Native model YAML](../../../data/accepted/fe_walter_hydrology.yaml) |
| Water at the start | Continuous hydrological initialization from 1989; separate assumed initial reservoir storage | [Initial conditions](../hydrology.md#4-shared-gwlf-and-routing-parameters) |
| Operating instructions | Seasonal-pool v1 prompt for LLM methods; independent rule configuration for the benchmark | [Seasonal target](../../../docs/USER_GUIDE.md) |

For another catchment, prepare and evaluate its hydrological model first. This
walkthrough starts from the accepted FE Walter input bundle; it does not download
raw GIS data or recalibrate parameters. The [preparation order](../hydrology.md#preparation-order-used-for-this-case)
explains how that bundle was built.

## 2. Review C&V before changing the operator

Use **1989** for warm-up, **1990–2010** for calibration and **2011–2020** for
independent validation. Accepted gauge KGE is **0.7326 / 0.7112**. Gauge 01447500
covers two donor units; the other five do not have independent gauge validation.
The 2021–2025 extension uses frozen parameters.

Review the [full metrics and fixed-parameter reproduction](../hydrology.md#5-accepted-calibration-and-validation-results).
Changing a prompt does not require rerunning a parameter search. Keep hydrology
fixed when comparing operation methods.

## 3. Prepare the common annual case

```bash
python examples/fe_walter/annual/prepare.py --year 2016 --directory runs/fe-walter-2016 --run-id fe-walter-2016
```

Preparation makes **zero LLM requests**. It reruns the accepted continuous
1989–2025 hydrology, retains upstream routing history, and selects 2016 for
operation. This gives **366 days**, including February 29. It does not cold-start
GWLF on January 1, 2016.

| Generated file | What you use it for |
|---|---|
| `case.json` | Shared physical limits, initial reservoir storage and network |
| `inflows.csv` | Routed inlet plus explicit zero lateral flow in the demonstration reach |
| `annual_hydrology.csv` | Check generated runoff, upstream routing and the selected inlet |
| `hydrology_summary.json` | Input/source pins and independent upstream-routing comparison |
| `rule.yaml` | Run the deterministic benchmark |
| `llm_available.yaml` | Run the available-information LLM method |
| `llm_knowledge.yaml` | Run the retrieved-guidance LLM method |
| `preparation.json` | Calendar, file hashes and preparation settings |

All three YAMLs point to the same physical case. The downstream demonstration
uses `UH=[1]`: outflow reaches the downstream node on the same day. It is not a
calibrated travel-time model. Initial reservoir storage is the retained reference
assumption, **not an observed January 2016 state**.

Choose a new preparation directory and run ID for a new experiment. Existing
directories are refused, including partial work; nothing is silently overwritten.

## 4. Check and run the rule-based method

```bash
python run_experiment.py check runs/fe-walter-2016/rule.yaml
python run_experiment.py run runs/fe-walter-2016/rule.yaml
python run_experiment.py verify runs/fe-walter-2016/run-rule --require-offline
```

The plan should report `days: 366`, `planned_llm_calls: 0` and
`strategy: benchmark` under the agent strategy map. A completed run has 366
committed decisions and physical updates. Verification checks stored evidence,
water balance and downstream routing; a PASS does not establish seasonal-pool
performance.

Rule coefficients and pre-experiment statistics are specified under the YAML's
`benchmark` section. See the [rule source and interpretation](../benchmark/README.md).

## 5. Configure and run one LLM method

For a live diagnostic, prepare a **new** directory with the explicit readiness
flag. This flag makes no model request; execution still needs `--allow-network`.

```bash
python examples/fe_walter/annual/prepare.py --year 2016 --directory runs/fe-walter-2016-live --run-id fe-walter-2016-live --live-diagnostic
python run_experiment.py check runs/fe-walter-2016-live/llm_knowledge.yaml
```

Inspect these settings before executing:

| Setting | Meaning |
|---|---|
| `agents.fe_operator.reservoir` | The physical reservoir controlled by this independent operator |
| `strategy: reference_v3_7` | The retained example implementation, not the name of a general LLM method |
| `reference.method` | Available-information or retrieved-guidance behavior |
| `reference.system_prompt` | Fixed seasonal operating instructions |
| `reference.dkp` | Identified knowledge document for the retrieved-guidance method |
| `models.reservoir_model` | Ollama, `gemma3:4b`, temperature 0.7, token limit and timeout |
| `max_calls: 366` | At most one request per reservoir-day; no automatic retry |
| `auditors` | Release-bound checks; separate from the model's response-format checks |

The current tutorial uses the complete current-day simulated mean inlet as a
hindcast input. It is not a real-time forecast. Information changes each day;
fixed instructions do not. [Prompt construction and raw outputs](../dkp/README.md)
show the retained example fields.

Once the model is installed locally and the configuration is checked:

```bash
python run_experiment.py run runs/fe-walter-2016-live/llm_knowledge.yaml --allow-network
python run_experiment.py verify runs/fe-walter-2016-live/run-llm_knowledge
```

This requests new model decisions. To choose the available-information method,
use `llm_available.yaml` instead. Running both methods requires a separate budget
for each. Do not add `--require-offline` when verifying a real-inference run.

## 6. Inspect one decision, then the whole year

Start with [one captured real decision](decision_2016_01_01.md): complete messages,
the model's full reply, original audit reasons and the next day's feedback.

| Inspect | What it tells you |
|---|---|
| `progress.json` and `backend_events.jsonl` | Last completed step and visible decision/feedback events |
| `decisions.jsonl` and referenced `raw/` files | Information, fixed/rendered prompt, model reply, requested release and response checks |
| `physics.jsonl` | Implemented controlled release, spill, ending storage and feedback for the next step |
| `reservoir_trajectory.csv` | Full-period inlet, requested/implemented release and storage |
| `network_flows.csv` and `network_balance.csv` | Downstream total outflow and accounting |
| `audit.jsonl` | Operating checks and original PASS/FAIL/WARN/UNKNOWN verdicts |
| `summary.json` | Completion status, committed days, calls and output hashes |

The aggregate CSV files are written after successful completion. A failed run
may contain only the committed JSONL journals and referenced raw files. The saved
annual LLM attempt has no final trajectory or network CSV; its partial figure
was reconstructed from those journals and stops at the last committed day.

At day t, add inlet to beginning storage; obtain a requested release; apply the
shared physical calculation; route **implemented controlled release + spill once**.
Day t + 1 uses committed ending storage and implemented-release history.
The retained reference prompt shows both the prior requested decision and what
was actually released. Its implemented history is total outflow, including spill.

Read a concrete day's prompt/reply and physical result before interpreting an
annual plot. Check all 366 dates, balances, next-day continuity and request counts.
Keep **response validity**, **successful execution** and **operating performance**
as separate conclusions. Audit FAIL must remain visible even if execution completes.

If a model call or write fails, retain the run and its partial evidence. The
runner does not silently retry, switch methods or resume. See
[resources and interruption handling](../../../docs/RUNNING.md).

## 7. Follow the code

| Reader's step | Code responsibility |
|---|---|
| Prepare one year | [prepare.py](prepare.py): select dates, prepare shared case and method YAMLs |
| Recompute accepted upstream inflow | [historical.py](../../../src/delaware_operations/historical.py): `run_historical`, pinned GWLF/Lohmann and convolution check |
| Validate settings and choose the method | [workflow.py](../../../src/llm_reservoir_agent/workflow.py): `load_settings`, `run_settings` |
| Construct the LLM prompt, retrieve knowledge and retain the reply | [reference_backend.py](../../../src/llm_reservoir_agent/reference_backend.py): retained example backend |
| Run native Dam/routing and common physical updates | [network.py](../../../src/llm_reservoir_agent/network.py), [agent.py](../../../src/llm_reservoir_agent/agent.py) |
| Keep committed decisions, audits and physical evidence together | [experiment.py](../../../src/llm_reservoir_agent/experiment.py), [trace.py](../../../src/llm_reservoir_agent/trace.py) |
| Verify the saved run | [verification.py](../../../src/llm_reservoir_agent/verification.py) |

This is an executable **two-stage chain**: weather-derived inlet preparation,
then daily coupled operation/routing. A single weather-mode CLI and feedback that
changes upstream runoff remain separate integration work; this walkthrough does
not claim those features.
