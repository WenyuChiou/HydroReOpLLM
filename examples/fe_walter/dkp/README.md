# FE Walter: DKP

[English](README.md) | [繁體中文](README.zh-TW.md) · [Three examples](../README.md)

DKP adds conditionally retrieved operating knowledge to the same LLM interface
used by zero-shot. The difference is the information supplied to the model;
it does not imply better policy performance.

## 1. Prepare input

Inspect the [daily inflow](../../../cases/fe_walter_reference/inflows.csv) and
[reservoir case](../../../cases/fe_walter_ollama_demo/case.json).

| Setting | Shared demonstration condition |
|---|---|
| Dates | 2016-01-01 through 2016-01-03, daily |
| Inflow | Frozen simulated inflow, m³/s |
| Initial storage | 2,457,848.279729185 m³ (1,992.61 acre-ft) |
| Losses | Zero |
| Downstream routing | Identity unit hydrograph, `UH=[1.0]` |

Initial storage and identity routing are integration assumptions, not field
validation. The bounded Ollama diagnostic does not remove the original case's
readiness gate. Read the saved example without starting a model.

## 2. Configure YAML

Open [experiment.ollama.yaml](experiment.ollama.yaml). The YAML selects local Ollama `gemma3:4b`, **temperature 0.7**, daily steps,
**at most three requests**, and **no retries**. Each controlled reservoir is
assigned one independent agent; this case has one.

For a new run, copy it beside its original:

```powershell
Copy-Item examples/fe_walter/dkp/experiment.ollama.yaml examples/fe_walter/dkp/my-run.yaml
```

In `my-run.yaml`, set `run_id: fe-walter-dkp-my-run` and
`output: ../../../runs/fe-walter-dkp-my-run`. Keep the remaining settings for this first
demonstration. An existing output folder must not be reused.

## 3. Review the prompt or rule

Read the [system prompt](../../../prompts/fe_walter_reference/dkp_system.txt)
and [reading preview](prompt_preview.txt). The system template is fixed; current
inflow, starting storage and implemented release history update each day.
Editing the preview does not change execution.

The [DKP document](../../../data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md) supplies
applicable excerpts. The trace preserves the retrieval and its source.

Follow **info → rendered prompt → full reply → operation proposal → response
checks → actual release → next-day information** in the
[main tutorial](../../../tutorials/main.ipynb). It displays complete saved prompts
and replies, including the rationale; release is not the only response field.

## 4. Check

Validate your copied configuration from the repository folder:

```powershell
python run_experiment.py check examples/fe_walter/dkp/my-run.yaml
```

This checks the configuration without inference or a model request.

## 5. Run

The [saved three-day result](../../../results/fe_walter_ollama_2016_01/dkp/) is already available.
Only execute the following if you intend to start a new simulation:

```powershell
python run_experiment.py run examples/fe_walter/dkp/my-run.yaml --allow-network
```

Ollama must already be running with `gemma3:4b` available. `--allow-network`
permits the configured local model requests. This example has a three-request
limit and no automatic retries. An invalid reply stops before release is applied.

## 6. Verify

Verify the existing saved result without rerunning its simulation:

```powershell
python run_experiment.py verify results/fe_walter_ollama_2016_01/dkp
```

After your new run, use `runs/fe-walter-dkp-my-run` instead. Verification checks execution
evidence; it does not establish that the operating policy is good.

## 7. Read results and audit/trace

Read `reservoir_trajectory.csv` for requested release, implemented controlled
release, spill and ending storage. Total outflow is controlled release plus spill
and enters routing once. Next-day history uses implemented release.

| Date | Inflow (m³/s) | Requested (m³/s) | Implemented (m³/s) | Spill (m³/s) | Ending storage (m³) |
|---|---:|---:|---:|---:|---:|
| 2016-01-01 | 32.125319 | 1.415842 | 1.415842 | 0.000000 | 5,111,147.04 |
| 2016-01-02 | 22.353047 | 1.415842 | 1.415842 | 0.000000 | 6,920,121.54 |
| 2016-01-03 | 14.193931 | 1.415842 | 1.415842 | 0.000000 | 8,024,148.43 |

![Three-method daily trajectories](../../../tutorials/assets/fe_walter_three_method.png)

The plot compares the shared three-day demonstration conditions. It is not a
policy-performance assessment. The table above displays this method's saved
trajectory; stored CSVs retain full precision.

The saved operating audit retains **0 PASS / 3 FAIL**.
Its strategy acceptance remains unset. A valid reply and feasible release do not
imply a passing operating audit.

Inspect the saved decision:

```powershell
python tutorials/inspect_decision_flow.py results/fe_walter_ollama_2016_01/dkp
```

`decisions.jsonl`, `raw/`, `audit.jsonl`, `physics.jsonl` and `backend_events.jsonl`
link the information and proposal to checks and execution. The notebook separates
the recorded checker result from a current contract recheck. The inspector makes
no model request. See [results and troubleshooting](../../../docs/RESULTS_GUIDE.md).

[View the main tutorial](../../../tutorials/main.ipynb) ·
[Module reference](../../../docs/LLM_MODULES.md) ·
[Multiple reservoirs](../../../tutorials/advanced.ipynb)
