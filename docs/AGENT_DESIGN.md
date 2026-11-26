# Operator and LLM agent design

<div class="hero-band" markdown="1">

HydroReOpLLM separates **operating decisions** (a deterministic rule or an LLM policy) from **physical water balance** (the shared HydroCNHS `Dam` mass-balance and routing engine). Both rule-based and LLM operators observe the exact same reservoir state, return a requested release in `m³/s`, and obey identical outlet bounds, dead storage, and spill physics.

</div>

## Architectural boundary with HydroCNHS

HydroReOpLLM wraps HydroCNHS's Agent-Based Modeling (`ABM`) `Dam` interface (`examples/llm_reservoir_abm.py`). Each controlled reservoir receives its routed inflow from HydroCNHS, exposes current beginning storage and feasible release bounds to its assigned operator, and returns `controlled_release_cms + spill_cms` back to HydroCNHS for downstream routing.

Because the decision backend only requests a target release and never edits storage or routing directly, you can compare a **Hanasaki rule**, a **custom Python guide curve**, and an **LLM operator** on the exact same physical watershed without changing a single hydrology parameter.

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="Closed-loop reservoir operation architecture integrating HydroCNHS and LLM/rule agents">
  <figcaption><strong>Figure 1.</strong> Closed-loop reservoir operation architecture: watershed runoff enters the reservoir, the operator evaluates storage, inflow, forecasts/observations, or operational knowledge (DKP) to propose a release, and host physics enforces operating limits and mass conservation before downstream routing.</figcaption>
</figure>

<figure class="figure-card">
  <img src="assets/diagrams/framework.png" alt="Simulation workflow connecting hydrology inputs, operators, auditors, and HydroCNHS routing">
  <figcaption><strong>Simulation module workflow.</strong> How experiment configuration, causal information retrieval, rule or LLM decision backends, diagnostic auditors, and HydroCNHS routing fit together at each step.</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. Basin inflow</strong>Local runoff + lagged upstream outflow (m³/s)</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. Reservoir state</strong>Beginning storage (m³) &amp; feasible bounds</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. Info &amp; DKP</strong>Gauges, forecasts, targets &amp; manual excerpts</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. Prompt render</strong>Fill system &amp; daily user templates</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. Decision</strong>Rule equation or LLM inference</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. Parse &amp; convert</strong>Extract JSON &amp; convert units to m³/s</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. Auditors</strong>Flag bound or range violations</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. Physics &amp; route</strong>Enforce dead storage, spill &amp; route downstream</div>
</div>

## Per-timestep coupling data flow

At each timestep `t` (stepping upstream to downstream across the basin), every controlled reservoir executes eight steps:

| Stage | What happens hydrologically | Inputs | Outputs | Units |
| --- | --- | --- | --- | --- |
| 1. Basin & upstream inflow | Combines local subbasin runoff with lagged releases arriving from upstream reservoirs. | `inflows.csv` + upstream `total_outflow_cms` | Routed reservoir inlet flow `inflow_cms` | `m³/s` (interval mean) |
| 2. Reservoir observation | Snapshots beginning pool volume and feasible outlet capacity. | `storage_m3`, `inflow_cms`, `PhysicalConfig` | Observation snapshot & `release_upper_bound_cms` | `m³`, `m³/s` |
| 3. Info & DKP retrieval | Attaches causal observations, forecasts, guide curves, or relevant DKP rules. | `information` profile / `context_providers` | Read-only decision context | Declared site or SI units |
| 4. Prompt formatting | Inserts current state, prior committed releases, and knowledge into templates. | System & user prompt files + history | Rendered prompt messages (for LLM operators) | Text |
| 5. Operator decision | Evaluates the rule formula or queries the configured LLM provider. | Observation (rule) or messages (LLM) | Proposed release decision | `m³/s` or site units (e.g., `cfs`) |
| 6. Parse & unit conversion | Extracts the numeric release from JSON and converts site units to SI. | Structured JSON reply | Requested controlled release `target_release_cms` | `m³/s` |
| 7. Diagnostic audit | Checks whether the requested release violates bounds or custom thresholds. | Observation + requested release | `PASS`, `WARN`, `FAIL`, or `UNKNOWN` (does not alter flow) | Diagnostic only |
| 8. Host physics & routing | Enforces `[min, max]` bounds, protects `dead_storage_m3`, computes `spill_cms`, and routes outflow downstream. | `storage_start_m3`, `inflow_cms`, `target_release_cms` | `controlled_release_cms`, `spill_cms`, `storage_end_m3` | `m³/s`, `m³` |

## Rule-based operators and Python extensions

Use `type: rule_based` for deterministic hydrological benchmarks and baseline comparisons, or `type: llm` for model-driven operations:

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based` (Deterministic rule)

- **Required keys**: `reservoir_id`, `type: rule_based`, `rule`, optional `rule_parameters`, `auditors`, and optional `customization.information`.
- **Network use**: Strictly `0` model calls (`max_calls: 0` or `null`).
- **Use case**: Hanasaki flood-control baseline, seasonal rule curves, or custom Python hydrological policies.

</div>
<div class="panel-card" markdown="1">

### `type: llm` (Model-driven operator)

- **Required keys**: `reservoir_id`, `type: llm`, `model_profile`, `prompt_file`, optional `auditors`, and `customization:`.
- **Network use**: Requires `--allow-network` for live inference (`customization.execution: live`), or `0` calls in `execution: replay`.
- **Use case**: Reasoning over multi-objective targets, forecasts, and unstructured/structured water-control manuals (DKP).

</div>
</div>

### Built-in and extension Hanasaki rules

The **Hanasaki** flood-control baseline (`examples/fe_walter/rule_based.yaml`, `examples/fe_walter/study/rule/__init__.py`) determines daily release from the reservoir's regulation degree and annual storage state:

- **Regulation ratio**: γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>), comparing reservoir capacity <i>C</i> (m³) against mean annual inflow volume using long-term mean inflow <i>Q&#772;</i><sub>in</sub> (m³/s). Larger storage-to-inflow reservoirs smooth releases using annual storage, whereas run-of-river reservoirs weight current inflow more heavily when γ &lt; 0.5.
- **Annual release coefficient**: `k_rls` = <i>S</i><sub>year_start</sub> / (α · <i>C</i>), refreshed on the first step of each calendar year, with flood-control storage ceiling α · <i>C</i> (default α = 0.85).
- **Operational floors & ceilings**: Enforces a minimum environmental release of 0.1 · <i>Q&#772;</i><sub>in</sub>, clips storage below α · <i>C</i> by releasing excess floodwater, and protects a minimum pool of 0.1 · <i>C</i>.

```yaml
# examples/fe_walter/rule_based.yaml (excerpt)
agents:
  walter_operator:
    reservoir_id: FEWalter
    type: rule_based
    rule: hanasaki
    rule_parameters:
      purpose: flood_control
      alpha: 0.85
      inflow_statistics_file: rule_statistics.json   # 1996-2015 reference inflow stats (or mean_inflow_cms)
    auditors: [release_bounds]
extensions:
  hanasaki: study/rule/__init__.py
```

<div class="callout callout-info" markdown="1">

**Upstream provenance note.** The `flood_control_step` implementation in `examples/fe_walter/study/rule/__init__.py` follows Hanasaki et al. (2006) / Abeshu et al. (2023) and matches the `RiverAI-Project/MOSART-Urban` reference formulation (`scripts/verify_hanasaki_rule.py`, `THIRD_PARTY_NOTICES.md`) inside HydroReOpLLM's neutral SI kernel.

</div>

### Custom extension hook contract

To write your own seasonal guide curve or site-specific Python rule, register a package folder under `extensions:` (pointing to its `__init__.py`) and implement `validate_backend`, `build_backend`, and a `decide(observation)` method with `network_calls = 0`:

```python
# my_rules/__init__.py — minimal ~15-line custom guide-curve rule
class GuideCurveRule:
    network_calls = 0  # Required safeguard: confirms this rule never calls an LLM

    def __init__(self, target_storage_m3, base_release_cms):
        self.target = target_storage_m3
        self.base = base_release_cms

    def decide(self, observation):
        storage = observation["state"]["storage_m3"]
        inflow = observation["inflow_cms"]
        # Release at least inflow above target pool; conserve half base release below target
        release = max(inflow, self.base) if storage > self.target else self.base * 0.5
        return {"release_cms": release}

def validate_backend(spec, **kwargs):
    return {"rule_parameters": spec.get("rule_parameters", {})}, {}

def build_backend(settings, **kwargs):
    p = settings["rule_parameters"]
    return GuideCurveRule(p["target_storage_m3"], p["base_release_cms"])
```

Optional extension capabilities include `rebase_agent` (to resolve relative paths in `rule_parameters`), `preview_backend` (custom offline Day-1 preview), `supported_dt_seconds` (e.g., `(3600,)` for hourly runs), and `supports_prompt_context = True` (to receive `information` profiles and `context_providers`).

## LLM operator YAML schema

In `hydroops-coupled-simulation.v2` (or `v1`), configure each LLM operator under `agents.<agent_id>`. Keep public keys (`reservoir_id`, `type`, `model_profile`, `prompt_file`, `customization`) separate from legacy keys (`reservoir`, `mode`, `strategy`, `model`, `prompt`)—do not mix them in the same agent entry.

| Field path | Values / Format | Hydrological & operational role |
| --- | --- | --- |
| `reservoir_id` | Reservoir key | Exact key under `network.reservoirs` (one agent per controlled dam). |
| `type` | `llm` \| `rule_based` | Selects LLM reasoning vs. deterministic rule. |
| `model_profile` | Key in `models:` | Primary local or cloud LLM profile ([Model providers](MODEL_PROVIDERS.md)). |
| `prompt_file` | Relative `.txt` path | Daily/step user prompt template containing `$observation` and optional placeholders. |
| `auditors` | List of auditor IDs | Diagnostic checks wrapped around the operator (e.g., `[release_bounds]`). |
| `customization.system_prompt_file` | Relative `.txt` path | Standing instructions: dam role, capacity/dead storage, seasonal rules, and JSON output format. |
| `customization.prompt_version` | String (default `'1'`) | Version label to track prompt revisions across experiments. |
| `customization.prompt_variables` | `{name: value}` | Static parameters injected via `$name` (e.g., target pool elevation or dam name). |
| `customization.context_providers` | `{alias: {extension, config, preview}}` | Dynamic Python retrievers (such as selecting applicable DKP rules for today's pool level). |
| `customization.knowledge` | `{pkg_id: path}` | Static operating manual text files injected via `$knowledge`. |
| `customization.context` / `context_file` | Mapping or JSON path | Fixed site metadata included inside `$observation` (`static_context`). |
| `customization.information` | Profile key | Binds a causal [Decision-time information](INFORMATION.md) profile (requires `$information` in prompt). |
| `customization.response_schema` | Schema name | Custom structured JSON output (e.g., reasoning fields + `release_cfs` before SI conversion). |
| `customization.fallback_models` | List of profile keys | Ordered backup models used if the primary model times out or returns invalid JSON. |
| `customization.history_steps` | Integer `>= 0` | Number of previous committed transitions included in `$completed_history`. |
| `customization.execution` | `live` (default) \| `replay` | Switch between live inference and offline deterministic replay (with `customization.backend`). |

```yaml
# Complete commented LLM operator example (split-file v2 layout)
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local                # Defined in models.yaml (e.g., Ollama gemma4:12b)
  prompt_file: prompts/operator.txt   # Daily state & instruction template
  customization:
    system_prompt_file: prompts/system.txt
    prompt_version: '1'
    history_steps: 2                  # Show last 2 days of requested vs. actual release
    information: upstream_and_forecast # Causal gauge/forecast view from information.yaml
    fallback_models: [cloud_backup]
  auditors: [release_bounds]
```

## Prompt anatomy and variable substitution

Effective reservoir LLM prompts combine a **stable System Prompt** (physical constraints, operating priorities, seasonal targets, and output JSON rules) with a **dynamic User Prompt** filled at each timestep using `$placeholder` tokens:

| Placeholder | What it supplies at decision time | Typical hydrological use |
| --- | --- | --- |
| `$observation` | Current `inflow_cms` (m³/s), beginning `storage_m3` (m³), feasible release limit, and `static_context`. | Ground the LLM in exact current pool storage and today's inflow. |
| `$previous_transition` | Previous step's `target_release_cms`, `controlled_release_cms`, `spill_cms`, and `storage_end_m3` (`null` on step 0). | Prevent erratic day-to-day gate swings and show whether yesterday's request was clipped or spilled. |
| `$completed_history` | Last `history_steps` consecutive committed steps. | Give multi-day hydrograph rising/recession context. |
| `$information` | Causal observations, forecasts, seasonal targets, and committed upstream states. | Inject stream gauges, inflow forecasts, or target levels ([Information guide](INFORMATION.md)). |
| `$knowledge` | Contents of files declared under `customization.knowledge`. | Provide compact standing operating procedures. |
| `$<custom>` | Values from `prompt_variables` or `context_providers`. | Inject converted site units (ft, cfs, acre-ft) or retrieved DKP rule excerpts. |

**Design lesson from F.E. Walter (`examples/fe_walter/study/formatter.py`)**:
1. **Work in familiar engineering units**: The F.E. Walter prompt formatter interpolates `storage_m3` against `study/elevation_storage.csv` to report pool level in `ft NGVD29` and converts inflow/previous releases to `cfs` and `acre-ft`.
2. **Seasonal Target vs. DKP**: The *Without operational knowledge* (`seasonal_target`) prompt provides only pool level, seasonal target (`1,300` ft winter / `1,370` ft summer), and 2-day release history. The *With operational knowledge* (`dkp`) prompt retrieves specific rule excerpts from `dkp.md` (`R-RELEASE`, `R-MINNORM`, `R-ATSITE`, `R-ZONE`, plus `R-PLAN` during flood drawdown or `R-RECREATION` in Apr–Oct) so the model reasons explicitly against the water control manual.

## Structured JSON output and unit conversion

By default, HydroReOpLLM expects the LLM to return a strict JSON object with SI release rate:

```json
{"schema_version": "reservoir-action.v1", "release_cms": 12.5}
```

When designing prompts in non-SI units (such as USACE `cfs`), pair a custom `response_schema` (`examples/fe_walter/study/response_schemas.json`) with a response parser that validates diagnostic reasoning fields **before** converting `release_cfs` into SI `release_cms`:

- **F.E. Walter schema fields**: `applicable_target_ft`, `pool_position` (`below_target` | `at_target` | `above_target`), `intended_storage_direction`, `release_relation_to_inflow`, (plus `operating_mode` and `rules_applied` for DKP), `reasoning`, and `release_cfs`.
- **Unit conversion at the boundary**: `_parse_release` multiplies `release_cfs * 0.028316847` (`CFS_TO_CMS`) so the physical water-balance kernel always operates strictly in `m³/s` and `m³`.

## Safety gates, physical clamping, and replay

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Gate 1: Pre-flight & budget gates

- **Zero-cost preview**: `reservoir-experiment check` renders Day-1 prompts and checks all bounds and units before any API request.
- **Explicit network permission**: Live LLM calls execute only when you pass `--allow-network` and the case marks `"live_readiness": {"ready": true}` (or `synthetic_fixture`).
- **Budget cap (`max_calls`)**: Caps total provider calls (including retries and fallbacks) so a misconfigured loop never runs unbounded API billing.

</div>
<div class="panel-card" markdown="1">

### Gate 2: Auditors & physical enforcement

- **Diagnostic auditors (`release_bounds`, `field_range`)**: Check whether the operator's requested release stays within feasible outlet limits or custom ranges and log `PASS` / `WARN` / `FAIL` in `audit.jsonl` without altering flows.
- **Hard physical limits**: The reservoir physics engine always clamps `controlled_release_cms` to `[minimum_release_cms, maximum_release_cms]`, prevents drawdown below `dead_storage_m3`, routes overflow above `capacity_m3` as `spill_cms`, and closes the water balance every step.

</div>
</div>

### Deterministic replay and crash recovery

- **Offline replay**: Archived LLM decision series (`study/archived_releases.csv` or `llm-reservoir-daily`) can be replayed through the exact same reservoir physics and routing network with `0` provider calls to verify metrics or test downstream sensitivity.
- **Crash recovery**: If a long multi-year LLM run stops mid-way, `reservoir-experiment resume` preserves the partial output, replays completed decisions without re-querying the LLM, and continues seamlessly into a fresh output directory.
