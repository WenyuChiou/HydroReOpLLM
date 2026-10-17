# Build a weather-to-operation simulation

This tutorial takes one accepted HydroCNHS model through reservoir operation.
Start with the rule-based configuration. It exercises the full hydrology,
reservoir, routing and evidence path without contacting a model provider.

The runnable teaching case is in
[`examples/multiple_reservoirs`](../examples/multiple_reservoirs/experiment.yaml).
It contains two independent river systems. Its short forcing record and
synthetic parameters test software connections; they are not a calibrated
hydrological model or a validated operating policy.

## 1. Install the project

Create an environment, install the repository, and confirm the command is
available:

```powershell
git clone https://github.com/WenyuChiou/HydroOpsLLM.git
cd HydroOpsLLM
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
reservoir-experiment --help
```

Hydrology and orchestration run on the CPU. A GPU is relevant only when a local
inference server uses it. Remote providers do not use your local GPU.

## 2. Accept the HydroCNHS model first

Use an agent-free HydroCNHS model with GWLF or ABCD rainfall-runoff and Lohmann
routing. Establish warm-up, calibration and validation before treating its flow
as an operating boundary. Keep the accepted model, forcing bytes, metrics,
periods and provenance together.

The weather table contains every model day for every weather-driven subbasin:

```text
date,subbasin_id,precipitation_mm,temperature_c,pet_cm
2020-02-27,basin_a,10,10,0.1
```

Preparation runs native HydroCNHS over the complete continuous period, including
warm-up. It then selects the daily boundaries for reservoir operation. Reservoir
decisions do not feed back into the weather-to-runoff calculation.

See [HydroCNHS setup and calibration/validation](HYDROLOGY_SETUP.md) and
[weather inputs](WEATHER_INPUTS.md) before adapting the teaching files.

## 3. Bind hydrology to the reservoir network

The top-level file points to `hydrology.yaml` and `reservoirs.yaml`:

```yaml
schema_version: hydroops-coupled-simulation.v2
case: reservoirs.yaml
start_date: '2020-02-28'
end_date: '2020-03-02'
hydrology: {file: hydrology.yaml}
```

Each hydrology binding supplies incremental local flow to one operation node:

```yaml
model: model.yaml
forcing: forcing.csv
zero_flow_nodes: []
inflow_bindings:
  inlet_a: {runoff: basin_a}
  inlet_b: {runoff: basin_b}
  river_a: {constant: 0}
  river_b: {constant: 0}
```

Do not add already routed upstream flow as local inflow again. The operation
network routes controlled release plus spill exactly once.

The physical case uses `reservoir-physical-case.v1`. Every water ID is explicit.
The current reservoir kernel assumes zero evaporation and seepage.
New networks use `llm-reservoir-network.v2` and an `outlets` list:

```yaml
schema_version: reservoir-physical-case.v1
data_kind: synthetic_fixture
network:
  schema_version: llm-reservoir-network.v2
  start_date: '2020-02-28'
  reservoirs:
    lake_a:
      inflow_node: inlet_a
      physical:
        reservoir_id: lake_a
        capacity_m3: 1000000
        dead_storage_m3: 0
        initial_storage_m3: 500000
        minimum_release_cms: 0
        maximum_release_cms: 20
        dt_seconds: 86400
  connections:
    - source: lake_a
      target: river_a
      unit_hydrograph: [0, 1]
  outlets: [river_a]
```

Every item in `outlets` is an exact terminal node. Independent systems can share
one experiment and remain independent; do not invent a common outlet. Information
sources describe what an agent may see. They never create water connections.

## 4. Choose an agent for every controlled reservoir

Each controlled reservoir has exactly one agent. Passive reservoirs have no
agent. Start with the deterministic Hanasaki rule:

```yaml
operator_a:
  reservoir_id: lake_a
  type: rule_based
  rule: hanasaki
  rule_parameters:
    alpha: 0.85
    inflow_statistics_file: statistics_a.json
  auditors: [bounds]
```

Use `type: rule_based` with `rule` naming an explicitly registered rule extension.
Hanasaki is this example's rule; register another implementation for your own
operating curves, water-supply or hydropower controller. Use `type: llm`,
`model_profile` and `prompt_file` for
a general model-backed operator. Optional prompt/context controls belong inside
`customization`; no common system instruction is injected.
Rule-based agents can also select `customization: {information: downstream}`;
the engine supplies available values in `observation.context.decision_information`.
The F.E. Walter Anik teaching methods are an active case extension with their
own native message formatting. They do not define the generic configured prompt.

Continue with [Agents, prompts and context](CONFIGURATION.md) and
[model providers](MODEL_PROVIDERS.md) before enabling an LLM agent.

## 5. Check without running anything

From the repository root:

```powershell
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
```

`check` reads and validates every referenced section, path, model profile,
prompt, extension, date, binding and physical setting. It runs neither hydrology
nor a provider request. Each path is relative to the file that declares it.

## 6. Prepare hydrology

```powershell
reservoir-experiment prepare examples/multiple_reservoirs/experiment.yaml
```

`prepare` runs the full continuous hydrology period and writes the selected
operation boundaries. It makes zero model requests. The preparation contains
`inflows.csv`, `case.json`, `experiment.yaml`, `hydrology.json` and
`preparation.json`, with hashes that bind the generated files to their sources.

## 7. Run the rule-based case

```powershell
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
```

The operation period is four days: 2020-02-28 through 2020-03-02. Each day the
agent requests controlled release, the physical kernel implements a feasible
release and spill, and native routing advances downstream. The next decision
uses the committed ending state. Same-day downstream flow does not feed back
into the decision that produced it.

To run the LLM variant later, use `experiment.llm.yaml`. It selects
`agents.llm.yaml`, gives the run a separate identity and keeps `lake_b` on its
Hanasaki rule. Each agent selects its own method within the shared experiment.
Add the explicit network gate:

```powershell
reservoir-experiment run examples/multiple_reservoirs/experiment.llm.yaml --allow-network
```

`max_calls: null` removes the total request cap. It does not remove each model
profile's `max_attempts` limit.

## 8. Verify and read the result

```powershell
reservoir-experiment verify runs/independent-rivers-rule/operation
```

Read `summary.json` first, then inspect:

| Evidence | Question it answers |
|---|---|
| `decisions.jsonl` | What observation and proposal were bound to each decision? |
| `raw/` and provider ledger | What messages, requests, replies, usage and attempt metadata were retained? |
| `audit.jsonl` | Which configured decision checks passed, warned, failed or remained unknown? |
| `physics.jsonl` | What release and spill were implemented, and did storage balance? |
| `network_flows.csv` | What flow reached each routing node? |
| `reservoir_trajectory.csv` | How did each reservoir state change? |

Evidence-write failure stops execution. Audit FAIL and physical failure do not
trigger another model attempt. A completed run establishes reproducible
execution and water accounting; it does not establish policy quality.

## 9. Resume after an interruption

Resume into a new output directory:

```powershell
reservoir-experiment resume examples/multiple_reservoirs/experiment.yaml `
  --from-run runs/interrupted/operation `
  --output runs/resumed `
  --run-id resumed-01
```

Resume verifies and replays the committed prefix. It skips committed decisions
and reuses captured replies when available. It does not overwrite the source run.
Add `--allow-network` only if unfinished decisions need new provider requests.
All five provider adapters can replay committed attempts, including retries and
fallbacks. Committed custom context values are reused without rerunning retrieval.
Dynamic numeric information sources with `type: extension` need a durable
replay contract and are currently rejected by `resume`; use pinned CSV/static
information for resumable studies.

The ledger prevents silent duplicate decisions inside the recovered trace, but
it cannot promise exactly-once behavior at an external network service.

Next, use the [complete two-reservoir walkthrough](MULTI_RESERVOIR.md) or the
[parameter reference](PARAMETER_REFERENCE.md).
