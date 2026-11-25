# Check, prepare, run, and verify

From the repository root, use the same configuration for `check` and `run`.
For both prepared and coupled cases, the shortest sequence is

```powershell
reservoir-experiment check path/to/experiment.yaml
reservoir-experiment run path/to/experiment.yaml
reservoir-experiment verify path/to/output
```

`check` loads references and validates settings without hydrology execution or a
provider request. To inspect the inflow before a **coupled** run, insert
`reservoir-experiment prepare path/to/experiment.yaml` between `check` and `run`.
This command runs native hydrology
and writes pinned `inflows.csv`, `case.json`, `experiment.yaml`, `hydrology.json`,
and `preparation.json` into the configured output directory. `run` performs that
preparation automatically when the output does not exist, or validates and reuses
an existing preparation. It then writes reservoir-operation records. `verify`
reads saved evidence without rerunning hydrology or an operator; add
`--require-offline` when zero provider calls is an acceptance condition.

The output layout depends on the input style:

| Input style | Configured output | Operation records | Verify command |
|---|---|---|---|
| Coupled HydroCNHS | preparation directory | `<output>/operation/` | `reservoir-experiment verify <output>` |
| Prepared inflows | operation directory | `<output>/` | `reservoir-experiment verify <output>` |

For the bundled coupled example, use:

```powershell
reservoir-experiment verify runs/independent-rivers-rule --require-offline
```

Passing `runs/independent-rivers-rule/operation` verifies only its operation
records. A preparation directory is not a completed run until
`operation/summary.json` exists with status `COMPLETED`.

## Live model calls

Live LLM transport requires an LLM operator and the explicit
`reservoir-experiment run ... --allow-network` flag. `max_calls` bounds total
provider attempts when it is an integer; retries and fallback attempts count
toward that limit. Non-synthetic physical inputs also require an explicit ready
declaration in the case. A successful `check` validates the declared plan, not
remote model availability, credentials, billing, or response quality.

## Resume an interrupted operation

Preserve the interrupted output and resume into a distinct unused directory:

```powershell
reservoir-experiment resume path/to/experiment.yaml `
  --from-run path/to/partial-operation `
  --output path/to/new-operation `
  --run-id NEW_RUN_ID
```

Add `--allow-network` only when new provider calls are intended. Reuse is
accepted only when the saved prefix matches the current settings and runtime.
The source run remains unchanged. Resume may reuse completed decisions and
captured replies, but a request interrupted in flight can have unknown provider
delivery or cost.

## Replay saved daily responses

For a daily case with an existing response file, use the installed offline
replay command. This is an interface for user-supplied saved responses; the
repository does not ship a response file. Supply both input paths relative to
the case directory and choose a new output directory.

```powershell
llm-reservoir-daily --case-root path/to/case-directory `
  --case case.json `
  --responses responses.json `
  --output runs/replay
reservoir-experiment verify runs/replay --require-offline
```

For responses labelled `recorded_llm_response`, strict verification checks the
saved source digest against the decision and audit records, matches each raw
response to its date and requested release, and requires zero observed provider
calls during replay. Keep the original response file if you also want to compare
its bytes with the saved SHA-256 digest.

Continue with [read your results](RESULTS_GUIDE.md).
