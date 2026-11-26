# HydroReOpLLM user manual

<div class="hero-band" markdown="1">

**HydroReOpLLM** builds on top of [HydroCNHS](https://github.com/philip928lin/HydroCNHS) to simulate coupled watershed hydrology, multi-reservoir routing, and reproducible **rule-based** or **LLM-driven** reservoir release decisions under one auditable water-balance kernel.

[Install and run the template](GETTING_STARTED.md) · [Design operators & LLM agents](AGENT_DESIGN.md) · [F.E. Walter tutorial](../tutorials/README.md) · [繁體中文手冊](README.zh-TW.md)

</div>

## Four-pillar learning path

Design an entire experiment end-to-end by following the four pillars in sequence:

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### Pillar 1: HydroCNHS foundation

Prepare daily or sub-daily local inflows via `inflows.csv` or native HydroCNHS (`GWLF` / `ABCD` + Lohmann routing), bind catchments without double counting, and verify clock alignment.

- [Native HydroCNHS hydrology](HYDROLOGY_SETUP.md)
- [Time scales and units](TIME_SCALES.md)
- [Experimental hourly GWLF](HOURLY_GWLF.md)

</div>
<div class="panel-card" markdown="1">

### Pillar 2: Rule & LLM agent design

Configure deterministic rules (such as Hanasaki flood control) or LLM operators with structured prompts, causal information catalogs, JSON schemas, and release-bound auditors.

- [Operator & LLM agent design](AGENT_DESIGN.md)
- [Decision-time information](INFORMATION.md)
- [Model providers](MODEL_PROVIDERS.md)

</div>
<div class="panel-card" markdown="1">

### Pillar 3: Coupling & execution

Assemble single-file or split-file YAML configurations, wire single or hybrid multi-reservoir cascades, enforce network gates, and verify durable step-level provenance.

- [Configuration files](CONFIGURATION.md)
- [Reservoir networks](MULTI_RESERVOIR.md)
- [Run, verify and resume](RUNNING.md)
- [Read the results](RESULTS_GUIDE.md)

</div>
<div class="panel-card" markdown="1">

### Pillar 4: Case study & reference

Reproduce the 21-run F.E. Walter Dam benchmark offline (Hanasaki, Seasonal Target, and DKP), inspect saved trajectories, or diagnose validation errors.

- [F.E. Walter Dam study](../examples/fe_walter/README.md)
- [F.E. Walter tutorial](../tutorials/README.md)
- [Troubleshooting](TROUBLESHOOTING.md)

</div>
</div>

## End-to-end architecture

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="Closed-loop HydroReOpLLM and HydroCNHS reservoir operation framework">
  <figcaption><strong>Figure 1.</strong> Coupled HydroCNHS–HydroReOpLLM simulation loop: watershed inflows and beginning reservoir state enter observation formatting and causal information/DKP retrieval, pass to either a deterministic rule or an LLM provider, return a structured release request converted into SI units, and close the mass balance through host physics and downstream routing.</figcaption>
</figure>

## Public starting points

| Starting point | Operator & method | Network calls (`check` / `run`) | What it demonstrates |
| --- | --- | --- | --- |
| [Generic prepared-inflow template](../examples/template/README.md) | `mode: offline` (`4.0` & `5.0` m3/s) | `0` / `0` | Two-reservoir cascade (`upper` → `lower` → `outlet`) with routing lags and water-balance checks. |
| [F.E. Walter — Hanasaki rule](../examples/fe_walter/README.md) | `type: rule_based` (`strategy: hanasaki`, α = 0.85) | `0` / `0` | Offline Hanasaki flood-control rule pinned to 1996–2015 reference inflow statistics. |
| [F.E. Walter — Seasonal Target](../examples/fe_walter/README.md) | `type: llm` (`study_method: seasonal_target`) | `0` / `7` (7-day) or `1,826` (full) | LLM control using elevation–storage state, seasonal pool target, and 2-step committed feedback. |
| [F.E. Walter — DKP](../examples/fe_walter/README.md) | `type: llm` (`study_method: dkp`) | `0` / `7` (7-day) or `1,826` (full) | Same physical case augmented with a Decision Knowledge Package (`dkp.md`) and rule-citation schema. |

<div class="callout callout-info" markdown="1">

**Zero-cost validation first.** `reservoir-experiment check` validates schemas, SHA-256 input pins, network topology, and rendered prompt previews offline for all starting points. Live LLM execution requires an explicit `--allow-network` flag and a case marked `"live_readiness": {"ready": true}` (or `synthetic_fixture`).

</div>

## Complete chapter map

| Pillar | Chapter | Primary focus |
| --- | --- | --- |
| Start | [Installation and first run](GETTING_STARTED.md) | Python 3.12 setup, `init-examples`, and running the offline template. |
| Start | [Generic prepared-inflow template](../examples/template/README.md) | Field-by-field walkthrough of `experiment.yaml`, `case.json`, and `inflows.csv`. |
| Hydrology | [Native HydroCNHS hydrology](HYDROLOGY_SETUP.md) | `hydrology.yaml`, GWLF/ABCD + Lohmann setup, `ModelBuilder`, `Dam` links, and balance checks. |
| Hydrology | [Time scales and units](TIME_SCALES.md) | SI kernel units (`m3`, `m3/s`, `dt_seconds`), depth-to-rate rules, and output aggregation. |
| Hydrology | [Experimental hourly GWLF](HOURLY_GWLF.md) | Sub-daily `run_GWLF_hourly` API (`3600`, `1800`, `900` s), state continuity, and diagnostics. |
| Operator & LLM | [Operator & LLM agent design](AGENT_DESIGN.md) | `LLMReservoirAgent` callbacks, Hanasaki rules, LLM YAML customization, prompts, JSON contracts, and safety gates. |
| Operator & LLM | [Decision-time information](INFORMATION.md) | `InformationCatalog`, causal `valid_time`/`available_at`/`issued_at` guards, and unit conversions. |
| Operator & LLM | [Model providers](MODEL_PROVIDERS.md) | `ollama`, `openai`, `openai_compatible`, `anthropic`, and `gemini` settings, retries, fallbacks, and identity. |
| Coupling & Execution | [Configuration files](CONFIGURATION.md) | `v1`/`v2` YAML schemas, `{file: ...}` composition, `UniqueLoader` rules, and `outcome_checks`. |
| Coupling & Execution | [Reservoir networks](MULTI_RESERVOIR.md) | Topologies, split fractions, unit hydrographs, and hybrid Hanasaki + LLM cascades. |
| Coupling & Execution | [Run, verify and resume](RUNNING.md) | CLI subcommands (`check`, `prepare`, `run`, `verify`, `resume`), `max_calls`, and replay. |
| Coupling & Execution | [Read the results](RESULTS_GUIDE.md) | `summary.json`, trajectory/flow/balance CSVs, and `decisions.jsonl`/`audit.jsonl` provenance. |
| Case Study | [F.E. Walter Dam](../examples/fe_walter/README.md) | 2021–2025 daily & seasonal benchmarks (Figures 2–4), offline replay, and Ollama 0.40.6 study reproduction. |
| Reference | [Troubleshooting](TROUBLESHOOTING.md) | Symptom-to-fix table for path, hydrology, provider, and verification errors. |
