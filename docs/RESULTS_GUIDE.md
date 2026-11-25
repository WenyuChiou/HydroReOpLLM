# Read your results

Open `summary.json` first. In a coupled run it is under `<output>/operation/`;
in a prepared-inflow run it is directly under `<output>/`. Confirm `status` is
`COMPLETED`, then inspect the files named below rather than treating command
exit alone as an operating-performance result.

![Output directory structure and relationships across CSV and JSONL result files](assets/diagrams/results-outputs-map.svg)

- **Output root**: prepared-inflow runs write directly to `<output>/`, whereas coupled runs place hydrology prep in `<output>/` and operation results in `<output>/operation/`.
- **Summary & CSVs**: check `status == "COMPLETED"` in `summary.json`, then inspect `reservoir_trajectory.csv`, `network_flows.csv`, and `network_balance.csv`.
- **Trace & verify**: `decisions.jsonl`, `physics.jsonl`, `audit.jsonl`, and `raw/` record step-level provenance for `reservoir-experiment verify`.

## Physical and routed results

| File | Main fields | Meaning |
|---|---|---|
| `reservoir_trajectory.csv` | timestamp/date, reservoir ID, inflow, target and controlled release, spill, start/end storage, adjustments | One physical transition per reservoir and step. |
| `network_flows.csv` | timestamp/date, node, `local_inflow_cms`, `routed_flow_cms` | Local input and total routed flow at every network node. |
| `network_balance.csv` | local input, outlet output, storage/channel changes, residual | Integrated network water balance in m3. |
| `reach_volume_trace.json` | delayed reach volumes | Water held in routing lags between steps. |

Flows are interval-mean m3/s; storage and balance terms are m3. The requested
or target release is the operator's action. `controlled_release_cms` is the
physically applied outlet release after bounds and available water are enforced.
`spill_cms` is separate. Routing receives controlled release plus spill.
Therefore a clipped request is a recorded adjustment, not automatically a run
failure.

For plots, compare storage (or elevation after applying a study-specific
storage-elevation curve), controlled release, spill, and downstream routed flow.
Keep units and interval labels explicit. Normalize timestamp spelling before
joining tables if one file uses a full timestamp and another uses a date.

## Decision and audit evidence

| File or folder | Read it for |
|---|---|
| `decisions.jsonl` | observation, selected decision information, action, decision/request IDs, and serving profile. |
| `physics.jsonl` | the observation/action bound to the resulting transition. |
| `audit.jsonl` | per-decision auditor PASS, WARN, FAIL, or UNKNOWN findings. |
| `backend_events.jsonl` | decision lifecycle and request-attempt linkage. |
| `provider_attempts.jsonl` | provider attempts when a model transport was used. |
| `raw/` | saved prompt/policy/reply payloads referenced by trace records. |
| `experiment.json` | frozen network, inputs, implementation identities, information catalog, and provenance. |

Use `decision_id` to join a decision, its physical transition, audit, and raw
references. If `summary.json` reports `fallback_used: true`, inspect
`serving_profiles` and the successful attempt before attributing the decision to
the primary model. Auditor findings are diagnostic: a run can be internally
consistent and still contain WARN or FAIL findings or miss an operating goal.

## Verify saved evidence

```powershell
reservoir-experiment verify path/to/output --require-offline
```

Omit `--require-offline` when provider calls were intended. Verification checks
saved hashes, complete causal trace sequences, physical transitions, routing,
water balance, selected information, and declared offline evidence. It does not
rerun hydrology or an operator, and it leaves operating-strategy acceptance
unknown. For a coupled run, the command accepts either the preparation root or
its completed `operation/` directory.

If verification fails, preserve the output and follow
[troubleshooting](TROUBLESHOOTING.md). If it passes, report the verification
result separately from hydrologic calibration, policy skill, or study-specific
performance.
