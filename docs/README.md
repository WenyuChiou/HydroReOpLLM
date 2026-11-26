# HydroReOpLLM overview

<div class="hero-band" markdown="1">

**HydroReOpLLM** extends [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) with a unified, water-conserving simulation framework for coupling subbasin rainfall–runoff, river routing, and reservoir operations—making it straightforward to compare deterministic **Rule-based** policies against **LLM** operators on the exact same watershed.

[Installation & CLI](GETTING_STARTED.md) · [Rules & LLM prompts](AGENT_DESIGN.md) · [Interactive notebook](../tutorials/README.md) · [繁體中文總覽](README.zh-TW.md)

</div>

## When to use HydroReOpLLM

- Compare **Rule-based** baselines (such as Hanasaki flood control or custom Python rules) against **LLM** operators on identical hydrology and routing.
- Encode seasonal pool targets, operating rules, or water control manuals into structured prompts and test how operational knowledge changes reservoir performance.
- Simulate single reservoirs or multi-reservoir cascades mixing rule-based and LLM agents in the same basin.
- Verify water balance, routing lags, and time-ordered gauge/forecast inputs offline before running live model inference.

## Three core building blocks

<div class="panel-grid panel-grid-3" markdown="1">
<div class="panel-card" markdown="1">

### Hydrology & routing

Supply prepared incremental local inflows (`inflows.csv`) or couple directly to a calibrated HydroCNHS catchment model (`GWLF`/`ABCD` + Lohmann routing) with multi-step channel lags.

</div>
<div class="panel-card" markdown="1">

### Operators: Rule-based & LLM

Attach one isolated operator per controlled reservoir—Hanasaki flood control, custom Python guide curves, or local Ollama / cloud LLMs using structured prompts and JSON replies.

</div>
<div class="panel-card" markdown="1">

### Physical limits & verification

Enforce outlet bounds (`[min, max]`), dead storage, and uncontrolled spill inside one shared water-balance engine, with offline `check` previews and post-run `verify` audits.

</div>
</div>

## How the coupled loop works

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="Closed-loop HydroReOpLLM and HydroCNHS reservoir operation framework">
  <figcaption><strong>Figure 1.</strong> Coupled HydroCNHS–HydroReOpLLM simulation loop: watershed inflows and beginning reservoir storage feed a rule or LLM operator, and the water-balance engine enforces outlet bounds and spill before routing water downstream.</figcaption>
</figure>

## Manual map

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### Installation & workflow

Install Python 3.12+, configure experiments, and verify outputs.

- [Installation & CLI](GETTING_STARTED.md)
- [Experiment setup](CONFIGURATION.md)
- [Run, verify & resume](RUNNING.md)
- [Reading results](RESULTS_GUIDE.md)

</div>
<div class="panel-card" markdown="1">

### Watershed & hydrology

Connect inflows, HydroCNHS catchments, river networks, and timesteps.

- [Inflows & HydroCNHS](HYDROLOGY_SETUP.md)
- [Multi-reservoir networks](MULTI_RESERVOIR.md)
- [Time scales & units](TIME_SCALES.md)
- [Hourly GWLF (experimental)](HOURLY_GWLF.md)

</div>
<div class="panel-card" markdown="1">

### Reservoir operators

Design Hanasaki rules, custom Python rules, prompts, gauges, and models.

- [Rules & LLM prompts](AGENT_DESIGN.md)
- [Gauges & forecasts](INFORMATION.md)
- [Model providers](MODEL_PROVIDERS.md)

</div>
<div class="panel-card" markdown="1">

### Examples & tutorials

Run the single-reservoir and multi-reservoir cases or troubleshoot errors.

- [Single-reservoir case (F.E. Walter)](../examples/fe_walter/README.md)
- [Interactive notebook](../tutorials/README.md)
- [Multi-reservoir case](../examples/multi_reservoir/README.md)
- [Troubleshooting](TROUBLESHOOTING.md)

</div>
</div>

## Included examples

| Example | Operator & config | Execution | What it demonstrates |
| --- | --- | --- | --- |
| [Single-reservoir: Rule-based](../examples/fe_walter/README.md) | Hanasaki (`α = 0.85`, `rule_based.yaml`) | Offline | Offline F.E. Walter Dam baseline over 2021–2025 inflows. |
| [Single-reservoir: Without operational knowledge](../examples/fe_walter/README.md) | LLM (`seasonal_target.yaml`) | Local Ollama | Pool elevation, seasonal target, and 2-day release history only. |
| [Single-reservoir: With operational knowledge](../examples/fe_walter/README.md) | LLM (`dkp.yaml`) | Local Ollama | Same physical case with structured water-control manual (`dkp.md`). |
| [Multi-reservoir: Rule-based](../examples/multi_reservoir/README.md) | Hanasaki on both dams (`rule_based.yaml`) | Offline | Taiwan Xindian River cascade (`feitsui` → `zhitan` → `xindian_outlet`, May 2020 Mei-Yu front). |
| [Multi-reservoir: Hybrid LLM](../examples/multi_reservoir/README.md) | Upstream Hanasaki + downstream LLM (`hybrid_llm.yaml`) | Local Ollama | Mixed `feitsui` Hanasaki + `zhitan` LLM cascade (`prompts/operator.txt`). |

<div class="callout callout-info" markdown="1">

**Check offline first.** `reservoir-experiment check` validates files, dates, inflows, and Day-1 prompt previews at zero model cost; live LLM calls run only with `--allow-network`.

</div>
