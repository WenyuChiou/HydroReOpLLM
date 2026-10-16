# Running and maintenance

Start with the saved examples. Before a new model run, check the configuration,
available resources and output path. This page describes the current runner;
automatic retry, checkpoint restore and policy fallback are not provided.

## 1. Plan CPU, GPU and memory

| Work | Where it runs | What to check |
|---|---|---|
| Hydrology, reservoir accounting and routing | Python host / CPU | Catchment and network size; host memory and step duration |
| Prompt construction, checks, audit and trace | Python host / CPU | Prompt/history size and disk writes |
| Local LLM inference | Ollama process | Loaded model, CPU/GPU placement, RAM/VRAM and response duration |
| Remote LLM inference | Provider service | Request latency, call allowance and available usage/cost records |

A GPU is not required to read results or build the manual. The inference
provider determines whether a local model uses CPU, GPU or both.
`ollama ps` lists already loaded models and their processor placement; it does
not request a generation. See the [Ollama FAQ](https://docs.ollama.com/faq).

Hardware requirements depend on the model, context and network. The three-day
tutorial is not a CPU/GPU benchmark. Inspect host and provider processes
separately in your system monitor before choosing a longer experiment.

## 2. Bound a new experiment

| Setting | Purpose |
|---|---|
| `start_date`, `end_date` | Inclusive daily interval within the case's continuous input |
| `max_calls` | At least days × LLM agents; request allowance, not a cost or memory limit |
| `max_tokens` | Positive response-length limit; too small can yield an incomplete reply |
| `timeout_seconds` | Single-request timeout; timeout stops execution without retry |
| Information profile | Select fields/history actually needed by the prompt |

Keep temperature **0.7** for these examples. A new start date needs verified
initial reservoir and routing state; it does not inherit an earlier run.
Agent count does not by itself establish parallel inference.
Full controls and defaults are in the [parameter reference](PARAMETER_REFERENCE.md).
Provider concurrency and context limits are provider settings, not extra
HydroOpsLLM YAML fields.

## 3. Reserve storage and preserve evidence

Store inputs, model files and run outputs separately. Reserve space for:

- The environment, input bundle and local model files.
- Per-decision messages, raw replies, proposals, audit and physics/feedback records.
- Reservoir and routing tables, summaries, backups and figures.

Measure a representative **completed** run directory and extrapolate cautiously
to the planned days and agents. Prompt/history growth can make output size
nonlinear. No fixed GB-per-year claim has been validated.

Keep the full run directory and its YAML, case, source hashes and prompt/knowledge
versions together. Do not prune `raw/` to make a run appear complete.
The original notebook downloads and saved results are evidence, not caches.

Ollama manages model storage separately; consult its
[storage documentation](https://docs.ollama.com/faq#where-are-models-stored)
before moving model files.

## 4. If execution is interrupted

1. **Confirm the process has stopped.** Check its command line before launching
   another run.
2. **Preserve the output directory.** Copy it for diagnosis; retain the failed or
   partial records and original configuration.
3. **Verify existing evidence.** Run `verify` against that directory. A missing
   summary, truncated file or failed binding is incomplete evidence, not a pass.
4. **Find the last fully committed transition.** Match the decision, audit,
   physics and feedback records. A raw reply alone does not prove release was
   applied.
5. **Resolve the cause before another experiment.** Use a new run ID/output.
   Do not overwrite the interrupted run or rerun completed dates as recovery.

A timeout or lost connection can leave the provider outcome and cost unknown.
A system crash can leave a partial record. Preserve uncertainty; do not infer
success from a returned fragment.

**This runner has no general resume command.** Continuing from a later date
requires an explicitly reviewed reconstruction of reservoir storage, routing
memory and agent history. Changing only `start_date` is not a recovery method.

## 5. Checks, fallback and outcome

| Event | Current behavior |
|---|---|
| Incomplete reply, invalid schema/unit/value or provider error | Stop before applying that proposal; no automatic retry |
| Valid requested release exceeds feasible water/limits | Common physical calculation determines implemented release and spill |
| Operation audit FAIL/WARN/UNKNOWN | Preserve the diagnostic verdict; it is not a silent replacement policy |
| Storage/process failure or incomplete evidence | Preserve partial files; diagnose before another run |

Physical clipping is not a fallback operating policy. To compare a rule policy
with an LLM, select it as a separate experiment with the same verified inputs.
An automatic emergency policy would need an explicit, tested contract and
traceable activation; it is not a current configuration option.

Continue with [results and audit/trace](RESULTS_GUIDE.md) or
[troubleshooting](USER_GUIDE.md#troubleshooting).
