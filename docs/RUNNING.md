# Run, recover, and plan resources

Use the generic four-day coupled fixture before a case study or long provider
run. Keep one experiment YAML for `check`, `prepare`, and `run`, and verify the
operation directory produced by that YAML.

## Run the generic coupled fixture

From the repository root, run the rule-based path first:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule/operation
```

The top-level YAML sets `output: ../../runs/independent-rivers-rule`. For a
coupled experiment, preparation evidence is stored under that output root and
daily operation evidence is stored in its `operation/` directory. The current
verification target is therefore:

```text
runs/independent-rivers-rule/operation
```

Expected success is four completed dates, 2020-02-28 through 2020-03-02, plus a
successful verification of links, hashes, and water accounting. Read
`runs/independent-rivers-rule/operation/summary.json` next.

After the rule path succeeds, configure the `local` model profile and run the LLM
variant deliberately:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.llm.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.llm.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.llm.yaml --allow-network
reservoir-experiment verify runs/independent-rivers-mixed/operation
```

Only the LLM `run` command needs `--allow-network`. `check` validates references
without running hydrology or a provider. `prepare` runs hydrology and makes zero
model requests.

Some older supplied-inflow examples write operation files directly at the
configured output root because they do not have a separate coupled preparation
stage. For those examples, use the output path documented by that example. Do
not remove or add `/operation` by analogy; inspect the entry type and resolved
output path.

## Bound a new experiment

| Setting | Purpose |
|---|---|
| `start_date`, `end_date` | Inclusive operation interval within continuous case inputs |
| `max_calls` | Integer total request allowance, or explicit `null` for no total cap; retries count |
| `max_tokens` | Positive response limit; a small value can truncate a reply |
| `timeout_seconds` | Timeout for one provider attempt |
| `max_attempts` | Maximum attempts for one decision and one profile; default `1` |
| `retry_delay_seconds` | Delay between eligible retries; default `2` seconds |
| Information profile | Fields and history available when the decision is made |

The examples use temperature **0.7**. A new start date requires verified initial
reservoir and routing state; it does not inherit state from another run. Agent
count does not establish parallel inference. Provider concurrency and context
limits are service settings, not extra HydroOpsLLM YAML fields.

## Plan CPU, GPU, memory, and storage

| Work | Where it runs | What to check |
|---|---|---|
| Hydrology, reservoir accounting, routing | Python host / CPU | Network size, host memory, step duration |
| Prompt construction, checks, audit, trace | Python host / CPU | Prompt/history size and disk writes |
| Local LLM inference | Local provider process | Loaded model, CPU/GPU placement, RAM/VRAM, response duration |
| Remote LLM inference | Provider service | Latency, call allowance, available usage and cost records |

A GPU is not required to prepare hydrology, run rule agents, read results, or
build the manual. The inference service determines local CPU/GPU use. `ollama ps`
shows loaded models and processor placement without requesting a generation.
See the [Ollama FAQ](https://docs.ollama.com/faq).

The four-day fixture is not a hardware benchmark. Measure a representative
completed run before extending the period. Prompt and history growth can make
storage nonlinear; no fixed GB-per-year estimate has been validated.

Retain inputs, model files, and run outputs separately. Keep the complete run
directory with configuration, case, source hashes, prompt and knowledge
versions, decisions, raw replies, provider attempts, physics, routing, audits,
backups, and figures. Do not prune `raw/` to make a run appear complete.

## Resume an interrupted run

1. Confirm the original process stopped.
2. Preserve the partial output and original configuration.
3. Compare `backend_events.jsonl`, `provider_attempts.jsonl`, and the last
   decision and physics records. A raw reply alone does not prove release was
   applied.
4. Resume unchanged inputs into a new output directory.
5. Verify the new operation directory and retain the source run beside it.

For the coupled fixture, `--from-run` points to the source `operation/` directory:

```powershell
reservoir-experiment resume examples/multiple_reservoirs/experiment.yaml `
  --from-run runs/interrupted/operation `
  --output runs/continued `
  --run-id continued
reservoir-experiment verify runs/continued
```

`resume --output` is the operation output itself, so the verification target in
this command is `runs/continued`, without another `/operation` suffix. Add
`--allow-network` only when unfinished LLM decisions require new requests.

Resume verifies and replays the **committed history**: completed days already
saved with their decisions, physical transitions, and evidence. It skips those
decisions and reuses captured replies and custom context where available. It
does not overwrite the source run.

Recovery rejects changed inputs, prompts, model settings, code, or Python
version. It supports static case information. Dynamic external information
extensions require a durable replay contract and are rejected without one. A
finite call allowance includes attempts from the source run.

An in-flight request without a journaled decision can be sent again. A timeout
or crash can leave provider outcome and cost unknown. Preserve that uncertainty;
the external service cannot be guaranteed to receive a request exactly once.

## Interpret retries, fallback, and outcomes

| Event | Current behavior |
|---|---|
| Incomplete reply or invalid fields | Retry within the selected profile's `max_attempts`; do not advance physics |
| Timeout or eligible connection/HTTP failure | Retry within the same profile and retain failed attempts |
| Exhausted eligible attempts | Try ordered `customization.fallback_models`, when configured |
| Authentication/configuration error or evidence-write failure | Stop and preserve diagnostics |
| Requested release exceeds feasible water or limits | Apply the common physical calculation and record implemented release and spill |
| Operation audit FAIL/WARN/UNKNOWN | Preserve the diagnostic; do not regenerate or replace the action |

Physical clipping is not a fallback operating policy. Compare a rule policy and
an LLM in separate experiments with the same verified inputs. An emergency
policy would require an explicit, tested, traceable contract; it is not a current
configuration option.

Continue with [Results, audit, and trace](RESULTS_GUIDE.md) or
[Troubleshooting](USER_GUIDE.md#troubleshooting).
