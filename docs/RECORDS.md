# Decision records and audits

Use this reference when you need to explain one decision or diagnose a run.
For the main water-level and release plots, read [Results](RESULTS_GUIDE.md).

## Follow one decision

Read **input information → prompt → reply → requested release → actual release**.
The same decision ID connects these records under the run's `operation/` folder:

| File | Question it answers |
|---|---|
| `decisions.jsonl` and `raw/` | What information and messages did the agent receive, and what did it return? |
| `provider_attempts.jsonl` | Which requests were sent (URL and request body, including the model), and did each one return or fail? One record is written before each request and one after it. |
| `audit.jsonl` | Did the requested decision meet the configured diagnostic criteria? |
| `physics.jsonl` | What release, spill and storage change actually occurred? |
| `backend_events.jsonl` | Was the completed transition saved for the next decision? |
| `experiment.json` | Which settings, source hashes and runtime produced the run? |

A source hash identifies the exact file bytes used. A completed or **committed**
day has its decision and physical transition saved together. A raw reply alone
does not establish that release was applied.

## Count which model profile served each decision

An agent can list backup profiles in `customization.fallback_models`. When the
primary model fails and a backup profile answers, the run still ends COMPLETED
and `verify` reports PASS. Each record in `decisions.jsonl` carries the
*configured primary* profile under `provenance.model` (and the configured
backups under `provenance.fallback_models`), not the profile that served the
decision. Do not read `provenance.model` as the model that answered. Also,
`automatic_retry` in `experiment.json` only reflects whether an agent's primary
profile allows more than one attempt; it says nothing about fallback. There is
no rule-based, last-release or fixed-value fallback. If every profile fails, the
run fails.

To count the serving profile for each decision:

1. Take the decision's `raw_policy_ref` from `decisions.jsonl` and open that
   `raw/policy_*.json` file.
2. In `backend_trace.attempts`, find the attempt with `"success": true`.
3. Read its `profile` (the position in the order primary profile first, then
   `fallback_models`; `0` is the primary), `provider` and `model`.
4. Count decisions per `profile`.

Check this before attributing results to one model. If the count for profile `0`
is lower than the number of decisions, part of the run came from a backup model.

## Count tokens, requests and runtime

There are no run-level token or runtime totals. `summary.json` reports request
counts only (for example `observed_network_calls`). Each request has its own
record:

- `backend_trace.attempts[]` in each `raw/policy_*.json` file holds one entry
  per request, including failed ones, with `usage`, `elapsed_seconds` (seconds)
  and `error_class`.
- Each returned record in `provider_attempts.jsonl` keeps the complete native
  reply, which includes the provider's own usage block.

To total them, add up the usage fields over all attempts, including failed
attempts and backup-profile attempts. Field names and token definitions differ
by provider (Ollama reports `prompt_eval_count` and `eval_count`; Gemini reports
`usageMetadata`). A provider that returns no usage block is recorded as `null`
(Ollama: an empty mapping), which is not zero. Count those attempts separately
instead of adding zero.

## Response validation, physics and audit

| Check | Role | Effect on another model request |
|---|---|---|
| Response validation | Accept only the required fields, types, units and completed reply. | An eligible invalid reply can retry within `max_attempts`. |
| Reservoir physics | Apply available water and release limits; calculate spill and storage. | Does not resample an operating decision. |
| Operation audit | Evaluate the configured operating criterion. | Records the outcome; does not resample. |

Audit verdicts are `PASS`, `FAIL`, `WARN` or `UNKNOWN`. `UNKNOWN` means that an
applicable check or required evidence is missing. These verdicts describe the
selected criterion; they do not establish overall operation quality. An audit
FAIL or WARN is diagnostic: it does not change the run status, the exit code or
the PASS from `verify`, which checks record integrity and water balance.

## Read post-routing outcome checks

An optional `outcome_audit.jsonl` evaluates flow at a control point after routing.
It records the node, bounds, flow, decision references and verdict. A bound may
come from information selected for that decision; missing optional information
produces `UNKNOWN`. This check records downstream conditions without changing
release or assigning causal blame to one reservoir.

Keep the complete run, including raw replies, failed attempts and source hashes.
If writing these records fails, execution stops. See
[Troubleshooting](TROUBLESHOOTING.md) and [Run and resume](RUNNING.md).
