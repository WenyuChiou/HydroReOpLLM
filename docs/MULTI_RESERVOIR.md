# Multiple reservoirs

Use [`examples/multiple_reservoirs`](../examples/multiple_reservoirs/README.md)
for a complete synthetic two-reservoir network. The essential invariants are:

- every reservoir key, physical `reservoir_id`, operator assignment, and inflow
  binding is unique and consistent;
- each controlled reservoir has one operator and its own decision history;
- local inflow excludes upstream water that arrives through a connection;
- outgoing fractions from one source sum to 1;
- terminal nodes exactly match `outlets`;
- routing weights are nonnegative and sum to 1.

For prepared inflows, the CSV contains every date and node using the header
`date,node,local_inflow_cms`. For native hydrology, `inflow_bindings` map model
flows to the network's inflow nodes. Downstream nodes receive only additional
local runoff; counting upstream release in both places duplicates water.

Check the default rule-based example before selecting its LLM variant:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule --require-offline
```

The first run creates a coupled preparation at
`runs/independent-rivers-rule/` and operation records in its `operation/`
subdirectory. Read the [results guide](RESULTS_GUIDE.md) before comparing nodes.
