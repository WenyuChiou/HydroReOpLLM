# MOSART-Urban flood-control rule

This bundled rule uses the normal operator, physics, routing, auditing, and
output interfaces. It is intended for deterministic comparison with the other
synthetic operators in this repository.

| Setting | Behavior |
|---|---|
| Annual coefficient | Beginning storage at January 1; held until the next year |
| First operation step | Uses configured initial storage as the first snapshot |
| Alpha | 0.85 by default, used in the release coefficient and storage ceiling |
| High storage | Releases volume above alpha times physical capacity |
| Environmental release | 10% of the configured historical mean inflow |
| Time and purpose | Daily flood control teaching fixture |

Physical capacity stays unchanged; the 85% ceiling belongs to the rule. A
configuration whose host release or protected-storage limits conflict with the
rule stops before the controller advances.

## Run the synthetic examples

| Example | Configuration |
|---|---|
| Single reservoir with prepared inflows | `examples/daily_offline/single.mosart.yaml` |
| Multiple reservoirs with hydrology | `examples/multiple_reservoirs/experiment.mosart.yaml` |

```powershell
reservoir-experiment check examples/daily_offline/single.mosart.yaml
reservoir-experiment run examples/daily_offline/single.mosart.yaml
reservoir-experiment verify runs/daily-single-mosart --require-offline
```

Use a new run ID and output path before repeating a run. These examples make no
model request and demonstrate software integration; they do not establish
hydrological calibration or the real-world skill of an operating policy.
