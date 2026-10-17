# Results, audit and troubleshooting

First compare what the operation method requested with what the reservoir
executed. Then inspect the audit and the trace explaining that decision.

## Read the trajectory

| File | Read it for |
|---|---|
| `reservoir_trajectory.csv` | Inflow, requested release, implemented controlled release, spill and storage |
| `network_flows.csv` | Flow at reservoirs and downstream network nodes |
| `network_balance.csv` | Water-balance evidence for the network |
| `reach_volume_trace.json` | Routing inputs and outputs |
| `summary.json` | Completion, numerical checks and audit counts |
| `outcome_audit.jsonl` | Optional post-routing control-point diagnostics and resolved limit sources |

Rates use **m³/s**; storage and water-balance residuals use **m³**. Total outflow
is implemented controlled release plus spill. The total is injected into routing
once. The next step begins with the previous step's ending storage and uses the
release that was actually implemented.

The [FE Walter results chapter](../examples/fe_walter/results.md) displays the complete saved 2016–2020 daily trajectory and follows selected decisions into their physical outcomes.

## Follow a decision in the trace

Read one step in this order: **available information → rendered prompt → full
reply → operation proposal → response checks → actual release → next-step
information**. For the retrieved-knowledge method, also inspect the excerpts and their sources.

| Record | Evidence |
|---|---|
| `decisions.jsonl` and `raw/` | Information, prompts, replies and normalized proposals |
| `audit.jsonl` | Configured operating criteria and their verdicts |
| `physics.jsonl` and `backend_events.jsonl` | Applied release, storage calculations and coupling events |
| `experiment.json` | Saved settings and provenance |

When an information profile is enabled, the selected source, valid/available
times and history are preserved under
`observation.context.decision_information`. Read that snapshot beside the final
messages, action, physical transition and any control-point outcome record.

The [LLM decision workflow](LLM_MODULES.md) explains each module. The inspector
reads saved records; it makes no model request.

## Distinguish response checks from operation audit

Response checks validate reply completeness, required fields, units and numeric
values. Invalid replies stop before a release is applied. Operation audit
evaluates the configured operating criteria. A feasible release can still fail
an operating criterion.

| Verdict | Interpretation |
|---|---|
| PASS | The applicable configured checks passed |
| FAIL | At least one applicable check failed; inspect its evidence |
| WARN | A configured warning requires interpretation |
| UNKNOWN | The required evidence or an applicable auditor is unavailable |

The saved three-day available-information example retains **2 PASS / 1 FAIL**;
the three-day retrieved-knowledge example retains **3 FAIL**. For annual saved-run
evidence, see the [2016 coupled results](../examples/fe_walter/coupled/README.md#verified-2016-results).
Those completed annual outputs used a prior diagnostic configuration whose DKP
method incorrectly retained `missing_inputs`; the corrected Anik V3.7
configuration is confirmed, but its real-LLM rerun is still pending. Treat the
saved outputs as execution and water-accounting evidence, not acceptance or a
quality result for the corrected case.
The benchmark retains **3 PASS** under its release-bounds auditor. Their auditor
suites differ, so these counts do not establish which policy is better. Strategy
acceptance remains unset in the LLM snapshots.

These historical machine names identify preserved provenance. The public method
titles are **LLM operation with available information** and **LLM operation with
retrieved knowledge**.

## Read post-routing outcome checks

`outcome_audit.jsonl` is separate from request/decision `audit.jsonl`. Each
`control-point-audit.v1` row records the check ID, timestep, node, routed flow,
resolved minimum/maximum, status, limit sources and decision references. A
dynamic limit comes from selected information at that same decision timestep;
missing optional information yields `UNKNOWN`.

The result diagnoses the routed system after decisions and routing. It does not
change a release, resample an LLM after a seasonal FAIL, optimize routing,
guarantee safety or assign causal blame to one agent. Keep its counts separate
from historical request-audit counts.

## Troubleshoot

| Observation | Next step |
|---|---|
| Incomplete or invalid reply | Inspect raw reply and response-check error; no release should be applied |
| FAIL with balanced water | Read the failed operating criterion separately from numerical checks |
| UNKNOWN audit | Check the configured auditor and available evidence |
| Output folder already exists | Copy the YAML and set a new run ID and output path |
| Readiness blocks execution | Resolve the documented prerequisite; retain the original gate |

For interrupted runs and resource planning, read [Running and maintenance](RUNNING.md).
See [detailed troubleshooting](USER_GUIDE.md#troubleshooting),
[audit plugins](auditor_plugins.md) and [live readiness](LIVE_READINESS.md).

- {download}`Download the main notebook <../_notebook_downloads/main.ipynb>`
