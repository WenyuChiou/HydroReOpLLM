# Rules and LLM operator design

<div class="hero-band" markdown="1">

HydroReOpLLM separates **operating decisions** (a deterministic rule or an LLM) from **physical water balance** (the shared HydroCNHS reservoir and river-routing engine).

</div>

## Decision vs. water-balance boundary

At every timestep, the water-balance engine delivers routed inflow and beginning storage to the reservoir operator, receives a requested release (`m³/s`), enforces outlet limits and spill, and routes `controlled_release_cms + spill_cms` downstream. Because operators never alter storage directly, you can compare **Rule-based**, **Without operational knowledge**, and **With operational knowledge** on the exact same basin.

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="Closed-loop reservoir operation architecture integrating HydroCNHS and LLM/rule agents">
  <figcaption><strong>Figure 1.</strong> Closed-loop coupling: watershed runoff enters the reservoir, the rule or LLM operator proposes a release, and the water-balance engine enforces storage and outlet limits before routing downstream.</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. Inflow</strong>Local + upstream runoff (m³/s)</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. State</strong>Storage (m³) &amp; bounds</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. Context</strong>Gauges, forecasts &amp; guidance</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. Prompt</strong>Fill templates</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. Decide</strong>Rule or LLM</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. Parse</strong>JSON &amp; convert to m³/s</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. Audit</strong>Check bounds</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. Water balance</strong>Limits, spill &amp; route</div>
</div>

In addition to current storage and inflow, an LLM operator can receive **operational knowledge**—structured excerpts from a dam's water control manual (such as `dkp.md` in F.E. Walter)—alongside gauge observations and forecasts. Each timestep runs eight stages:

| Stage | Hydrological action | Output & unit |
| --- | --- | --- |
| 1. Basin & upstream inflow | Adds local runoff to lagged upstream outflows. | `inflow_cms` (`m³/s`) |
| 2. Reservoir observation | Reads beginning storage and feasible outlet ceiling. | `storage_m3` (`m³`), `release_upper_bound_cms` (`m³/s`) |
| 3. Gauges, forecasts & operational knowledge | Attaches allowed gauges, forecasts, or water-control manual excerpts. | Read-only context |
| 4. Prompt formatting | Inserts state, history, and context into templates. | Prompt messages (LLM only) |
| 5. Operator decision | Evaluates a rule formula or queries the LLM. | Proposed release (`m³/s` or site units) |
| 6. Parse & unit conversion | Extracts JSON and converts site units (e.g., `cfs`) to SI. | `target_release_cms` (`m³/s`) |
| 7. Diagnostic check | Flags bound or range violations without changing flow. | `PASS` / `WARN` / `FAIL` / `UNKNOWN` |
| 8. Water balance & routing | Clamps `[min, max]` and `dead_storage_m3`, computes `spill_cms`, and routes. | `controlled_release_cms`, `spill_cms`, `storage_end_m3` |

## Rule-based operators and custom Python rules

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based` (Operating rule)

- Requires `reservoir_id`, `type: rule_based`, `rule`, and optional `rule_parameters`.
- Runs offline for Hanasaki baselines or custom Python rules.

</div>
<div class="panel-card" markdown="1">

### `type: llm` (LLM operator)

- Requires `reservoir_id`, `type: llm`, `model_profile`, `prompt_file`, and `customization:`.
- Uses `--allow-network` for `execution: live`, or runs offline with `execution: replay`.

</div>
</div>

### Hanasaki flood-control rule

The **Rule-based** Hanasaki baseline ([Hanasaki et al., 2006](https://doi.org/10.1016/j.jhydrol.2005.11.011) / Abeshu et al., 2023) sets daily release from five physical quantities:

| Parameter / Rule | Formula / Value | Hydrological meaning |
| --- | --- | --- |
| Regulation ratio | γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>) | Capacity <i>C</i> divided by mean annual inflow volume (weights current inflow when γ &lt; 0.5). |
| Release coefficient | `k_rls` = <i>S</i><sub>year_start</sub> / (α · <i>C</i>) | Annual storage ratio refreshed at the start of each calendar year (default α = 0.85). |
| Minimum release | 0.1 · <i>Q&#772;</i><sub>in</sub> | Environmental flow floor based on long-term mean inflow. |
| Minimum storage | 0.1 · <i>C</i> | Protected minimum pool fraction. |
| Flood-control ceiling | α · <i>C</i> | Operating storage cap; excess inflow above α · <i>C</i> is released. |

HydroReOpLLM provides two ways to configure Hanasaki depending on your workflow:

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Built-in `strategy: benchmark` (multi-reservoir)

Used in `examples/multi_reservoir/rule_based.yaml` (`feitsui` & `zhitan`) and `hybrid_llm.yaml` (`zhitan`) with no `extensions:` needed:

```yaml
zhitan_operator:
  reservoir: zhitan
  mode: offline
  strategy: benchmark
  benchmark:
    statistics: zhitan_statistics.json
    purpose: flood_control
    alpha: 0.85
```

</div>
<div class="panel-card" markdown="1">

### Paper rule extension `rule: hanasaki` (F.E. Walter)

Used in `examples/fe_walter/rule_based.yaml` when strictly matching physical non-clipping bounds:

```yaml
agents:
  walter_operator:
    reservoir_id: FEWalter
    type: rule_based
    rule: hanasaki
    rule_parameters: { purpose: flood_control, alpha: 0.85, inflow_statistics_file: rule_statistics.json }
extensions:
  hanasaki: study/rule/__init__.py
```

</div>
</div>

### Write a custom Python operating rule

Place your rule in a folder (`my_rules/__init__.py`), register it under `extensions:`, and return `{"release_cms": ...}` from `decide(observation)` with `network_calls = 0`:

```python
class GuideCurveRule:
    network_calls = 0
    def __init__(self, target_storage_m3, base_release_cms):
        self.target, self.base = target_storage_m3, base_release_cms
    def decide(self, observation):
        s, q_in = observation["state"]["storage_m3"], observation["inflow_cms"]
        return {"release_cms": max(q_in, self.base) if s > self.target else self.base * 0.5}

def validate_backend(spec, **kwargs):
    return {"rule_parameters": spec.get("rule_parameters", {})}, {}

def build_backend(settings, **kwargs):
    p = settings["rule_parameters"]
    return GuideCurveRule(p["target_storage_m3"], p["base_release_cms"])
```

## LLM operator YAML setup

Keep public keys (`reservoir_id`, `type`, `model_profile`, `prompt_file`, `customization`) separate from legacy keys (`reservoir`, `mode`, `strategy`, `model`, `prompt`) in any agent entry.

| YAML field | Purpose |
| --- | --- |
| `reservoir_id` | Reservoir key under `network.reservoirs`. |
| `type` | `llm` or `rule_based`. |
| `model_profile` | Profile key defined in `models.yaml` ([Model providers](MODEL_PROVIDERS.md)). |
| `prompt_file` | Daily/step user prompt template (`.txt`). |
| `customization.system_prompt_file` | Standing dam rules, pool targets, and JSON format instructions. |
| `customization.prompt_variables` / `context` | Fixed site values (`$var`) or static JSON attached to `$observation`. |
| `customization.knowledge` / `context_providers` | Operating manual files (`$knowledge`) or dynamic rule retrievers. |
| `customization.information` | Named gauge/forecast view ([Gauges & forecasts](INFORMATION.md); requires `$information`). |
| `customization.history_steps` | Number of prior committed steps included in `$completed_history`. |
| `customization.response_schema` | Custom JSON reply schema (e.g., reasoning + `release_cfs` before SI conversion). |
| `customization.fallback_models` | Backup model profiles tried on timeouts, `429`/`5xx`, or parse errors. |
| `customization.execution` | `live` (default) or `replay` when paired with a custom `backend`. |
| `auditors` | Diagnostic checks (e.g., `[release_bounds]`) logged per step. |

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    history_steps: 2
    information: upstream_and_forecast
    fallback_models: [cloud_backup]
  auditors: [release_bounds]
```

## Concrete prompt and JSON reply example

Below is a minimal end-to-end prompt pair and model reply showing how placeholders connect to the release decision:

**1. `prompts/system.txt`** (standing rules & output format):

```text
You operate Lake A (capacity 8,000,000 m3, dead storage 200,000 m3, target 4,500,000 m3).
Keep storage near target while limiting abrupt release jumps.
Reply ONLY with JSON: {"schema_version": "reservoir-action.v1", "release_cms": <number >= 0>}.
```

**2. `prompts/operator.txt`** (filled at each timestep):

```text
Current observation (m3/s, m3): $observation
Previous committed step: $previous_transition
Gauges and forecasts: $information
Choose today's controlled release_cms.
```

**3. Valid JSON replies** (default SI vs. F.E. Walter site units):

```json
{"schema_version": "reservoir-action.v1", "release_cms": 12.5}
```

```json
{
  "applicable_target_ft": 1300.0,
  "pool_position": "above_target",
  "reasoning": "Pool is above winter target; release slightly above inflow to draw down gradually.",
  "release_cfs": 441.4
}
```

For site-unit schemas (`examples/fe_walter/study/response_schemas.json`), the parser validates every field and converts `release_cfs × 0.028316847` into SI `release_cms` before water balance runs.

| Placeholder | Value injected at decision time |
| --- | --- |
| `$observation` | Current `inflow_cms` (`m³/s`), `storage_m3` (`m³`), release limit, and static context. |
| `$previous_transition` | Prior step's requested release, implemented release, spill, and ending storage. |
| `$completed_history` | List of the last `history_steps` committed steps. |
| `$information` | Selected gauges, forecasts, and committed upstream states. |
| `$knowledge` | Contents of static manual files under `customization.knowledge`. |
| `$<custom>` | Values from `prompt_variables` or `context_providers`. |

**F.E. Walter prompt design lessons (`examples/fe_walter/study/formatter.py`)**:

- **Use site engineering units**: Convert `storage_m3` via `elevation_storage.csv` into `ft NGVD29` and flows into `cfs` / `acre-ft`.
- **Without operational knowledge** (`seasonal_target.yaml`): Supplies only pool level, seasonal target (`1,300` ft winter / `1,370` ft summer), and 2-day release history.
- **With operational knowledge** (`dkp.yaml`): Adds relevant rules from `dkp.md` (`R-RELEASE`, `R-MINNORM`, `R-ATSITE`, `R-ZONE`, plus `R-PLAN` or `R-RECREATION`) for explicit rule citations.

## Safety checks, physical limits, and offline replay

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Gate 1: Pre-flight & budget

- `reservoir-experiment check` previews Day-1 prompts at `0` cost.
- Live runs require `--allow-network`, `"live_readiness": {"ready": true}` (or synthetic fixture), and `max_calls`.

</div>
<div class="panel-card" markdown="1">

### Gate 2: Diagnostic checks & water balance

- Auditors (`release_bounds`, `field_range`) log `PASS`/`WARN`/`FAIL` without altering releases.
- Water-balance physics clamps `[minimum_release_cms, maximum_release_cms]`, protects `dead_storage_m3`, and spills above `capacity_m3`.

</div>
</div>

Use `examples/fe_walter/study/replay.py` or `llm-reservoir-daily` for zero-cost offline replay, and `reservoir-experiment resume` to continue interrupted runs without re-querying completed steps.
