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

Rates use **m³/s**; storage and water-balance residuals use **m³**. Total outflow
is implemented controlled release plus spill. The total is injected into routing
once. The next step begins with the previous step's ending storage and uses the
release that was actually implemented.

![Three-day FE Walter trajectories](../tutorials/assets/fe_walter_three_method.png)

The saved examples share inflow and initial conditions. The plot illustrates
the resulting reservoir trajectories, not a validated ranking of operation
methods. Detailed tables are embedded in the [main tutorial](../tutorials/main.ipynb).

## Follow a decision in the trace

Read one step in this order: **available information → rendered prompt → full
reply → operation proposal → response checks → actual release → next-step
information**. For DKP, also inspect the retrieved excerpts and their sources.

| Record | Evidence |
|---|---|
| `decisions.jsonl` and `raw/` | Information, prompts, replies and normalized proposals |
| `audit.jsonl` | Configured operating criteria and their verdicts |
| `physics.jsonl` and `backend_events.jsonl` | Applied release, storage calculations and coupling events |
| `experiment.json` | Saved settings and provenance |

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

The saved zero-shot example retains **2 PASS / 1 FAIL**; DKP retains **3 FAIL**.
The benchmark retains **3 PASS** under its release-bounds auditor. Their auditor
suites differ, so these counts do not establish which policy is better. Strategy
acceptance remains unset in the LLM snapshots.

## Troubleshoot

| Observation | Next step |
|---|---|
| Incomplete or invalid reply | Inspect raw reply and response-check error; no release should be applied |
| FAIL with balanced water | Read the failed operating criterion separately from numerical checks |
| UNKNOWN audit | Check the configured auditor and available evidence |
| Output folder already exists | Copy the YAML and set a new run ID and output path |
| Readiness blocks execution | Resolve the documented prerequisite; retain the original gate |

See [detailed troubleshooting](USER_GUIDE.md#troubleshooting),
[audit plugins](auditor_plugins.md) and [live readiness](LIVE_READINESS.md).

- {download}`Download the main notebook <../_notebook_downloads/main.ipynb>`
