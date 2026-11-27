# Module 02: LLM Prompt Engineering, Schemas & Operational Knowledge (DKP)

Discover how **HydroReOpLLM** turns operational manuals into structured, auditable LLM reservoir decisions. This module compares **Without operational knowledge** (`seasonal_target.yaml`) against **With operational knowledge** (`dkp.yaml`) on **F.E. Walter Dam** across **2021** (`0` network calls via offline replay).

## Learning Objectives

- Compare `seasonal_target.yaml` and `dkp.yaml` configurations, SHA-256 `source_dependencies`, and zero-cost Day-1 prompt previews via `load_settings`.
- Understand how `study/response_schemas.json` enforces a causal decision chain (`applicable_target_ft` → `pool_position` → `intended_storage_direction` → `release_relation_to_inflow` → `release_cfs`) plus `operating_mode` and `rules_applied` under DKP.
- Trace dynamic rule retrieval from the Decision Knowledge Package (`dkp.md`) across winter, summer normal, and flood-storage regimes.
- Replay archived 2021 LLM decisions (`10` seeds per condition) offline through `RecordedResponseBackend` and benchmark KGE, NSE, and RMSE against USGS gauges `01447780`, `01447800`, and `01449000`.

## What You Configure, Run, and See

| Stage | Action | Artifact / Output |
| --- | --- | --- |
| **Configure** | Load `seasonal_target.yaml` and `dkp.yaml` offline via `load_settings` | Side-by-side configuration & SHA-256 dependency comparison table |
| **Operate** | Inspect Day-1 prompt previews, `prompts/dkp.user.txt`, `study/response_schemas.json`, and `StudyPrompt` rule retrieval | Schema diff (`operating_mode`, `rules_applied`) and regime-dependent DKP rule excerpts |
| **Execute** | Replay 2021 archived releases (`20` LLM runs + `1` Rule-based baseline) through `RecordedResponseBackend` & `run_network` | Verified `0` network calls + 2021 KGE/NSE/RMSE benchmark table against USGS |
| **Inspect & Plot** | Aggregate 10-seed ensemble medians and interquartile ranges (`25th–75th` pct) | 2-panel 2021 pool elevation (`USGS 01447780`) and release (`USGS 01447800`) comparison plot |

## Inputs & Files Used

- [`02_llm_prompt_and_knowledge.ipynb`](02_llm_prompt_and_knowledge.ipynb) — pre-executed hands-on notebook
- [`examples/fe_walter/seasonal_target.yaml`](../../examples/fe_walter/seasonal_target.yaml) — Without operational knowledge config
- [`examples/fe_walter/dkp.yaml`](../../examples/fe_walter/dkp.yaml) — With operational knowledge (DKP) config
- [`examples/fe_walter/dkp.md`](../../examples/fe_walter/dkp.md) — F.E. Walter Decision Knowledge Package (`DKP-FEWALTER-v1.2`)
- [`examples/fe_walter/prompts/dkp.user.txt`](../../examples/fe_walter/prompts/dkp.user.txt) — Day-1 DKP user prompt sample
- [`examples/fe_walter/study/response_schemas.json`](../../examples/fe_walter/study/response_schemas.json) — strict JSON output schemas
- [`examples/fe_walter/study/archived_releases.csv`](../../examples/fe_walter/study/archived_releases.csv) & [`study/observations.csv`](../../examples/fe_walter/study/observations.csv) — archived LLM release series and USGS observations

## How to Run

From the repository root (with `.venv` activated):

```sh
python -m jupyterlab tutorials/02_prompt_and_knowledge_design/02_llm_prompt_and_knowledge.ipynb
```

Select the `.venv` Python kernel and choose **Run → Run All Cells** (runs 100% offline with `0` model requests).

## Next Module

Continue to **[Module 03: Watershed Hydrology, 10-Year C&V & HydroCNHS Coupling](../03_watershed_hydrology_and_cv/README.md)** to build and validate the upstream rainfall-runoff model on Taiwan's Xindian River basin.
