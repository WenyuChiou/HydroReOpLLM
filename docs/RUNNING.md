# Run lifecycle

Run commands from the repository root.

```powershell
reservoir-experiment check path/to/experiment.yaml
reservoir-experiment prepare path/to/experiment.yaml
reservoir-experiment run path/to/experiment.yaml
reservoir-experiment verify path/to/output
```

`check` loads references and validates settings without hydrology execution or a
provider request. `prepare` writes coupled hydrology products. `run` writes a new
experiment directory. `verify` reads saved evidence; add `--require-offline` when
the acceptance condition is zero provider calls.

For a completed coupled run, pass its output directory. For the bundled
two-reservoir example, use `reservoir-experiment verify runs/independent-rivers-rule --require-offline`.
Use the `operation/` subdirectory to verify the reservoir operation on its own.
A directory produced by `prepare` is ready for `run` once hydrology preparation
succeeds. Verification of the operation requires a completed simulation.

Live LLM transport requires both an LLM operator and the explicit
`reservoir-experiment run ... --allow-network` flag. `max_calls` bounds total
provider attempts when it is an integer; retries count toward that limit.

## Resume

Preserve the interrupted output and resume into a distinct directory:

```powershell
reservoir-experiment resume path/to/experiment.yaml `
  --from-run path/to/partial-output `
  --output path/to/new-output `
  --run-id NEW_RUN_ID
```

Add `--allow-network` only when new provider calls are intended. Reuse is
accepted only when the saved prefix matches the current settings and runtime.

## Replay saved daily responses

For a daily case with an existing response file, use the installed offline
replay command. Supply both input paths relative to the case directory and
choose a new output directory.

```powershell
llm-reservoir-daily --case-root path/to/case-directory --case case.json --responses responses.json --output runs/replay
reservoir-experiment verify runs/replay --require-offline
```

For responses labeled `recorded_llm_response`, strict verification checks the
saved source digest against the decision and audit records, matches each raw
response to its date and requested release, and requires zero observed provider
calls during replay. Keep the original response file if you also want to compare
its bytes with the saved SHA-256 digest.
