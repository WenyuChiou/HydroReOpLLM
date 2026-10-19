# Decision records and audits

Use this reference when you need to explain one decision or diagnose a run.
For the main water-level and release plots, read [Results](RESULTS_GUIDE.md).

## Follow one decision

Read **input information → prompt → reply → requested release → actual release**.
The same decision ID connects these records under the run's `operation/` folder:

| File | Question it answers |
|---|---|
| `decisions.jsonl` and `raw/` | What information and messages did the agent receive, and what did it return? |
| `provider_attempts.jsonl` | Which provider/model answered? Were there retries, errors or fallback attempts? |
| `audit.jsonl` | Did the requested decision meet the configured diagnostic criteria? |
| `physics.jsonl` | What release, spill and storage change actually occurred? |
| `backend_events.jsonl` | Was the completed transition saved for the next decision? |
| `experiment.json` | Which settings, source hashes and runtime produced the run? |

A source hash identifies the exact file bytes used. A completed or **committed**
day has its decision and physical transition saved together. A raw reply alone
does not establish that release was applied.

## Response validation, physics and audit

| Check | Role | Effect on another model request |
|---|---|---|
| Response validation | Accept only the required fields, types, units and completed reply. | An eligible invalid reply can retry within `max_attempts`. |
| Reservoir physics | Apply available water and release limits; calculate spill and storage. | Does not resample an operating decision. |
| Operation audit | Evaluate the configured operating criterion. | Records the outcome; does not resample. |

Audit verdicts are `PASS`, `FAIL`, `WARN` or `UNKNOWN`. `UNKNOWN` means that an
applicable check or required evidence is missing. These verdicts describe the
selected criterion; they do not establish overall operation quality.

## Read post-routing outcome checks

An optional `outcome_audit.jsonl` evaluates flow at a control point after routing.
It records the node, bounds, flow, decision references and verdict. A bound may
come from information selected for that decision; missing optional information
produces `UNKNOWN`. This check records downstream conditions without changing
release or assigning causal blame to one reservoir.

Keep the complete run, including raw replies, failed attempts and source hashes.
If writing these records fails, execution stops. See
[Troubleshooting](TROUBLESHOOTING.md) and [Run and resume](RUNNING.md).
