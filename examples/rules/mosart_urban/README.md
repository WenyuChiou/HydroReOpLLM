# MOSART-Urban flood-control rule

This shared extension follows the reservoir-operation equations in
[MOSART-Urban commit 7883c5c](https://github.com/RiverAI-Project/MOSART-Urban/tree/7883c5cac62e8c0c585fbafbb1045118cad2dd42).
It uses the normal operator, physics, routing, auditing and output interfaces.
The original Hanasaki extension remains available under its existing ID.

| Setting | MOSART-Urban behavior |
|---|---|
| Annual coefficient | Beginning storage at January 1; held until the next year |
| First operation step | Uses the configured initial storage as the first snapshot |
| Alpha | 0.85 by default, used in the release coefficient and storage ceiling |
| High storage | Releases the volume above alpha times physical capacity |
| Low storage | Applies the source's negative-storage and 10% capacity branches |
| Environmental release | 10% of historical mean inflow before storage regulation |
| Outlet limit | Upstream has no separate maximum; conflicting host limits raise an error |
| Time and purpose | Daily flood control |

Physical capacity stays at its original value. The 85% ceiling is part of this
rule. A configuration whose minimum/maximum release or protected storage would
change the source result raises a `MOSART-Urban parity conflict` before the
controller advances. Inspect the required and host release in that error.

## Select an example

After installing the package, run these commands from the repository root.
Each entry uses a distinct run ID and output directory.

| Example | Configuration |
|---|---|
| Single reservoir with prepared inflows | `examples/daily_offline/single.mosart.yaml` |
| Multiple reservoirs with hydrology | `examples/multiple_reservoirs/experiment.mosart.yaml` |
| F.E. Walter with hydrology | `examples/fe_walter/coupled/experiment.mosart.yaml` |
| F.E. Walter with prepared 2021–2025 inflows | `examples/fe_walter/operation/experiment.mosart.yaml` |

```shell
reservoir-experiment check examples/daily_offline/single.mosart.yaml
reservoir-experiment run examples/daily_offline/single.mosart.yaml
reservoir-experiment verify runs/daily-single-mosart
```

Use the same check/run commands with the selected multi-reservoir or F.E. Walter
configuration. All entries make zero model requests. Reference statistics are
checked against their pinned source; the tiny single-reservoir example declares
its constant teaching mean explicitly.

The F.E. Walter MOSART profiles set the extra protected-storage and absolute
minimum-release limits to zero. MOSART's own low-storage regulation then applies.
They retain the original capacity, initial storage, maximum release, forcing and
routing. Existing F.E. Walter cases remain available. A later LLM comparison must
use the same physical profile for all methods.

## Check numerical parity with the original

Obtain `src/mosart_urban/reservoir_operation.py` from the pinned commit using
your authorized upstream access. The verifier requires its exact SHA256,
`ef0ea6ce834910417cc84d5f0ca8883988a1f620cb883dac476d538b4dfde510`.

```shell
python scripts/verify_mosart_rule.py --upstream-source /path/to/reservoir_operation.py --output /new/path/parity.json
```

The verifier calls the unmodified original Python functions with the JIT
decorator disabled. It compares regulation branches, randomized inputs and
three years of releases/storage through the common physical kernel. It saves
the source/candidate hashes, maximum differences and the complete trajectory.
Use a fresh output path. The upstream file is supplied separately.

This comparison isolates reservoir operation under identical inlet flows,
initial storage and historical mean. MOSART's full river solver initializes its
reservoirs to 50% capacity and keeps the initial array sample as state; align
that initialization and sample convention when comparing complete solvers.
