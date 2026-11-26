# Check, prepare, run, and verify

<div class="hero-band" markdown="1">

Every HydroReOpLLM experiment follows one reproducible CLI lifecycle (`src/llm_reservoir_agent/workflow.py`): `check` → (`prepare` for coupled HydroCNHS) → `run` → `verify` (plus `resume` for interrupted runs).

</div>

<figure class="figure-card">
  <img src="assets/simulation-stages.png" alt="Daily workflow from configuration through check, prepare, run, and verify">
  <figcaption><strong>Workflow lifecycle.</strong> Validation, optional hydrology preparation, bounded execution, and independent verification share pinned source hashes.</figcaption>
</figure>

## CLI lifecycle and output layout

Run the shortest sequence from the repository root (or exported examples directory):

```powershell
reservoir-experiment check path/to/experiment.yaml
reservoir-experiment run path/to/experiment.yaml
reservoir-experiment verify path/to/output
```

| Subcommand | Role | Writes output? | Network calls |
| --- | --- | --- | --- |
| `check <config>` | Validates schemas, SHA-256 pins, bindings, and builds offline Day-0 prompt previews. | No | `0` |
| `prepare <config>` | Coupled only (`hydroops-coupled-simulation.v1/.v2`): runs HydroCNHS hydrology + warm-up and pins `inflows.csv`. | Preparation dir | `0` |
| `run <config> [--allow-network]` | Prepares (if coupled and needed), runs reservoir agents + routing, and writes durable journals. | Fresh `<output>` | `0` unless `--allow-network` |
| `verify <output> [--require-offline]` | Checks hashes, causal trace sequences, water balance, routing, and selected information. | No | `0` |
| `resume <config> --from-run ... --output ... --run-id ...` | Replays unchanged prefix from an interrupted run into a fresh directory. | Fresh `--output` | Only for uncompleted steps |

The output directory structure depends on the entry schema:

| Input style | Configured `output` | Operation records | Verify target |
| --- | --- | --- | --- |
| Coupled HydroCNHS (`v1`/`v2`) | Preparation directory (`inflows.csv`, `preparation.json`) | `<output>/operation/` | `reservoir-experiment verify <output>` (or `<output>/operation`) |
| Prepared inflows (`v1`/`v2`) | Operation directory | `<output>/` | `reservoir-experiment verify <output>` |

<div class="callout callout-info" markdown="1">

**Preparation reuse.** If you run `prepare` first and inspect `inflows.csv`, a subsequent `run` validates `preparation.json` (`hydrology_signature` and file SHA-256 checksums) and skips recomputing HydroCNHS runoff. A preparation directory is not a completed simulation until `operation/summary.json` has `status: "COMPLETED"`.

</div>

## Live model calls and safety gates

Live LLM inference requires **three** explicit conditions (`_live_gate_message` in `workflow.py`):

1. **CLI flag**: Pass `--allow-network` to `reservoir-experiment run` (or `resume`).
2. **Case readiness**: Non-synthetic cases (`observed_local_inflow` or `simulated_local_inflow`) must declare `"live_readiness": {"ready": true}` in `case.json` / `reservoirs.yaml`. (`synthetic_fixture` cases are ready without it.)
3. **Budget cap (`max_calls`)**: Must be an integer covering `llm_agent_count * steps` (or explicit `null`). Every primary attempt, retry (`max_attempts`), and `fallback_models` attempt reserves a `STARTED` entry in `provider_attempts.jsonl` before sending.

## Resume an interrupted operation

Never delete or mutate a failed run directory. Point `resume` at the interrupted run (`--from-run`) with a fresh `--output` and `--run-id`:

```powershell
reservoir-experiment resume path/to/experiment.yaml `
  --from-run path/to/partial-operation `
  --output path/to/new-operation `
  --run-id NEW_RUN_ID
```

`RecoveryTape` (`src/llm_reservoir_agent/recovery.py`) requires exact matches on package code, HydroCNHS core pins, Python version, network, and inflows. It replays saved replies and context, reconstructs physics identically, and inherits prior `STARTED` attempt reservations against `max_calls`. Add `--allow-network` only if remaining steps require new LLM calls.

## Replay saved daily responses

Replay archived daily releases (`recorded_llm_response`) offline through the host physics and routing engine:

```powershell
llm-reservoir-daily --case-root path/to/case-directory `
  --case case.json `
  --responses responses.json `
  --output runs/replay
reservoir-experiment verify runs/replay --require-offline
```

For the F.E. Walter 21-run benchmark reproduction, use `python examples/fe_walter/study/replay.py --output runs/walter-paper-replay` (see [F.E. Walter Dam guide](../examples/fe_walter/README.md)). Continue with [Read your results](RESULTS_GUIDE.md).
