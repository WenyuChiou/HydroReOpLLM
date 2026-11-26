# Experiment configuration

<div class="hero-band" markdown="1">

Every experiment starts from a top-level `experiment.yaml` that links your physical basin, operating rules or LLMs, and simulation clock. Start by copying the [Two-reservoir template](../examples/template/README.md) or using the modular split-file layout below.

</div>

## Three building blocks of an experiment

<div class="panel-grid panel-grid-3" markdown="1">
<div class="panel-card" markdown="1">

### Block A: Physical basin & inflows

Reservoir capacities, dead storage, release limits, routing lags (`case.json` or `reservoirs.yaml`), plus either `inflows.csv` or `hydrology.yaml`.

</div>
<div class="panel-card" markdown="1">

### Block B: Operators, info & models

One rule or LLM agent per controlled dam (`agents`), optional gauge/forecast feeds (`information`), model profiles (`models`), and `auditors`.

</div>
<div class="panel-card" markdown="1">

### Block C: Clock & output

Unique `run_id`, unused `output` folder, operation dates (`start_date`–`end_date` or UTC `start_time`–`end_time`), and `max_calls`.

</div>
</div>

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM configuration layout connecting experiment.yaml, case, hydrology, agents, models, and information">
  <figcaption><strong>Configuration file layout.</strong> Each YAML file resolves relative paths from its own folder.</figcaption>
</figure>

## Schema versions and relative paths

| `schema_version` | Hydrology | `{file: ...}` sections | Typical use |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | Prepared inflows | Inline | Generic template and F.E. Walter studies (`inflows.csv` + `case.json`). |
| `llm-reservoir-experiment.v2` | Prepared inflows | `models`, `agents`, `auditors`, `extensions`, `information` | Modular prepared-inflow studies across separate YAML files. |
| `hydroops-coupled-simulation.v1` | Coupled HydroCNHS | Inline | Single-file coupled watershed + reservoir study. |
| `hydroops-coupled-simulation.v2` | Coupled HydroCNHS | `hydrology`, `models`, `agents`, `auditors`, `extensions`, `information` | Recommended modular layout for multi-reservoir and hybrid basins. |

- All paths (`case`, `output`, `prompt_file`, `knowledge`, CSVs) resolve relative to the **declaring** YAML file.
- Each `{file: ...}` reference replaces that entire top-level section; do not mix inline keys inside a `{file: ...}` block.

## Top-level experiment keys

| Key | Required | Purpose |
| --- | --- | --- |
| `schema_version` | Yes | Selects `v1`/`v2` prepared-inflow or coupled HydroCNHS format. |
| `run_id` | Yes | Unique label saved in `summary.json` and step logs. |
| `output` | Yes | Fresh output folder path (existing folders are never overwritten). |
| `case` | Yes | `case.json` or `reservoirs.yaml` defining reservoirs, routing, and `inflow_source.sha256` (if prepared). |
| `start_date` / `end_date` | Daily | Quoted `YYYY-MM-DD` inclusive operation dates. |
| `start_time` / `end_time` / `time` | Sub-daily | UTC timestamps (exclusive `end_time`) and `{simulation_step, output_step}` for hourly runs. |
| `hydrology` | Coupled | HydroCNHS catchment model, weather forcing, and `inflow_bindings`. |
| `agents` | Yes | Assigns one operator (`rule_based`, `llm`, or `offline`) per controlled reservoir. |
| `models` | LLM runs | Named Ollama or cloud LLM profiles ([Model providers](MODEL_PROVIDERS.md)). |
| `auditors` | No | Diagnostic checks (`release_bounds`, `field_range`) applied to requested releases. |
| `extensions` | No | Registered Python rule packages (e.g., `hanasaki: study/rule/__init__.py`). |
| `information` | No | Gauge, forecast, guide-curve, and upstream-state feeds ([Gauges & forecasts](INFORMATION.md)). |
| `outcome_checks` | No | Post-routing downstream flow checks (`minimum_cms`, `maximum_cms`) at junctions or outlets. |
| `max_calls` | Recommended | Maximum total LLM calls (`0` for offline/rule runs; `>= llm_agents * steps` for live runs). |

## Setup order and YAML rules

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. Run &amp; dates</strong><code>run_id</code>, unused <code>output</code>, quoted dates</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. Hydrology</strong><code>inflows.csv</code> or <code>hydrology.yaml</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. Reservoirs</strong>Storage, bounds &amp; routing lags</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. Operators</strong>1 agent per controlled dam</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. Info &amp; models</strong><code>models.yaml</code>, prompts, <code>information</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. Check</strong><code>reservoir-experiment check</code></div>
</div>

<div class="callout callout-warn" markdown="1">

**Common YAML pitfalls.** Duplicate keys in any YAML section are rejected so repeated entries cannot silently overwrite settings. Always include `+` or `-` in scientific notation (`8.0e+6` or `8000000.0`), because YAML parses `8.0e6` as text.

</div>

- **Operators (`agents`)**: Choose `type: rule_based`, `type: llm`, or `mode: offline` ([Rules & LLM prompts](AGENT_DESIGN.md)).
- **Auditors (`auditors`)**: Check `release_bounds` (`tolerance_cms`) or `field_range` (`path`, `minimum`, `maximum`, `on_violation: FAIL | WARN`) without altering flows.
- **Outcome checks (`outcome_checks`)**: Flag downstream flood exceedances or low-flow deficits at junctions or outlets after routing completes.
