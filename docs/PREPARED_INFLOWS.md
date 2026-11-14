# Prepared inflows

Use this route when you already have local inflow series for each reservoir and
do not want HydroReOpLLM to run a HydroCNHS model. The inflows can come from a
hydrological model you ran earlier, from gauges or from a synthetic test. The
reservoir physics, operators, records and `verify` are the same as in the coupled
route; only the source of inflow differs.

Use the [coupled route](DAILY_WORKFLOW.md#choose-the-input-route) instead when
you want weather to drive a HydroCNHS model and be prepared by the package.

## What you provide

- A table of local inflow in m³/s for every routing node and every operation day.
  Local inflow is the runoff added at that node. Do not repeat upstream release
  or spill in a downstream node; the network routes it.
- A physical case: reservoir capacities, release limits, initial storage and the
  water connections (see [Reservoirs and network](BUILD_SIMULATION.md)).
- One operator per controlled reservoir, as in [Operators and prompts](CONFIGURATION.md).

Copy the whole [prepared-inflow template](../templates/prepared/README.md) folder
and replace its invented values. Its README lists every file and field, so this
page does not repeat them. A complete working example with invented inflows and
no model service is [examples/daily_offline](../examples/daily_offline/README.md).

## Check, run, verify

Replace `study` with your copy of the template folder:

```shell
reservoir-experiment check study/experiment.yaml
reservoir-experiment run study/experiment.yaml
reservoir-experiment verify <the folder named by output in experiment.yaml>
```

There is no `prepare` step. `check` reads and validates the files without
running a model; `run` writes the results into the `output` folder, which must
not exist yet; `verify` reads the saved records and checks them. Use a new
`run_id` and `output` for every experiment.

For an LLM operator, `run` also needs `--allow-network`, a `max_calls` that
covers the planned requests, and a case that declares `live_readiness` (unless
its `data_kind` is `synthetic_fixture`, as in the template). See
[Check and run](RUNNING.md) and [Before a new LLM experiment](LIVE_READINESS.md).

## What to keep in mind

- `experiment.start_date` and `end_date` can select any sub-range of the inflow
  record. The case's `initial_storage_m3` applies on the first operated day.
- Every operator is given that day's own mean inflow. See
  [Timing of the current inflow](INFORMATION.md#timing-of-the-current-inflow).
- Your inflows are your own input. The package checks that the files are
  consistent and that water balances; it does not check that the inflows are
  realistic. Read the results as described in [Results](RESULTS_GUIDE.md).
