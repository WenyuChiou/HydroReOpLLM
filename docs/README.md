# HydroReOpLLM user manual

<div class="hero-band" markdown="1">

**HydroReOpLLM** builds on [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) to simulate watershed runoff, reservoir operations, and downstream routing using deterministic rules or LLMs.

[Install & first run](GETTING_STARTED.md) · [Rules & LLM prompts](AGENT_DESIGN.md) · [F.E. Walter notebook](../tutorials/README.md) · [繁體中文手冊](README.zh-TW.md)

</div>

## Four-step learning map

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### Step 1: Watershed & hydrology

Prepare local inflows or run HydroCNHS catchments.

- [Inflows & HydroCNHS](HYDROLOGY_SETUP.md)
- [Time scales & units](TIME_SCALES.md)
- [Hourly GWLF (experimental)](HOURLY_GWLF.md)

</div>
<div class="panel-card" markdown="1">

### Step 2: Reservoir operators

Configure Hanasaki rules, custom Python rules, or LLM prompts.

- [Rules & LLM prompts](AGENT_DESIGN.md)
- [Gauges & forecasts](INFORMATION.md)
- [Model providers](MODEL_PROVIDERS.md)

</div>
<div class="panel-card" markdown="1">

### Step 3: Build & run

Connect multi-reservoir networks, run simulations, and inspect results.

- [Experiment setup](CONFIGURATION.md)
- [Multi-reservoir networks](MULTI_RESERVOIR.md)
- [Run, verify & resume](RUNNING.md)
- [Reading results](RESULTS_GUIDE.md)

</div>
<div class="panel-card" markdown="1">

### Step 4: Case study & help

Reproduce the F.E. Walter study and fix common errors.

- [F.E. Walter Dam](../examples/fe_walter/README.md)
- [F.E. Walter notebook](../tutorials/README.md)
- [Troubleshooting](TROUBLESHOOTING.md)

</div>
</div>

## How the coupled loop works

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="Closed-loop HydroReOpLLM and HydroCNHS reservoir operation framework">
  <figcaption><strong>Figure 1.</strong> Coupled HydroCNHS–HydroReOpLLM loop: watershed inflows and reservoir storage feed a rule or LLM operator, and the water-balance engine enforces outlet bounds and spill before routing downstream.</figcaption>
</figure>

## Starter examples

| Example | Operator & method | Network calls (`check` / `run`) | What it demonstrates |
| --- | --- | --- | --- |
| [Two-reservoir template](../examples/template/README.md) | Fixed release (`4.0` & `5.0` m³/s) | `0` / `0` | Two-reservoir cascade (`upper` → `lower` → `outlet`) with routing lags. |
| [Rule-based](../examples/fe_walter/README.md) | `type: rule_based` (`hanasaki`, α = 0.85) | `0` / `0` | Offline Hanasaki flood-control baseline on F.E. Walter (`rule_based.yaml`). |
| [Without operational knowledge](../examples/fe_walter/README.md) | `type: llm` (`seasonal_target.yaml`) | `0` / `7` (7-day) or `1,826` (full) | LLM release using pool elevation, seasonal target, and 2-day history. |
| [With operational knowledge](../examples/fe_walter/README.md) | `type: llm` (`dkp.yaml`) | `0` / `7` (7-day) or `1,826` (full) | Same case with structured operating manual retrieval (`dkp.md`). |

<div class="callout callout-info" markdown="1">

**Check offline first.** `reservoir-experiment check` validates files, dates, inflows, and Day-1 prompt previews at zero model cost; live LLM calls run only with `--allow-network`.

</div>
