# Read your results

Open `<output>/operation/summary.json` first. It identifies the run, completion
status and the records to inspect. For prepared-inflow workflows, use the
operation output directory specified by that experiment.

## Check water and storage

| File | What to look at | Units |
|---|---|---|
| `reservoir_trajectory.csv` | Inflow, requested release, actual controlled release, spill and storage | m³/s; storage in m³ |
| `network_flows.csv` | Flow at reservoirs and downstream nodes | m³/s |
| `network_balance.csv` | Water-balance residual across the network | m³ |

**Controlled release** passes through the outlet. **Spill** is calculated
separately. Routing receives their sum. Requested release may differ from actual
controlled release when available water or physical limits constrain the request.

Convert storage to elevation with your reservoir's storage–elevation curve.
Label figure units: FE Walter displays use feet for elevation and cfs for flow,
while the framework stores volumes in m³ and flows in m³/s.

## Verify a completed run

```bash
reservoir-experiment verify <output>/operation
```

For a prepared-inflow run, replace the path with its operation output directory.
Check complete dates, water balance and the intended initial state and parameters
before comparing operators. Verification establishes record consistency, not
whether the operator meets seasonal or flood-management goals.

## Explain a decision

Match a change in the trajectory to its decision ID. Read the rendered prompt,
raw reply, requested release, physical result and operation audit together.
[Decision records](RECORDS.md) explains the fields, runtime and token logs.

For each reservoir, compare elevation and release first; use downstream flow to
see the routed outcome. Keep individual runs available when displaying a median
or uncertainty band.

Continue to [complete examples](CASE_STUDIES.md), or use
[troubleshooting](TROUBLESHOOTING.md) to investigate an incomplete run or a target miss.
