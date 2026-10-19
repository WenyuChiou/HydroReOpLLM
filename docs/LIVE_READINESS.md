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

The FE Walter example assumes initial storage of 2,457,848.279729185 m³,
zero reservoir losses and identity downstream routing. Its retained prompt
reports 110,700 acre-ft capacity, while the physical profile uses 109,878 acre-ft;
this source discrepancy is preserved for case reproduction. Its approved
seasonal targets are in the [current tutorial](../tutorials/README.md).

Valid replies and balanced water do not establish effective operation. Eligible
request/reply failures use the configured retry limit. Operation-target misses
are recorded without resampling. Follow [Configure agents](CONFIGURATION.md),
[Run and resume](RUNNING.md) and [Troubleshooting](TROUBLESHOOTING.md).
