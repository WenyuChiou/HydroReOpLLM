# Build a weather-to-operation simulation

Build the simulation in three layers: accept the hydrology and complete weather
record, define the reservoir and river network, then choose a rule or LLM decision
method. The supported entry point is one `hydroops-coupled-simulation.v1` YAML.

The execution has **two stages**. Preparation first runs native HydroCNHS over the
model's complete period, including its warm-up, and writes daily inlet boundaries
for the selected operation dates. Operation then advances the reservoir agents,
physical storage and native downstream routing one day at a time. It is not an
interleaved weather-feedback loop or a runoff callback inside each decision.

## 1. Start from accepted hydrology and complete weather

Supply an agent-free HydroCNHS model using GWLF or ABCD rainfall-runoff with
Lohmann routing. Establish its warm-up, calibration and validation before using
its flow as an operating boundary. The weather table must contain every model day
for every weather-driven subbasin:

```text
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
```

Precipitation is millimetres per day, temperature is degrees Celsius and PET is
centimetres per day. Preparation converts precipitation to the centimetres per
day expected by native HydroCNHS. Missing days, duplicate samples, unknown
subbasins, non-finite values, or negative precipitation/PET stop validation.

See [Weather and inflow inputs](WEATHER_INPUTS.md) for the complete contract and
[HydroCNHS setup and C&V](HYDROLOGY_SETUP.md) for model acceptance.

## 2. Define reservoir physics and the operation network

The coupled YAML points to a separate `reservoir-physical-case.v1` JSON. It holds
the `llm-reservoir-network.v1` network, including:

- reservoir capacity, dead storage, initial storage and release limits;
- one local inflow node for each reservoir;
- downstream connections and unit hydrographs; and
- one common outlet.

Use m³ for storage, m³/s for flow and `86400` seconds for the daily step. The
initial reservoir storage is an explicit operation assumption; hydrological
warm-up does not create it.

Every operation routing node needs one `hydrology.inflow_bindings` entry. A
binding can select a routed native outlet, direct subbasin runoff, or explicit
zero lateral flow. Bindings that contain overlapping upstream catchments are
rejected. In a series of reservoirs, supply only the incremental lateral flow at
the downstream local node; the operation network routes the upstream reservoir's
release and spill exactly once.

## 3. Choose the decision method

Each controlled reservoir has one agent. Passive outlets use physical discharge
and have no agent.

| Purpose | Agent setting | Model request |
|---|---|---|
| Rule-based benchmark | `strategy: benchmark`, `mode: offline` | None |
| General LLM operator | `strategy: configured`, `mode: llm` | Uses your prompt, selected information and model profile |
| Preserved F.E. Walter teaching methods | optional `strategy: reference_v3_7` plugin | Uses the example's available-information or operating-knowledge prompt builder |

For a new reservoir, use `configured`. The F.E. Walter plugin preserves a named
historical method; it does not turn “DKP” into a generic operation method.

The LLM or rule requests a controlled release. The shared physical kernel applies
release limits and water availability, computes spill and ending storage, and
passes controlled release plus spill to native routing.

## 4. Check, prepare, run and verify

From the repository environment, use the same coupled YAML for all four steps:

```powershell
reservoir-experiment check simulation.yaml
reservoir-experiment prepare simulation.yaml
reservoir-experiment run simulation.yaml
reservoir-experiment verify OUTPUT/operation
```

`check` validates paths, hashes, dates, weather completeness, bindings, physics,
agents and model settings. It runs neither hydrology nor an LLM.

`prepare` runs only native hydrology, writes the selected daily boundaries and
makes **zero model requests**. Its output contains `inflows.csv`, `case.json`,
`experiment.yaml`, `hydrology.json` and `preparation.json`.

`run` verifies that preparation still matches the inputs, then creates
`OUTPUT/operation`. A rule-based run needs no network flag. An LLM run requires
the explicit network gate:

```powershell
reservoir-experiment run simulation.yaml --allow-network
```

`max_calls: null` means no total call cap; it does not alter the per-decision
`models.<id>.max_attempts` retry limit. Use a finite `max_calls` when the study
requires a total cap.

`verify OUTPUT/operation` checks saved records, hashes, request linkage and water
accounting. Completion establishes a reproducible execution, not acceptable
reservoir performance.

## 5. Follow one operation day

1. The prepared local boundary supplies the day's reservoir inlet.
2. The selected agent sees its allowed information and requests controlled release.
3. The physical kernel implements a feasible controlled release, spill and ending storage.
4. Native HydroCNHS routes controlled release plus spill downstream once.
5. The trace commits the decision, audit, physics and routing evidence.
6. The next day begins with committed ending storage and implemented-release history.

No same-day downstream result feeds back into the decision that produced it.

## 6. Reuse hydrology or resume an interrupted operation

When only the operation method changes, give the new configuration a new
`run_id` and `output`, then set:

```yaml
hydrology:
  prepared_from: ../previous-output
```

Reuse is accepted only when the hydrology model and forcing bytes, full model
period, selected operation dates, bindings, zero-flow nodes, relevant code and
numeric runtime match. The new preparation copies the verified boundaries and
records their checksums without rerunning hydrology.

Resume an interrupted operation into another new directory:

```powershell
reservoir-experiment resume simulation.yaml `
  --from-run OUTPUT/operation `
  --output NEW_OUTPUT `
  --run-id NEW_RUN_ID
```

Add `--allow-network` only when continuation must make new LLM requests. Resume
replays and checks the committed prefix; it never overwrites the source run.

Continue with the [F.E. Walter coupled example](../examples/fe_walter/coupled/README.md)
or inspect the [code structure](CODE_STRUCTURE.md).
