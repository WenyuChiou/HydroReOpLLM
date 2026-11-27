# Xindian River cascade (Taiwan) — Repository example

<div class="hero-band" markdown="1">

This **repository-only multi-reservoir example** (not part of the companion manuscript, which evaluates F.E. Walter Dam) models Taiwan's **Xindian River 2-reservoir cascade** — **Feitsui Reservoir** (`feitsui`) → **Zhitan Dam** (`zhitan`) → `xindian_outlet` — across one full out-of-sample year (**January 1 – December 31, 2025**, 365 daily steps). Using the same **HydroCNHS** (`GWLF` + `Lohmann`, calibrated with bundled `GA_DEAP`) 10-year C&V workflow and **F.E. Walter-aligned structured decision-chain prompt**, it compares a dual **Rule-based** Hanasaki cascade (`rule_based.yaml`) against a **Joint-dispatch Hybrid LLM cascade** (`hybrid_llm.yaml`).

</div>

## Study area, 10-year HydroCNHS hydrology, and C&V

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig5-xindian-study-area.png" alt="Xindian River 2-reservoir cascade study area showing subbasins U1-U2 and D1-D2, WRA gauges 10205 and 10212, Feitsui Dam, Zhitan Dam, and Xindian Outlet">
  <figcaption><strong>Figure 5.</strong> Xindian River <strong>2-reservoir series cascade</strong>, subbasins (<code>U1–U2</code> feeding <code>feitsui_local</code>, 30,300 ha; <code>D1–D2</code> contributing <code>zhitan_local</code>, 37,680 ha), WRA gauges (<code>10205</code>, <code>10212</code>), and mean annual precipitation (WorldClim 2.1): <strong>1. Feitsui Reservoir</strong> (<code>335,505,000 m3</code>; <code>[0, 500] m3/s</code>) routes through a calibrated Lohmann unit hydrograph (<code>[0.801305, 0.198693, 2e-06]</code>) into <strong>2. Zhitan Dam</strong> (<code>1,918,900 m3</code>; <code>[0, 800] m3/s</code>) before discharging to <code>xindian_outlet</code>.</figcaption>
</figure>

Local incremental inflows ([`inflows.csv`](inflows.csv), `data_kind: simulated_local_inflow`) come from the 4-subbasin HydroCNHS model ([`hydrology/xindian_catchments.yaml`](hydrology/xindian_catchments.yaml), [`hydrology/hydrology.yaml`](hydrology/hydrology.yaml)) forced by TFRA `145840` official daily catchment rainfall with ERA5 temperature/PET ([`hydrology/forcing.csv.gz`](hydrology/forcing.csv.gz), 2015 warm-up) and calibrated/validated over **10 years (`2016–2025`, 3,653 days)** via bundled `GA_DEAP` ([`hydrology/cv_summary.json`](hydrology/cv_summary.json)):

| Hydrology segment | Period | Days | KGE | NSE | RMSE (m³/s) |
| --- | --- | --- | --- | --- | --- |
| Calibration (`U1–U2` Feitsui inflow) | `2016-01-01`–`2022-12-31` (7 yr) | 2,557 | `0.926` | `0.863` | `18.73` |
| Validation (`U1–U2` Feitsui inflow) | `2023-01-01`–`2025-12-31` (3 yr) | 1,096 | `0.912` | `0.886` | `17.38` |
| Calibration (`D1–D2` Nanshi local flow) | `2016-01-01`–`2022-12-31` (7 yr) | 2,557 | `0.839` | `0.711` | `30.53` |
| Validation (`D1–D2` local / combined Zhitan) | `2023-01-01`–`2025-12-31` (3 yr) | 1,096 | `0.844` / `0.916` | `0.684` / `0.831` | `32.86` / `32.30` |

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Condition 1: Rule-based cascade

- **Config**: [`rule_based.yaml`](rule_based.yaml)
- **Method**: Dual **Rule-based** Hanasaki flood-control rule (`strategy: benchmark`, α = 0.85) calibrated on 7-year (`2016–2022`) TFRA statistics ([`feitsui_statistics.json`](feitsui_statistics.json), [`zhitan_statistics.json`](zhitan_statistics.json)), offline.
- **Result**: Ends 2025 at `271,292,850 m3` (`162.77 m`) in `feitsui` (from `316,895,260 m3`) and `1,918,697 m3` in `zhitan` (`PASS`).

</div>
<div class="panel-card" markdown="1">

### Condition 2: Hybrid LLM cascade (Joint dispatch)

- **Config**: [`hybrid_llm.yaml`](hybrid_llm.yaml)
- **Method**: Upstream `feitsui_operator` runs `gemma4:12b` (`strategy: xindian_study`, MOEA/WRA official seasonal rule curve + daily downstream Nanshi Creek lateral inflow via [`study/formatter.py`](study/formatter.py) and [`study/response_schemas.json`](study/response_schemas.json)), paired with downstream Hanasaki on `zhitan_operator`.
- **Prompts**: [System](prompts/feitsui.system.txt) · [Day-1 User sample](prompts/feitsui.user.txt).
- **Result**: Ends 2025 at `321,867,597 m3` (`168.73 m`) in `feitsui` and `1,918,607 m3` in `zhitan` (`PASS`).

</div>
</div>

## Configuration files and quick run

Both conditions share [`case.json`](case.json) and [`inflows.csv`](inflows.csv). Validate both configs and run the offline 365-day baseline:

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

- **Inflow checksum**: After editing `inflows.csv`, update `inflow_source.sha256` in `case.json` with `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/multi_reservoir/inflows.csv`.
- **YAML scientific notation**: Include `+` or `-` in exponents (`8.0e+6` or `8000000.0`), because YAML parses `8.0e6` as text and `check` rejects it.

For network schemas and custom prompts, see [Multi-reservoir networks](../../docs/MULTI_RESERVOIR.md) and [Rules & LLM prompts](../../docs/AGENT_DESIGN.md).

## Full-year 2025 performance (validation window)

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig6-xindian-results.png" alt="Full-year 2025 Feitsui water level, Feitsui release, and downstream Xindian River flow comparing TFRA observations, Rule-based cascade, and Hybrid LLM cascade">
  <figcaption><strong>Figure 6.</strong> Daily 2025 Feitsui Reservoir water level (m), release (m³/s), and downstream Xindian River flow comparing TFRA observations against the Rule-based cascade and Joint-dispatch Hybrid LLM cascade (MOEA/WRA upper limit <code>168 m</code> Sep 21–Feb 10 and <code>164 m</code> Feb 11–Sep 20).</figcaption>
</figure>

Across the 365-day validation year, `Hybrid LLM` joint dispatch lowers Feitsui water-level error (`RMSE = 3.21 m`, `NSE = 0.498`) below `Rule-based` (`RMSE = 3.63 m`, `NSE = 0.358`) while matching downstream flow `RMSE` (`57.92` vs `57.48 m³/s`), whereas `Rule-based` Hanasaki attains the highest `Feitsui level KGE` (`0.915`) and `Downstream flow KGE` (`0.760`, [`study/expected_scores.csv`](study/expected_scores.csv)):

| Condition | Feitsui level KGE | Feitsui level NSE | Feitsui level RMSE (m) | Feitsui release KGE / RMSE (m³/s) | Downstream flow KGE / RMSE (m³/s) |
| --- | --- | --- | --- | --- | --- |
| Rule-based cascade (Hanasaki + Hanasaki) | `0.915` | `0.358` | `3.63` | `0.447` / `37.63` | `0.760` / `57.48` |
| Hybrid LLM cascade (Joint dispatch + Hanasaki) | `0.601` | `0.498` | `3.21` | `0.460` / `44.35` | `0.691` / `57.92` |

## Reproduce offline or run with local Ollama

Replay the 365-day archived decisions ([`study/archived_releases.csv`](study/archived_releases.csv)) and Rule-based cascade offline (`0` network calls), or run live with Ollama (`gemma4:12b`):

```sh
python examples/multi_reservoir/study/replay.py --output runs/xindian-replay
reservoir-experiment run examples/multi_reservoir/hybrid_llm.yaml --allow-network
```

Inspect outputs with [Reading results](../../docs/RESULTS_GUIDE.md) or compare with the manuscript benchmark [F.E. Walter Dam](../fe_walter/README.md).
