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
```
