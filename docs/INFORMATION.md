# Decision-time information

<div class="hero-band" markdown="1">

An `information` profile gives an operator a **causal, read-only** view of external stream gauges, inflow/weather forecasts, seasonal guide curves, or upstream reservoir states at decision time—without ever allowing future flood peaks to leak into today's decision or mutating physical storage and routing.

</div>

## Causal availability and decision timing

At every timestep `t`, HydroReOpLLM enforces strict hydrological causality:

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### What an operator already knows

- Its own reservoir's beginning `storage_m3` and current step's routed `inflow_cms` (daily runs assume the current day's mean inflow is known when setting that day's release).
- Its own previous committed releases (`$previous_transition` / `$completed_history`).
- Upstream reservoirs' outflows/storages **only after** those upstream reservoirs have completed step `t` in topological order.

</div>
<div class="panel-card" markdown="1">

### Causal guards for gauges & forecasts

- **UTC timestamps**: All `valid_time`, `available_at`, and `issued_at` entries in CSVs must include `Z` or an explicit UTC offset (e.g., `2021-06-01T00:00:00Z`).
- **Gauge observations (`kind: observation`)**: Visible only when **both** `valid_time <= decision_clock` and `available_at <= decision_clock` (no peeking at tomorrow's gauge).
- **Forecasts (`kind: forecast`)**: `valid_time` may be in the future (e.g., 3-day lead inflow), provided **both** `issued_at <= decision_clock` and `available_at <= decision_clock`.

</div>
</div>

## Source types and unit conversions

Declare reusable data feeds under `information.sources` (`v2`) or `information_sources` (`v1`):

| `type` | Required fields | Optional fields | What it provides |
| --- | --- | --- | --- |
| `static` | `quantity`, `unit`, `location`, `value` | `datum` | Constant operational parameter (e.g., target release, flood stage, seasonal rule table). |
| `csv` | `quantity`, `unit`, `location`, `kind` (`observation` \| `forecast`), `path` | `datum` | Time-series gauge observations or issued forecasts with causal timestamp filtering. |
| `simulation` | `quantity` (`inflow` \| `storage` \| `release` \| `flow`), `unit`, `location` | `datum` | Live read-only state from another reservoir, junction, or outlet (`storage` in `m3`; flows in `m3/s`). |
| `extension` | `quantity`, `unit`, `location`, `provider` | `kind`, `parameters`, `datum` | Custom Python reader returning timestamped measurements or forecasts. |

### Concrete CSV examples

**Observation CSV (`kind: observation`)** — exact columns `valid_time,available_at,value`:

```csv
valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-01T00:00:00Z,1240.0
2021-01-02T00:00:00Z,2021-01-02T00:00:00Z,1580.0
```

**Forecast CSV (`kind: forecast`)** — exact columns `issued_at,valid_time,available_at,value`:

```csv
issued_at,valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-02T00:00:00Z,2021-01-01T00:00:00Z,1450.0
2021-01-01T00:00:00Z,2021-01-03T00:00:00Z,2021-01-01T00:00:00Z,1920.0
```

### Supported unit conversions

Add `unit:` on a profile field to convert scalars automatically for the operator without changing the SI physical ledger:

- **Flow**: `m3/s` ↔ `cfs` (`1 m³/s = 35.31466672148859 cfs`)
- **Volume**: `m3` ↔ `acre-ft` (`1 acre-ft = 1233.48183754752 m³`)
- **Length / Elevation**: `m` ↔ `ft` (`1 m = 3.280839895013123 ft`)

## Configuring profiles and agent bindings

Group selected sources into named operator views under `profiles.<profile_id>.fields.<alias>`, optionally requesting trailing `history` samples, freshness limits (`max_age_seconds`), target `unit`, and `required`:

```yaml
# information.yaml
sources:
  downstream_gauge:
    type: csv
    kind: observation
    quantity: flow
    unit: cfs
    location: usgs_01449000
    path: data/lehighton_obs.csv
  upstream_storage:
    type: simulation
    quantity: storage
    unit: m3
    location: upper_dam
profiles:
  operator_view:
    fields:
      lehighton_flow_cms:
        source: downstream_gauge
        unit: m3/s           # Automatic cfs -> m3/s conversion
        history: 3           # Include last 3 causal observations
        max_age_seconds: 86400
        required: false
      upper_pool_acft:
        source: upstream_storage
        unit: acre-ft        # Automatic m3 -> acre-ft conversion
        required: true
```

Attach `information.yaml` in `experiment.yaml` and bind the profile to an agent:

```yaml
# experiment.yaml
information:
  file: information.yaml

# agents.yaml
operator_a:
  reservoir_id: lower_dam
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    information: operator_view
```

- **LLM operators**: Include `$information` in `prompt_file` or `system_prompt_file` so the rendered JSON snapshot appears in the prompt.
- **Rule-based operators**: Read `observation["context"]["decision_information"]` inside your Python rule's `decide(observation)` method.
- **Custom dynamic retrievers**: For rule/manual retrieval plugins (such as DKP excerpt selection), use `customization.context_providers` ([Agent Design](AGENT_DESIGN.md)).

## Missing-data handling and verification

| Field setting | Missing or stale data behavior | Verification check |
| --- | --- | --- |
| `required: true` | Stops the simulation immediately—never silently substitutes `0.0`. | Confirms exact selected values against source CSVs/simulation states during `verify`. |
| `required: false` | Records `status: "MISSING"`, `value: null`, and an explicit `reason` so the operator knows data is absent. | Verifies causal timestamps (`valid_time`/`issued_at`/`available_at`) on every step in `decisions.jsonl`. |

<div class="callout callout-info" markdown="1">

**Check after edits.** Always run `reservoir-experiment check <config>` after modifying `information.yaml` or `$information` placeholders to verify column headers, UTC timestamps, and unit compatibility offline.

</div>
