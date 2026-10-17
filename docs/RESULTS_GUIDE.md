# Results, audit, and trace

For the generic coupled rule run, start here:

```text
runs/independent-rivers-rule/operation/summary.json
```

The experiment's configured output root is `runs/independent-rivers-rule`.
Preparation evidence is under that root; operation evidence is under
`runs/independent-rivers-rule/operation`. The LLM fixture follows the same layout
at `runs/independent-rivers-mixed/operation`.

Older supplied-inflow examples may place operation files directly at their
configured output root. Use each example's documented path instead of assuming
every output has an `operation/` child.

## Read the operation trajectory

| File under the operation directory | Read it for |
|---|---|
| `summary.json` | Completion, numerical checks, and audit counts |
| `reservoir_trajectory.csv` | Inflow, requested release, implemented controlled release, spill, and storage |
| `network_flows.csv` | Flow at reservoirs and downstream nodes |
| `network_balance.csv` | Network water-balance evidence |
| `reach_volume_trace.json` | Routing inputs and outputs |
| `outcome_audit.jsonl` | Optional post-routing control-point diagnostics and limit sources |

Rates use **m³/s**. Storage and water-balance residuals use **m³**. Total outflow
is implemented controlled release plus spill, injected into routing once. The
next step begins with prior ending storage and the release actually implemented.

## Follow one decision

Read one day in this order: **available information → rendered prompt → full
reply → proposal → response checks → implemented release → next-day information**.
For a retrieved-knowledge method, also inspect the selected excerpts and sources.

| Record under the operation directory | Evidence |
|---|---|
| `decisions.jsonl` and `raw/` | Information, messages, replies, and normalized proposals |
| `provider_attempts.jsonl` | Actual profile, provider, model, attempts, metadata, and errors |
| `audit.jsonl` | Configured decision criteria and verdicts |
| `physics.jsonl` and `backend_events.jsonl` | Applied release, storage calculation, and coupling events |
| `experiment.json` | Resolved settings and provenance |

When an information profile is selected, its source, valid and available times,
and history appear under `observation.context.decision_information`. Read that
snapshot beside the rendered messages, action, physical transition, and any
control-point outcome record. The [LLM decision workflow](LLM_MODULES.md)
describes the modules. The saved-record inspector makes no model request.

## Separate response, physics, and operation evidence

Response checks validate completeness, required fields, units, and numeric
values. Invalid replies stop before release is applied. The physical kernel then
checks feasible water and limits. Operation audits evaluate configured operating
criteria. A physically feasible release can still fail an operating criterion.

| Verdict | Meaning |
|---|---|
| PASS | Applicable configured checks passed |
| FAIL | At least one applicable check failed; inspect its evidence |
| WARN | A configured warning requires interpretation |
| UNKNOWN | Required evidence or an applicable auditor is unavailable |

`verify` establishes saved-file integrity and numerical consistency. Completed
dates establish execution completion. Neither claim establishes good operating
performance. Evaluate seasonal targets, flood control, water supply, or another
study objective with its own accepted rubric.

## Read the F.E. Walter evidence after the generic run

The [latest 2016 Gemma 4 comparison](../examples/fe_walter/coupled/README.md#verified-2016-results)
reports water level, controlled release, and seasonal compliance. Its explicit
current-result files are
[`models.yaml`](../examples/fe_walter/coupled/current/models.yaml),
[`llm_available.yaml`](../examples/fe_walter/coupled/current/llm_available.yaml),
and [`llm_knowledge.yaml`](../examples/fe_walter/coupled/current/llm_knowledge.yaml).
The [historical results chapter](../examples/fe_walter/results.md) preserves the
separate 2016–2020 trajectory and its original targets. Do not use an older
Gemma 3 profile to claim reproduction of the Gemma 4 comparison.

The current comparison uses confirmed Anik V3.7 prompts with the approved
seasonal-target edit and real `gemma4:12b` replies. Original code and HydroOpsLLM
completed 366 days for each LLM method. Read completion, engineering checks, and
seasonal operating performance separately; completion does not mean every
operating target was met.

The [earlier annual configuration](../examples/fe_walter/coupled/README.md#earlier-2016-configuration-preserved)
retains the earlier diagnostic response contract, including DKP
`missing_inputs`. The older three-day tutorial preserves **2 PASS / 1 FAIL** for
available information, **3 FAIL** for retrieved knowledge, and **3 PASS** for its
rule method. The auditor suites differ, so these counts do not rank the methods.
Strategy acceptance remains unset in those three-day LLM snapshots.

Historical machine names preserve provenance. Public method titles are **LLM
operation with available information** and **LLM operation with retrieved
knowledge**.

## Read post-routing outcome checks

`outcome_audit.jsonl` is separate from decision `audit.jsonl`. Each
`control-point-audit.v1` row records the check ID, timestep, node, routed flow,
resolved limit, status, limit sources, and decision references. A dynamic limit
comes from selected information at the same decision timestep; missing optional
information produces `UNKNOWN`.

This result diagnoses the routed system after decisions and routing. It does not
change release, resample an LLM after a seasonal FAIL, optimize routing,
guarantee safety, or assign causal blame to one agent. Keep these counts separate
from historical request-audit counts.

## Troubleshoot

| Observation | Next step |
|---|---|
| Incomplete or invalid reply | Inspect the raw reply and response-check error; release should not be applied |
| FAIL with balanced water | Read the operating criterion separately from numerical checks |
| UNKNOWN audit | Check the configured auditor and available evidence |
| Output folder already exists | Copy the YAML and set a new run ID and output path |
| Readiness blocks execution | Resolve the documented prerequisite and retain the original gate |

For interruption and resource planning, read [Running and recovery](RUNNING.md).
See [audit plugins](auditor_plugins.md) and [live readiness](LIVE_READINESS.md)
for advanced checks.

- {download}`Download the main notebook <../_notebook_downloads/main.ipynb>`
