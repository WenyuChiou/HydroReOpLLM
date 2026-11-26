# Run, verify, and resume

<div class="hero-band" markdown="1">

Every HydroReOpLLM experiment uses one CLI workflow: `check` → (`prepare` for coupled HydroCNHS) → `run` → `verify` (plus `resume` for interrupted live runs).

</div>

<figure class="figure-card">
  <img src="assets/simulation-stages.png" alt="Daily workflow from configuration through check, prepare, run, and verify">
  <figcaption><strong>Simulation lifecycle.</strong> Validate inputs offline, optionally inspect HydroCNHS inflows, run operators, and verify water balance.</figcaption>
</figure>

## CLI lifecycle and output layout

```powershell
reservoir-experiment check path/to/experiment.yaml
reservoir-experiment run path/to/experiment.yaml
reservoir-experiment verify path/to/output
```

| Subcommand | Purpose |
| --- | --- |
| `check <config>` | Validates hydrology, topology, dates, prompts, and Day-1 prompt previews. |
| `prepare <config>` | Coupled HydroCNHS only: runs catchment model + warm-up and saves `inflows.csv`. |
| `run <config> [--allow-network]` | Prepares inflows (if coupled), runs reservoir operators + routing, and writes results. |
| `verify <output> [--require-offline]` | Checks mass conservation, routing, timestamp ordering, and complete decision logs. |
| `resume <config> --from-run ... --output ... --run-id ...` | Replays completed steps from an interrupted run and finishes remaining steps. |

| Entry style | Configured `output` | Operation results | Verify command |
| --- | --- | --- | --- |
| Coupled HydroCNHS (`v1`/`v2`) | Preparation folder (`inflows.csv`, `hydrology*.json`) | `<output>/operation/` | `reservoir-experiment verify <output>` |
| Prepared inflows (`v1`/`v2`) | Operation folder | `<output>/` | `reservoir-experiment verify <output>` |

<div class="callout callout-info" markdown="1">

**Inspecting inflows before LLM runs.** Run `prepare` first to plot or gauge-check `inflows.csv`; a subsequent `run` reuses those prepared inflows automatically without re-running HydroCNHS.

</div>

## Live model calls and safety gates

Live LLM inference requires three explicit safeguards:

1. **CLI flag**: Pass `--allow-network` to `reservoir-experiment run` (or `resume`).
2. **Case readiness**: Real or simulated-inflow cases must set `"live_readiness": {"ready": true}` in `case.json` / `reservoirs.yaml` (synthetic fixtures are ready automatically).
3. **Call budget**: Set `max_calls` to at least `llm_agents * steps` (plus retry/fallback headroom) or `null`.

## Resume an interrupted operation

Keep the partial output folder untouched and resume into a fresh `--output` folder with a new `--run-id`:

```powershell
reservoir-experiment resume path/to/experiment.yaml `
  --from-run path/to/partial-operation `
  --output path/to/new-operation `
  --run-id NEW_RUN_ID
```

Completed steps replay without re-querying the LLM; add `--allow-network` only when remaining steps require new model calls.

## Replay saved daily responses

```powershell
llm-reservoir-daily --case-root path/to/case-directory `
  --case case.json `
  --responses responses.json `
  --output runs/replay
reservoir-experiment verify runs/replay --require-offline
```

To reproduce the F.E. Walter paper benchmark offline, run `python examples/fe_walter/study/replay.py --output runs/walter-paper-replay` ([F.E. Walter Dam](../examples/fe_walter/README.md)). Continue with [Reading results](RESULTS_GUIDE.md).
