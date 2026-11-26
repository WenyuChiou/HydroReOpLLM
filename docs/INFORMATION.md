# Decision-time information

<div class="hero-band" markdown="1">

An information profile (`InformationCatalog` in `src/llm_reservoir_agent/information.py`) gives an operator a **causal, read-only, unit-explicit** view of observations, forecasts, static targets, or simulation states at decision time—without mutating reservoir storage, inflows, bounds, or routing.

</div>

## Causal availability and decision timing

Every decision at step `t` obeys strict causal timing:

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### What an operator already sees

- Its own reservoir's beginning `storage_m3` and current interval-mean routed `inflow_cms` (daily runs assume the current day's mean inflow is known when deciding that day's release).
- Its own committed `previous_transition` (and up to `history_steps` earlier committed steps).
- Other reservoirs' states **only after** their step is committed (`simulation` sources respect topological commit order).

</div>
<div class="panel-card" markdown="1">

### Causal guards for external CSV & extension data

- **Timezone requirement**: All `valid_time`, `available_at`, and `issued_at` timestamps must end with `Z` or an explicit UTC offset.
- **Observation (`kind: observation`)**: Eligible only when `valid_time <= clock` **and** `available_at <= clock`.
- **Forecast (`kind: forecast`)**: `valid_time` may lie in the future, but **both** `issued_at <= clock` and `available_at <= clock` must hold.

</div>
</div>

## Source types and unit conversions

Declare reusable sources under `information.sources` (in `v2` split-file `information.yaml`) or `information_sources` (`v1`):

| `type` | Required fields | Optional fields | Selection & provenance behavior |
| --- | --- | --- | --- |
| `static` | `quantity`, `unit`, `location`, `value` | `datum` | Constant JSON value; always available. |
| `csv` | `quantity`, `unit`, `location`, `kind` (`observation` \| `forecast`), `path` | `datum` | Exact UTF-8 CSV bytes pinned by SHA-256. Observations require exact columns `valid_time,available_at,value`; forecasts require `issued_at,valid_time,available_at,value`. |
| `simulation` | `quantity` (`inflow` \| `storage` \| `release` \| `flow`), `unit`, `location` | `datum` | Reads current/committed native state; `storage` requires native unit `m3` at a reservoir node; flow quantities require `m3/s`. |
| `extension` | `quantity`, `unit`, `location`, `provider` | `kind`, `parameters`, `datum` | Invokes a registered Python reader once per source per decision; requires explicit `.version` attribute. |

### Supported unit conversions

Profile fields can declare `unit:` to convert scalar values explicitly at snapshot construction (`_CONVERSIONS` in `information.py`) without altering the physical ledger:

- **Flow**: `m3/s` ↔ `cfs` (`35.31466672148859`)
- **Volume**: `m3` ↔ `acre-ft` (`1 / 1233.48183754752`)
- **Length / Elevation**: `m` ↔ `ft` (`3.280839895013123`)

## Configuring profiles and agent bindings

Define named views under `profiles.<profile_id>.fields.<alias>`, specifying `source`, optional `unit`, `history` (positive sample count), `max_age_seconds` (freshness window), and `required` (boolean):

```yaml
# information.yaml
sources:
  operating_target:
    type: static
    quantity: target_release
    unit: m3/s
    location: lake_a
    value: 2.5
profiles:
  operator_view:
    fields:
      operating_target_cms:
        source: operating_target
        required: true
```

Attach `information.yaml` in `experiment.yaml`, then bind the profile on the target agent (`customization.information`):

```yaml
# experiment.yaml
information:
  file: information.yaml

# agents.yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    information: operator_view
```

- **For generic LLM agents**: Include `$information` in `prompt_file` or `system_prompt_file` (`workflow.py` rejects mismatched binding vs placeholder).
- **For rule-based extensions**: Read `observation["context"]["decision_information"]` inside `decide(observation)`.
- **Alternative custom bindings**: For ad-hoc retrieval plugins (such as vector/text DKP search), use `customization.context_providers` returning `ContextValue` (`validate_available_at` in `src/llm_reservoir_agent/context.py`), documented in [Operator & LLM agent design](AGENT_DESIGN.md).

## Missing-data handling and verification

| Profile field setting | Missing or stale record behavior | Provenance & `verify` check |
| --- | --- | --- |
| `required: true` | Stops execution with an explicit error—never substitutes `0.0`. | Reconstructs `static`, `csv`, and `simulation` snapshots deterministically from `experiment.json`. |
| `required: false` | Emits `status: "MISSING"`, `value: null`, and explicit `reason` in the snapshot. | Retains `source_sha256` / `provider_version` and verifies causal timing on every `decisions.jsonl` record. |

<div class="callout callout-info" markdown="1">

**Recovery note.** Because `extension` information providers may perform dynamic external reads, `RecoveryTape` (`reservoir-experiment resume`) requires a durable replay contract and rejects dynamic `extension` sources unless replayed via saved context. Run `reservoir-experiment check` after every catalog edit.

</div>
