# HydroReOpLLM user manual

<div class="hero-band" markdown="1">

**HydroReOpLLM** builds on top of [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) to simulate coupled watershed hydrology, multi-reservoir routing, and reproducible **rule-based** or **LLM-driven** reservoir release decisions inside one water-conserving simulation loop.

[Install and run the template](GETTING_STARTED.md) · [Design operators & LLM agents](AGENT_DESIGN.md) · [F.E. Walter tutorial](../tutorials/README.md) · [繁體中文手冊](README.zh-TW.md)

</div>

## Four-pillar learning path

Follow these four pillars in sequence to build, run, and evaluate a complete reservoir simulation experiment:

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### Pillar 1: HydroCNHS foundation

Supply prepared local inflows (`inflows.csv`) or run a calibrated HydroCNHS catchment model (`GWLF` / `ABCD` + Lohmann routing), bind subbasins without double-counting upstream releases, and align daily or hourly timesteps.

- [Native HydroCNHS hydrology](HYDROLOGY_SETUP.md)
- [Time scales and units](TIME_SCALES.md)
- [Experimental hourly GWLF](HOURLY_GWLF.md)

</div>
<div class="panel-card" markdown="1">

### Pillar 2: Rule & LLM agent design

Define deterministic operating rules (such as Hanasaki flood control or custom seasonal guide curves) or LLM operators with water-control manuals, gauge/forecast inputs, engineering-unit prompts, and safety bounds.

- [Operator & LLM agent design](AGENT_DESIGN.md)
- [Decision-time information](INFORMATION.md)
- [Model providers](MODEL_PROVIDERS.md)

</div>
<div class="panel-card" markdown="1">

### Pillar 3: Coupling & execution

Connect single dams, cascades, flow splits, and channel travel-time lags; mix rule-based and LLM operators in the same basin; preview prompts offline; and verify saved water balances.

- [Configuration files](CONFIGURATION.md)
- [Reservoir networks](MULTI_RESERVOIR.md)
- [Run, verify and resume](RUNNING.md)
- [Read the results](RESULTS_GUIDE.md)

</div>
<div class="panel-card" markdown="1">

### Pillar 4: Case study & reference

Explore the 5-year F.E. Walter Dam study (Hanasaki baseline, Seasonal Target, and Decision Knowledge Package), replay published trajectories offline, or diagnose configuration issues.

- [F.E. Walter Dam study](../examples/fe_walter/README.md)
- [F.E. Walter tutorial](../tutorials/README.md)
- [Troubleshooting](TROUBLESHOOTING.md)

</div>
</div>

## End-to-end architecture

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="Closed-loop HydroReOpLLM and HydroCNHS reservoir operation framework">
  <figcaption><strong>Figure 1.</strong> Coupled HydroCNHS–HydroReOpLLM simulation loop: catchment inflows enter the reservoir node, the operator combines current storage and inflow with seasonal targets, gauges/forecasts, or operating rules (DKP) to request a release, and the host enforces physical storage and outlet bounds before routing water downstream.</figcaption>
</figure>

## Public starting points

| Starting point | Operator & method | Network calls (`check` / `run`) | What it demonstrates |
| --- | --- | --- | --- |
| [Generic prepared-inflow template](../examples/template/README.md) | Fixed offline release (`4.0` & `5.0` m³/s) | `0` / `0` | Two-reservoir cascade (`upper` → `lower` → `outlet`) with routing lags and mass-balance checks. |
| [F.E. Walter — Hanasaki rule](../examples/fe_walter/README.md) | `type: rule_based` (`strategy: hanasaki`, α = 0.85) | `0` / `0` | Offline Hanasaki flood-control rule driven by 1996–2015 reference inflow climatology. |
| [F.E. Walter — Seasonal Target](../examples/fe_walter/README.md) | `type: llm` (`study_method: seasonal_target`) | `0` / `7` (7-day) or `1,826` (full) | LLM control using pool elevation, seasonal target level, and the previous two days' releases. |
| [F.E. Walter — DKP](../examples/fe_walter/README.md) | `type: llm` (`study_method: dkp`) | `0` / `7` (7-day) or `1,826` (full) | Same physical basin augmented with a structured Decision Knowledge Package (`dkp.md`) of operating rules. |

<div class="callout callout-info" markdown="1">

**Check offline before running.** `reservoir-experiment check` validates all file paths, dates, inflow tables, routing weights, and Day-1 prompt previews at zero model cost. Live LLM calls run only when you pass `--allow-network` and mark the physical case ready.

</div>

## Complete chapter map

| Pillar | Chapter | Primary focus |
| --- | --- | --- |
| Start | [Installation and first run](GETTING_STARTED.md) | Python 3.12 setup, exporting bundled examples, and running the offline template. |
| Start | [Generic prepared-inflow template](../examples/template/README.md) | Field-by-field walkthrough of `experiment.yaml`, `case.json`, and `inflows.csv`. |
| Hydrology | [Native HydroCNHS hydrology](HYDROLOGY_SETUP.md) | Prepared inflows vs. coupled HydroCNHS (`hydrology.yaml`), spin-up, and catchment bindings. |
| Hydrology | [Time scales and units](TIME_SCALES.md) | Native units (`m3`, `m3/s`, `dt_seconds`), precipitation/PET depth rules, and output aggregation. |
| Hydrology | [Experimental hourly GWLF](HOURLY_GWLF.md) | Sub-daily `run_GWLF_hourly` workflow (`3600`, `1800`, `900` s), state continuity, and diagnostics. |
| Operator & LLM | [Operator & LLM agent design](AGENT_DESIGN.md) | Hanasaki & custom Python rules, LLM prompt design, unit conversions, and physical safety gates. |
| Operator & LLM | [Decision-time information](INFORMATION.md) | Feeding gauges, forecasts, guide curves, and upstream reservoir states without future leakage. |
| Operator & LLM | [Model providers](MODEL_PROVIDERS.md) | Ready-to-copy YAML profiles for Ollama, OpenAI, Gemini, Anthropic, and OpenAI-compatible APIs. |
| Coupling & Execution | [Configuration files](CONFIGURATION.md) | Single-file vs. split-file YAML layout, top-level keys, and `outcome_checks`. |
| Coupling & Execution | [Reservoir networks](MULTI_RESERVOIR.md) | Cascades, split fractions, unit-hydrograph lags, passive weirs, and hybrid Rule + LLM basins. |
| Coupling & Execution | [Run, verify and resume](RUNNING.md) | CLI workflow (`check`, `prepare`, `run`, `verify`, `resume`), budgets, and offline replay. |
| Coupling & Execution | [Read the results](RESULTS_GUIDE.md) | Interpreting `summary.json`, reservoir trajectories, routed hydrographs, and water-balance tables. |
| Case Study | [F.E. Walter Dam](../examples/fe_walter/README.md) | 2021–2025 daily & seasonal benchmarks (Figures 2–4), offline replay, and live Ollama runs. |
| Reference | [Troubleshooting](TROUBLESHOOTING.md) | Common hydrological, YAML, provider, and verification fixes. |
