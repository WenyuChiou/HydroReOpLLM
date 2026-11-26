# Operator and LLM agent design

<div class="hero-band" markdown="1">

HydroReOpLLM separates **what decides** (a rule or an LLM) from **what conserves water** (the shared HydroCNHS `Dam` mass-balance and routing engine).

</div>

## Architectural boundary with HydroCNHS

HydroReOpLLM connects to HydroCNHS's `Dam` interface (`examples/llm_reservoir_abm.py`): HydroCNHS passes routed inflow and beginning storage to the operator and routes `controlled_release_cms + spill_cms` downstream. Because operators never edit storage directly, you can swap between **Rule-based**, **Without operational knowledge**, and **With operational knowledge** on the exact same watershed.

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="Closed-loop reservoir operation architecture integrating HydroCNHS and LLM/rule agents">
  <figcaption><strong>Figure 1.</strong> Closed-loop coupling: watershed runoff enters the reservoir, the rule or LLM operator proposes a release, and host physics enforces storage and outlet bounds before routing downstream.</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. Inflow</strong>Local + upstream runoff (m³/s)</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. State</strong>Storage (m³) &amp; bounds</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. Context</strong>Gauges, forecasts &amp; rules</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. Prompt</strong>Fill templates</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. Decide</strong>Rule or LLM</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. Parse</strong>JSON &amp; convert to m³/s</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. Audit</strong>Check bounds</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. Physics</strong>Limits, spill &amp; route</div>
</div>

## Per-timestep coupling data flow

| Stage | Hydrological action | Output & unit |
| --- | --- | --- |
| 1. Basin & upstream inflow | Adds local runoff to lagged upstream outflows. | `inflow_cms` (`m³/s`) |
| 2. Reservoir observation | Reads beginning pool volume and outlet capacity. | `storage_m3` (`m³`), `release_upper_bound_cms` (`m³/s`) |
| 3. Info & DKP retrieval | Attaches causal gauges, forecasts, or DKP rules. | Read-only context |
| 4. Prompt formatting | Inserts state, history, and context into templates. | Prompt messages (LLM only) |
| 5. Operator decision | Evaluates rule equation or queries LLM provider. | Proposed release (`m³/s` or site units) |
| 6. Parse & unit conversion | Parses JSON and converts site units (e.g., `cfs`) to SI. | `target_release_cms` (`m³/s`) |
| 7. Diagnostic audit | Flags bound or range violations without changing flow. | `PASS` / `WARN` / `FAIL` / `UNKNOWN` |
| 8. Host physics & routing | Clamps `[min, max]` and `dead_storage_m3`, computes `spill_cms`, and routes. | `controlled_release_cms`, `spill_cms`, `storage_end_m3` |

## Rule-based operators and Python extensions

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based` (Deterministic rule)

- Requires `reservoir_id`, `type: rule_based`, `rule`, and optional `rule_parameters`.
- Runs strictly offline (`0` calls) for Hanasaki baselines or custom Python rules.

</div>
<div class="panel-card" markdown="1">

### `type: llm` (Model-driven operator)

- Requires `reservoir_id`, `type: llm`, `model_profile`, `prompt_file`, and `customization:`.
- Uses `--allow-network` for `execution: live`, or `0` calls for `execution: replay`.

</div>
</div>

### Built-in and extension Hanasaki rules

The **Rule-based** Hanasaki baseline (`examples/fe_walter/rule_based.yaml`) computes release from regulation degree γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>) and annual coefficient `k_rls` = <i>S</i><sub>year_start</sub> / (α · <i>C</i>) (refreshed each calendar year, default α = 0.85), enforcing minimum flow 0.1 · <i>Q&#772;</i><sub>in</sub>, minimum pool 0.1 · <i>C</i>, and flood-control ceiling α · <i>C</i>.

```yaml
agents:
  walter_operator:
    reservoir_id: FEWalter
    type: rule_based
    rule: hanasaki
    rule_parameters: { purpose: flood_control, alpha: 0.85, inflow_statistics_file: rule_statistics.json }
    auditors: [release_bounds]
extensions:
  hanasaki: study/rule/__init__.py
```

<div class="callout callout-info" markdown="1">

**Attribution.** `flood_control_step` follows Hanasaki et al. (2006) / Abeshu et al. (2023) and matches `RiverAI-Project/MOSART-Urban` (`scripts/verify_hanasaki_rule.py`, `THIRD_PARTY_NOTICES.md`).

</div>

### Custom extension hook contract

Register your own rule package under `extensions:` with `validate_backend`, `build_backend`, and `network_calls = 0`:

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

## LLM operator YAML schema

Keep public keys (`reservoir_id`, `type`, `model_profile`, `prompt_file`, `customization`) separate from legacy keys (`reservoir`, `mode`, `strategy`, `model`, `prompt`).

| Field | Role |
| --- | --- |
| `reservoir_id`, `type`, `model_profile`, `prompt_file`, `auditors` | Reservoir target, `llm` mode, provider key ([Providers](MODEL_PROVIDERS.md)), user template, and auditors. |
| `customization.system_prompt_file`, `prompt_version` | Standing reservoir rules/JSON instructions and revision label. |
| `customization.prompt_variables`, `context` / `context_file` | Fixed values (`$var`) or static site JSON inside `$observation`. |
| `customization.knowledge`, `context_providers` | Operating manual files (`$knowledge`) or dynamic rule retrievers. |
| `customization.information` | Causal gauge/forecast view ([Information](INFORMATION.md); requires `$information`). |
| `customization.response_schema`, `fallback_models`, `history_steps` | Custom JSON schema, backup models, and prior step count (`$completed_history`). |
| `customization.execution` (`live` \| `replay`), `backend`, `parameters` | Switch between live inference and deterministic replay for custom backends. |

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

## Prompt anatomy and variable substitution

| Placeholder | Content injected at each timestep |
| --- | --- |
| `$observation` | Current `inflow_cms` (`m³/s`), `storage_m3` (`m³`), release upper bound, and static context. |
| `$previous_transition`, `$completed_history` | Last step (or last `history_steps` steps) of requested vs. actual release and spill. |
| `$information`, `$knowledge`, `$<custom>` | Causal gauges/forecasts, static manuals, or custom engineering-unit variables. |

**Design lesson from F.E. Walter (`examples/fe_walter/study/formatter.py`)**:

- **Use familiar site units**: Convert `storage_m3` via `elevation_storage.csv` into `ft NGVD29` and flows into `cfs` / `acre-ft`.
- **Without operational knowledge** (`seasonal_target.yaml`): Supplies only pool level, seasonal target (`1,300` ft winter / `1,370` ft summer), and 2-day release history.
- **With operational knowledge** (`dkp.yaml`): Injects relevant rules from `dkp.md` (`R-RELEASE`, `R-MINNORM`, `R-ATSITE`, `R-ZONE`, plus `R-PLAN` or `R-RECREATION`) for explicit rule citations.

## Structured JSON output and unit conversion

- Default responses return `{"schema_version": "reservoir-action.v1", "release_cms": <float >= 0>}`.
- Custom `response_schema` files (`study/response_schemas.json`) can require reasoning fields plus `release_cfs`, converting `release_cfs * 0.028316847` into SI `release_cms` before physics runs.

## Safety gates, physical clamping, and replay

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Gate 1: Pre-flight & budget gates

- `reservoir-experiment check` previews Day-1 prompts at `0` cost.
- Live runs require `--allow-network`, `"live_readiness": {"ready": true}` (or synthetic fixture), and `max_calls`.

</div>
<div class="panel-card" markdown="1">

### Gate 2: Auditors & physical enforcement

- Auditors (`release_bounds`, `field_range`) log `PASS`/`WARN`/`FAIL` without altering releases.
- Host physics clamps `[minimum_release_cms, maximum_release_cms]`, protects `dead_storage_m3`, and spills above `capacity_m3`.

</div>
</div>

Use `examples/fe_walter/study/replay.py` or `llm-reservoir-daily` for zero-cost offline replay, and `reservoir-experiment resume` to continue interrupted runs without re-querying completed steps.
