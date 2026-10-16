# Run a full year, step by step

> This page preserves earlier diagnostic runs. For a new reproduction, use the
> [current coupled configurations](../coupled/README.md), their method-specific
> native system messages, and the explicit case extension.

This walkthrough connects the accepted FE Walter hydrology to reservoir decisions
and downstream flow. Begin here after [installation](../../../docs/GETTING_STARTED.md)
and the [shared case](../README.md). Run commands from the repository root.

**Previous diagnostic:** the rule-based method completed all 366 days. The real LLM
attempt committed 169 days, then stopped on June 18 because its reply was invalid
JSON. That run used a single-attempt transport. Its [results and stopping point](results.md)
remain unchanged. The later paired diagnostic used explicit bounded retries and
one shared custom system prompt, preserved at
[`outputs/custom_system_prompt_20261016.txt`](outputs/custom_system_prompt_20261016.txt).

One case supports a rule-based baseline and two LLM scenarios: available
information, and available information plus retrieved guidance. The current
configurations use separate native system messages and the same physical case and
daily inlet.

## 1. Understand the inputs

| You need to understand | FE Walter choice | Where to inspect it |
|---|---|---|
| Weather | Daymet V4 R1 precipitation and Tmin/Tmax; mean temperature and Hamon PET | [Data and preparation](../hydrology.md#2-data-and-periods) |
| Catchments and soil | Seven units; NHDPlus HR routes, Annual NLCD 2021, SSURGO/SDA attributes | [Subcatchments and parameter derivation](../hydrology.md#3-seven-subcatchments) |
| Hydrological parameters | Accepted semi-distributed GWLF and Lohmann settings | [Native model YAML](../../../data/accepted/fe_walter_hydrology.yaml) |
| Water at the start | Continuous hydrological initialization from 1989; separate assumed initial reservoir storage | [Initial conditions](../hydrology.md#4-shared-gwlf-and-routing-parameters) |
| Operating instructions | Method-specific native messages with only the approved seasonal-target edit; independent benchmark rules | [Current coupled example](../coupled/README.md#files) |

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

## 5. Configure and run the two LLM scenarios

For a live diagnostic, prepare a **new** directory with the explicit readiness
flag. This flag makes no model request; execution still needs `--allow-network`.

```bash
python examples/fe_walter/annual/prepare.py --year 2016 --directory runs/fe-walter-2016-live --run-id fe-walter-2016-live --live-diagnostic
python run_experiment.py check runs/fe-walter-2016-live/llm_knowledge.yaml
python run_experiment.py check runs/fe-walter-2016-live/llm_available.yaml
```

Inspect these settings before executing:

| Setting | Meaning |
|---|---|
| `agents.fe_operator.reservoir` | The physical reservoir controlled by this independent operator |
| `strategy: reference_v3_7` | The retained example implementation, not the name of a general LLM method |
| `reference.method` | Available-information or retrieved-guidance behavior |
| `reference.system_prompt` | Method-specific native system message with only the approved seasonal-target edit |
| `reference.dkp` | Identified knowledge document for the retrieved-guidance method |
| `models.reservoir_model` | Ollama, `gemma3:4b`, temperature 0.7, token limit and timeout |
| `max_calls: null` | Explicitly no total request cap; set an integer if a bounded experiment is preferred |
| `models.reservoir_model.max_attempts: 2` | At most two attempts for one decision, using the same request and unchanged reservoir state |
| `models.reservoir_model.retry_delay_seconds: 2` | Delay before a retry of a transient provider or invalid-response failure |
| `models.reservoir_model.num_ctx`, `.think`, `.keep_alive` | Current explicit Ollama controls: `16384`, `false`, `30m` |
| `reference.consultation_mode` | `daily` in the current example; `native_threshold` restores the native 10% consultation trigger |
| `reference.response_validation: policy` | Original policy parser validates required response fields |
| `auditors` | Release-bound checks; separate from the model's response-format checks |

The current tutorial uses the complete current-day simulated mean inlet as a
hindcast input. It is not a real-time forecast. Information changes each day;
fixed instructions do not. [Prompt construction and raw outputs](../dkp/README.md)
show the retained example fields.

Once the model is installed locally and both configurations are checked, run
the scenarios serially. These commands make real model requests:

```bash
python run_experiment.py run runs/fe-walter-2016-live/llm_available.yaml --allow-network
python run_experiment.py verify runs/fe-walter-2016-live/run-llm_available
python run_experiment.py run runs/fe-walter-2016-live/llm_knowledge.yaml --allow-network
python run_experiment.py verify runs/fe-walter-2016-live/run-llm_knowledge
```

The method differs under `reference.method`: `zeroshot` uses available
information; `dkp` also retrieves the selected knowledge document. Each points to
its own native system message. Do not add `--require-offline` for real-inference runs.

The bounded provider layer retries only its configured transport conditions.
With `response_validation: policy`, the original policy parser handles required
fields and preserves its native failure behavior. Operating audit FAIL, or pool
above/below the target, does not trigger a retry or replace the action. Those are
operating diagnostics and results.

### Read the current method-specific system messages

The [available-information message](../prompts/zeroshot_seasonal_v1_system.txt)
and [operating-knowledge message](../prompts/dkp_seasonal_v1_system.txt) preserve
their respective native instructions and response-field order. Only the approved
seasonal-target paragraph differs from the pinned original. The DKP request keeps
the full native `missing_inputs` field.

The completed 732-request annual records predate this correction. They used the
[preserved shared custom message](outputs/custom_system_prompt_20261016.txt),
omitted `num_ctx`, `think`, and `keep_alive`, and configured
`dkp_no_missing_inputs: true`. Treat them as a diagnostic variant, not current
reproduction evidence; their saved results and raw history remain unchanged.

## 6. Inspect one decision, then the whole year

Start with [one captured real decision](decision_2016_01_01.md): complete messages,
the model's full reply, original audit reasons and the next day's feedback.

| Inspect | What it tells you |
|---|---|
| `progress.json` and `backend_events.jsonl` | Last completed step and visible decision/feedback events |
| `provider_attempts.jsonl` | Durably recorded request starts, captured responses and transport failures, including retries |
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

The primary result figure shows **pool elevation** and **water release** over the
whole year. Storage and audit data remain in the saved records for inspection.

## 7. Continue an interrupted run

If both attempts fail or the process crashes, keep its original directory.
Continue in a new directory using the same configuration and unchanged runtime:

```bash
python run_experiment.py resume runs/fe-walter-2016-live/llm_knowledge.yaml --from-run runs/fe-walter-2016-live/run-llm_knowledge --output runs/fe-walter-2016-live/run-llm_knowledge-continued --run-id fe-walter-2016-knowledge-continued --allow-network
python run_experiment.py verify runs/fe-walter-2016-live/run-llm_knowledge-continued
```

Recovery replays saved replies to rebuild the native routing and reservoir/policy
history, checks the reconstructed physical records, then requests the missing
decision. It does not resample completed decisions or overwrite their source run.
An in-flight request whose response was not journaled can be requested again;
its earlier attempt remains visible. A finite `max_calls` includes earlier
attempts across recovery. With `null`, the total is uncapped.

Changed prompts, model settings, inputs, code or Python runtime require a new
experiment. Recovery currently requires static case information; dynamic external
information providers need a separate replay contract. See
[resources and interruption handling](../../../docs/RUNNING.md).

## 8. Follow the code

Read the [code structure and daily loop](../../../docs/CODE_STRUCTURE.md) for
the entry point, module boundaries and the order of one simulated day.

| Reader's step | Code responsibility |
|---|---|
| Prepare one year | [prepare.py](prepare.py): select dates, prepare shared case and method YAMLs |
| Recompute accepted upstream inflow | [historical.py](../legacy/historical.py): `run_historical`, pinned GWLF/Lohmann and convolution check |
| Validate settings and choose the method | [workflow.py](../../../src/llm_reservoir_agent/workflow.py): `load_settings`, `run_settings` |
| Construct the native prompt, retrieve knowledge and retain the reply | [reference_backend.py](../extensions/reference_backend.py): explicit case extension |
| Run native Dam/routing and common physical updates | [network.py](../../../src/llm_reservoir_agent/network.py), [agent.py](../../../src/llm_reservoir_agent/agent.py) |
| Keep committed decisions, audits and physical evidence together | [experiment.py](../../../src/llm_reservoir_agent/experiment.py), [trace.py](../../../src/llm_reservoir_agent/trace.py) |
| Verify the saved run | [verification.py](../../../src/llm_reservoir_agent/verification.py) |
| Rebuild an interrupted prefix and continue | [recovery.py](../../../src/llm_reservoir_agent/recovery.py) |

This is an executable **two-stage chain**: weather-derived inlet preparation,
then daily coupled operation/routing. A single weather-mode CLI and feedback that
changes upstream runoff remain separate integration work; this walkthrough does
not claim those features.
