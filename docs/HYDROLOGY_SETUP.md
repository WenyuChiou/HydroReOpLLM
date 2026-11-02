# Hydrology setup

Prepare and accept hydrology before comparing reservoir operators. Supply an
agent-free native HydroCNHS model, its complete forcing period, and an explicit
mapping from native flows to operation network nodes. Basin delineation,
parameter estimation, calibration, and validation remain user work.

Download [hydrology.yaml](../templates/coupled/hydrology.yaml) or browse the
[complete template folder](TEMPLATES.md).

## Connect a model to the operation network

The complete [two-reservoir teaching example](MULTI_RESERVOIR.md) provides filled
files. Its native model contains `basin_a` and `basin_b`; their local runoff is
bound to `inlet_a` and `inlet_b`. The physical network connects these inlet IDs
to `lake_a` and `lake_b`. The two `river_*` nodes add no local runoff.

```{literalinclude} ../examples/multiple_reservoirs/hydrology.yaml
:language: yaml
```

The corresponding forcing begins as follows. Precipitation is mm/day,
temperature is °C, and PET is cm/day. Each basin needs one row per model day.
The invented values below teach the format; replace them with your accepted
basin inputs for a real study.

```{literalinclude} ../examples/multiple_reservoirs/forcing.csv
:language: text
:lines: 1-5
```

Keep [model.yaml](../examples/multiple_reservoirs/model.yaml),
[forcing.csv](../examples/multiple_reservoirs/forcing.csv) and
[reservoirs.yaml](../examples/multiple_reservoirs/reservoirs.yaml) together.
Use `runoff` for a local catchment contribution and `routed` for a native routed
outlet. A downstream reservoir already receives upstream releases through the
water network; do not add that same water again as local inflow.

## Configure your own hydrology file

```{literalinclude} ../templates/coupled/hydrology.yaml
:language: yaml
```

| Field | Purpose and units | Required? | User-filled or referenced value |
|---|---|---|---|
| `model` | Complete native HydroCNHS model | Required | Path to user-owned accepted YAML |
| `forcing` | Daily weather table | Required | Path to user-owned CSV or CSV.gz |
| `zero_flow_nodes` | Native nodes with zero assigned local flow; upstream routed contributions remain | Optional; default empty | Native outlet IDs |
| `inflow_bindings` | One local boundary for every operation node | Required | Mapping keyed by network node ID |
| `runoff` | Local runoff before native routing | One binding choice | Native weather driven unit ID |
| `routed` | Native routed outlet flow | One binding choice | Native routing outlet ID |
| `constant` | Explicit absence of added lateral flow | One binding choice | Only `0` is accepted |
| `prepared_from` | Reuse a verified matching preparation | Optional | Existing preparation directory |

After viewing the complete file, `hydrology.model` can be used as shorthand for
the `model` key inside this section. It is a configuration position containing
a path, not a function.

The native `WaterSystem` dates define the continuous hydrology period. The
operation window in `experiment.yaml` must lie inside it. Keep the warm-up days
and accepted parameters in the native file. The current entry accepts GWLF or
ABCD rainfall-runoff with Lohmann routing and rejects native ABM agents so
reservoir control is not applied twice.

The forcing columns and units are listed in [Configuration overview](INPUT_OUTPUT.md).
Each weather driven `(subbasin_id, date)` pair must appear exactly once. Bind
each catchment contribution once: a downstream node receives upstream reservoir
outflow through `network.connections`, so its local binding contains only
additional lateral water.

For an aggregation outlet, zero local input means that the node adds no runoff
of its own. It can still receive and route water from upstream subcatchments;
the `routed` binding returns that upstream total.

See the [HydroCNHS manual](https://cylin928.github.io/HydroCNHS/) for native model
construction and calibration. Continue with [reservoirs and the water network](BUILD_SIMULATION.md).
