# Before a new LLM experiment

The tutorial reads saved annual results. To create a new run, check the model
profile and study assumptions before enabling provider requests.

| Check | What to confirm |
|---|---|
| Hydrology | Accepted model, forcing, warm-up, calibration/validation evidence and inlet mapping. |
| Initial state | Dated storage and routing state, or explicitly justified assumptions. |
| Reservoir physics | Capacity, dead storage, release limits and the elevation–storage curve. |
| Routing | Appropriate travel time and reach parameters; an identity hydrograph tests connectivity only. |
| Prompt and knowledge | Applicable operating targets, information availability, units and response schema. |
| Model profile | Exact provider/model, supported options, finite retries and credentials in environment variables. |
| Comparison | Same water inputs and initial physical state; explicit performance criteria and stochastic design. |
| Records | New run/output IDs and sufficient space for prompts, replies and failed attempts. |

## The live-run gate

`run` refuses an LLM experiment unless all of these hold:

- the command includes `--allow-network`;
- `max_calls` covers the planned requests (a positive integer at least the
  number of LLM decisions, or `null` for no cap); and
- the physical case file declares the case live-ready:

```yaml
live_readiness:
  ready: true
  notes: ["Why this setup is accepted for live requests."]
```

`live_readiness` is a top-level key next to `data_kind` in the physical case
(`reservoirs.yaml` or the case JSON). `notes` is optional. Only a case whose
`data_kind` is `synthetic_fixture` is ready without it. Setting `ready: true` is
your statement that the table above has been checked; the software does not
verify it. `check` shows `live_ready` in its report.

The automated tests use local HTTP fixtures and have not exercised a real
provider service, so first test a new provider and model on a short period.

The FE Walter example assumes initial storage of 2,457,848.279729185 m³,
zero reservoir losses and identity downstream routing. Its retained prompt
reports 110,700 acre-ft capacity, while the physical profile uses 109,878 acre-ft;
this source discrepancy is preserved for case reproduction. Its approved
seasonal targets are in the [current tutorial](../tutorials/README.md).

Valid replies and balanced water do not establish effective operation. Eligible
request/reply failures use the configured retry limit. Operation-target misses
are recorded without resampling. Follow [Configure agents](CONFIGURATION.md),
[Run and resume](RUNNING.md) and [Troubleshooting](TROUBLESHOOTING.md).
