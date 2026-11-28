# Key Configs & File Map

<div class="hero-band" markdown="1">

Every HydroReOpLLM experiment connects **4 key user-facing file layers** from one top-level YAML file. Start with the [Single-reservoir case (F.E. Walter)](../examples/fe_walter/README.md) or [Multi-reservoir case](../examples/multi_reservoir/README.md), and use the 1-to-1 file map below when adapting your own basin.

</div>

## Minimal starter bundle for your own basin

- **Rule-based baseline (3 files):** `<experiment>.yaml` (e.g., `rule_based.yaml`) + `case.json` + `inflows.csv` *(plus `*_statistics.json` for Hanasaki)*.
- **Standard SI LLM run (5 files):** Add `prompts/system.txt` + `prompts/user.txt` *(returns `release_cms` directly — **no custom Python or `study/` folder required**)*.

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM 4 key configuration layers: experiment YAML, hydrology, reservoir case, and agent definitions">
  <figcaption><strong>Four key config layers.</strong> All relative paths resolve from the YAML file that declares them.</figcaption>
</figure>

## 1-to-1 real file map (`examples/` and modular `v2`)

| Config layer | Real filenames in `examples/` (and `v2` split names) | Required? | What this file controls | Where to inspect fields |
| --- | --- | --- | --- | --- |
| **1. Experiment entry** | `rule_based.yaml`, `seasonal_target.yaml`, `dkp.yaml`, `hybrid_llm.yaml` *(or `experiment.yaml`)* | **Yes** | Run ID, simulation dates, links to Layers 2–4, `models`, `agents`, `max_calls`, `output`. | Top-level keys below |
| **2. Hydrology & inflows** | `inflows.csv` | Direct inflow | Daily local lateral runoff per non-dam node (`date,node,local_inflow_cms`). | [Inflows & HydroCNHS](HYDROLOGY_SETUP.md) |
| | `hydrology/hydrology.yaml` + `xindian_catchments.yaml` + `forcing.csv(.gz)` | Coupled only | HydroCNHS watershed model (`GWLF`/`ABCD` + `Lohmann`), climate forcing & `inflow_bindings`. | [Inflows & HydroCNHS](HYDROLOGY_SETUP.md) |
| **3. Reservoir network** | `case.json` *(or `rule_case.json`, `reservoirs.yaml`)* | **Yes** | Dam capacities, dead storage, release bounds `[min, max]`, and `unit_hydrograph` lags. | [Reservoir network & routing](MULTI_RESERVOIR.md) |
| **4. Decision agents** | `rule_statistics.json`, `feitsui_statistics.json`, `zhitan_statistics.json` | Hanasaki | Long-term mean inflows for Hanasaki flood-control parameterization. | [Rules, prompts & knowledge](AGENT_DESIGN.md) |
| | `prompts/*.system.txt`, `prompts/*.user.txt`, optional `dkp.md` | LLM | Standing rules, daily template placeholders, and optional operating manual rules. | [Rules, prompts & knowledge](AGENT_DESIGN.md) |
| | `information.yaml` *(optional)* & `models:` / `models.yaml` | Optional / LLM | Non-leaking gauge/forecast feeds and Ollama / cloud LLM settings (`seed`, `temperature`). | [Gauges & forecasts](INFORMATION.md) · [Model providers](MODEL_PROVIDERS.md) |

<div class="callout callout-info" markdown="1">

**Note on `study/` folders in `examples/`.** Files under `study/` (such as `formatter.py`, `response_schemas.json`, `archived_releases.csv`, `replay.py`) only handle paper score replay or imperial site-unit formatting (`ft` / `cfs`). Custom SI-unit (`m3` / `m3/s`) basins do **not** need `study/`.

</div>

## Schema versions & modular `{file: ...}` splits

| `schema_version` | Hydrology | `{file: ...}` split sections | Typical use |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | Prepared `inflows.csv` | Inline | Single-dam F.E. Walter and Xindian cascade examples. |
| `llm-reservoir-experiment.v2` | Prepared `inflows.csv` | `models`, `agents`, `auditors`, `extensions`, `information` | Large prepared-inflow studies split across clean files. |
| `hydroops-coupled-simulation.v1` | Coupled HydroCNHS | Inline | Single-file coupled watershed + reservoir study. |
| `hydroops-coupled-simulation.v2` | Coupled HydroCNHS | `hydrology`, `models`, `agents`, `auditors`, `extensions`, `information` | Recommended modular layout for coupled multi-dam studies. |

## Top-level YAML keys & common pitfalls

| Key | Required | Purpose |
| --- | --- | --- |
| `schema_version`, `run_id`, `output`, `case` | **Yes** | Config format version, unique run label, unused output folder, and `case.json`/`reservoirs.yaml`. |
| `start_date`, `end_date` *(or `start_time`/`end_time`/`time`)* | **Yes** | Quoted inclusive `YYYY-MM-DD` dates (or UTC `...Z` timestamps for fixed sub-daily intervals). |
| `hydrology` | Coupled | Links `hydrology.yaml` when running HydroCNHS before reservoir operations. |
| `agents` | **Yes** | One `rule_based`, `llm`, or `offline` operator per controlled reservoir. |
| `models` | LLM | Named Ollama or cloud profiles (`seed`, `temperature`, `max_tokens`, timeouts). |
| `information`, `auditors`, `outcome_checks`, `extensions` | No | Non-leaking gauges/forecasts, diagnostic bound checks, and custom Python rules. |
| `max_calls` | Recommended | LLM call budget cap (`0` for rule/offline runs; `>= llm_agents * steps` for live runs). |

<div class="callout callout-warn" markdown="1">

**Two YAML rules that save debugging time.** Duplicate keys in any block are rejected, and scientific notation **must include `+` or `-`** (`8.0e+6` or `8000000.0`, never `8.0e6`). Validate anytime with `reservoir-experiment check <config.yaml>`.

</div>
