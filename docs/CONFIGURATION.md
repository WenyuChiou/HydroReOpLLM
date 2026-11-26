# Configuration

<div class="hero-band" markdown="1">

Every HydroReOpLLM study starts from a top-level `experiment.yaml` file that connects your physical reservoir network, hydrology inflows, operating rules or LLM agents, model profiles, and output folder. Start by copying [`examples/template/`](../examples/template/README.md) for prepared inflows or using the modular split-file layout below for coupled HydroCNHS studies.

</div>

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM configuration layout connecting experiment.yaml, case, hydrology, agents, models, and information">
  <figcaption><strong>Configuration file layout.</strong> Top-level <code>experiment.yaml</code> resolves section files, reservoir networks, prompts, operating manuals, and Python rule packages relative to each declaring file.</figcaption>
</figure>

## Schema versions and file resolution

Choose single-file (`v1`) for compact prepared-inflow setups, or modular split-file (`v2`) when organizing multi-reservoir studies with separate YAML files:

| `schema_version` | Hydrology style | Modular section files (`{file: ...}`) | Typical use |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | Prepared inflows | Inline sections | Generic template and F.E. Walter studies (`inflows.csv` + `case.json`). |
| `llm-reservoir-experiment.v2` | Prepared inflows | `models`, `agents`, `auditors`, `extensions`, `information` | Large prepared-inflow studies organized across separate YAML files. |
| `hydroops-coupled-simulation.v1` | Native HydroCNHS | Inline sections | Single-file coupled HydroCNHS watershed + reservoir operation. |
| `hydroops-coupled-simulation.v2` | Native HydroCNHS | `hydrology`, `models`, `agents`, `auditors`, `extensions`, `information` | Recommended modular layout for multi-reservoir and hybrid Rule + LLM basins. |

- **Relative paths**: Every path (`case`, `output`, `prompt_file`, `system_prompt_file`, `knowledge`, `extensions`, CSV paths) is resolved relative to the **file that declares it**.
- **Full-section replacement**: A `{file: ...}` reference replaces that complete section (for example `agents: { file: agents.yaml }`); do not mix inline keys inside a `{file: ...}` block.

## Top-level experiment keys

| Key | Required | Purpose in the simulation |
| --- | --- | --- |
| `schema_version` | Yes | Selects `v1`/`v2` prepared-inflow or coupled HydroCNHS schema. |
| `run_id` | Yes | Unique experiment label saved in `summary.json` and decision logs. |
| `output` | Yes | Fresh output folder path (relative to `experiment.yaml`; never overwrites existing runs). |
| `case` | Yes | Path to `case.json` or `reservoirs.yaml` defining reservoir capacities, bounds, and routing. In prepared cases, `case.json` points to `inflows.csv` and its `inflow_source.sha256`. |
| `start_date`, `end_date` | Daily | Quoted `YYYY-MM-DD` inclusive operation dates inside the inflow/hydrology period. |
| `start_time`, `end_time`, `time` | Sub-daily | UTC timestamps (exclusive `end_time`) + `time: {simulation_step, output_step}` for hourly runs. |
| `hydrology` | Coupled only | Connects HydroCNHS catchment model, weather forcing, `inflow_bindings`, and `diagnostics`. |
| `agents` | Yes | Assigns exactly one operator (`rule_based`, `llm`, or `offline`) to each controlled reservoir. |
| `models` | LLM runs | Named local Ollama or cloud LLM profiles ([Model providers](MODEL_PROVIDERS.md)). |
| `auditors` | No | Diagnostic checks (`release_bounds`, `field_range`) applied to requested releases. |
| `extensions` | No | Maps custom rule or retrieval names (such as `hanasaki`) to Python package folders. |
| `information` | No | Causal stream-gauge, forecast, guide-curve, and upstream-state feeds ([Decision-time information](INFORMATION.md)). |
| `outcome_checks` | No | Post-routing downstream flow checks (`minimum_cms`, `maximum_cms`, or dynamic info bounds) at junctions or outlets. |
| `max_calls` | Recommended | Maximum total LLM requests allowed (`0` for offline/rule runs; at least `llm_agents * steps` for live LLM runs). |

## Setup order and YAML validation rules

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. Run &amp; window</strong><code>run_id</code>, unused <code>output</code>, quoted dates</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. Hydrology</strong><code>inflows.csv</code> or <code>hydrology.yaml</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. Reservoirs</strong>Storage, outlet bounds &amp; routing lags</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. Operators</strong>1 agent per controlled reservoir</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. Info &amp; models</strong><code>models.yaml</code>, prompts, <code>information</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. Check offline</strong><code>reservoir-experiment check</code></div>
</div>

<div class="callout callout-warn" markdown="1">

**Two common YAML pitfalls.** HydroReOpLLM rejects duplicate keys in any YAML section so an accidental repeated reservoir or model entry cannot silently overwrite an earlier setting. Also include an explicit `+` or `-` in scientific notation (`8.0e+6` or `8000000.0`) rather than `8.0e6`, which YAML parses as text.

</div>

## Operators, auditors, and outcome checks

- **Operators (`agents`)**: Choose `type: rule_based` (Hanasaki or custom Python rule), `type: llm` (prompted model), or `mode: offline` (`release_cms` smoke test). See [Operator & LLM agent design](AGENT_DESIGN.md).
- **Decision auditors (`auditors`)**: Built-in auditors verify whether a requested release fits within feasible outlet bounds (`release_bounds`, optional `tolerance_cms`) or whether any observation/action field lies inside `[minimum, maximum]` (`field_range`, `on_violation: FAIL | WARN`).
- **Downstream outcome checks (`outcome_checks`)**: Check routed flows at downstream gauges, junctions, or outlets after channel routing completes—ideal for flagging downstream flood-stage exceedances or environmental low-flow deficits.

Continue with [Reservoir networks](MULTI_RESERVOIR.md), [Time scales and units](TIME_SCALES.md), [Decision-time information](INFORMATION.md), and [Run, verify and resume](RUNNING.md).
