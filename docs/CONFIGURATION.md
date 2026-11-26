# Configuration

<div class="hero-band" markdown="1">

Every experiment starts from a top-level `experiment.yaml` connecting your physical reservoirs, inflows, operators, models, and output folder. Copy [`examples/template/`](../examples/template/README.md) for prepared inflows or use the split-file layout below for coupled HydroCNHS studies.

</div>

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM configuration layout connecting experiment.yaml, case, hydrology, agents, models, and information">
  <figcaption><strong>Configuration file layout.</strong> Each file resolves relative paths from its own directory.</figcaption>
</figure>

## Schema versions and file resolution

| `schema_version` | Hydrology | `{file: ...}` sections | Typical use |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | Prepared inflows | Inline | Generic template and F.E. Walter studies (`inflows.csv` + `case.json`). |
| `llm-reservoir-experiment.v2` | Prepared inflows | `models`, `agents`, `auditors`, `extensions`, `information` | Modular prepared-inflow studies across separate YAML files. |
| `hydroops-coupled-simulation.v1` | Native HydroCNHS | Inline | Single-file coupled HydroCNHS watershed + reservoir study. |
| `hydroops-coupled-simulation.v2` | Native HydroCNHS | `hydrology`, `models`, `agents`, `auditors`, `extensions`, `information` | Recommended modular layout for multi-reservoir and hybrid basins. |

- Paths (`case`, `output`, `prompt_file`, `knowledge`, CSVs) resolve relative to the **declaring** YAML file.
- Each `{file: ...}` reference replaces that entire top-level section; do not mix inline keys inside a `{file: ...}` block.

## Top-level experiment keys

| Key | Required | Purpose |
| --- | --- | --- |
| `schema_version`, `run_id`, `output` | Yes | Schema version, unique run label, and unused output folder path. |
| `case` | Yes | `case.json` or `reservoirs.yaml` defining capacities, bounds, routing, and `inflow_source.sha256` (if prepared). |
| `start_date`, `end_date` | Daily | Quoted `YYYY-MM-DD` inclusive operation dates. |
| `start_time`, `end_time`, `time` | Sub-daily | UTC timestamps (exclusive `end_time`) + `{simulation_step, output_step}` for hourly runs. |
| `hydrology` | Coupled | Native HydroCNHS model, weather forcing, and `inflow_bindings`. |
| `agents` | Yes | Assigns one operator (`rule_based`, `llm`, or `offline`) to each controlled reservoir. |
| `models` | LLM runs | Named local Ollama or cloud LLM profiles ([Model providers](MODEL_PROVIDERS.md)). |
| `auditors`, `extensions` | No | Release/range auditors and registered Python rule packages (e.g., `hanasaki`). |
| `information`, `outcome_checks` | No | Causal gauge/forecast feeds and post-routing downstream flow checks. |
| `max_calls` | Recommended | Maximum total LLM calls (`0` for offline/rule runs; `>= llm_agents * steps` for live runs). |

## Setup order and YAML validation rules

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

## Operators, auditors, and outcome checks

- **Operators (`agents`)**: Choose `type: rule_based`, `type: llm`, or `mode: offline` ([Agent design](AGENT_DESIGN.md)).
- **Decision auditors (`auditors`)**: Check `release_bounds` (`tolerance_cms`) or `field_range` (`path`, `minimum`, `maximum`, `on_violation: FAIL | WARN`) without altering flows.
- **Outcome checks (`outcome_checks`)**: Flag downstream flood-stage exceedances or low-flow deficits (`minimum_cms`, `maximum_cms`, or dynamic info bounds) at junctions or outlets after routing.
