# Module 01: Setup & First Offline Rule-Based Baseline

Build confidence in the **HydroReOpLLM** execution and verification pipeline by running a full-year (**2021**, 365 daily steps) offline **Hanasaki flood-control rule** baseline for **Francis E. Walter Dam** (Lehigh River basin, Pennsylvania) inside an isolated temporary directory.

## Learning Objectives

- Inspect how HydroReOpLLM separates physical reservoir/routing definitions (`rule_case.json`, `inflows.csv`) from operator policy (`rule_based.yaml`).
- Validate an experiment plan offline (`load_settings`) with zero network calls and strict SHA-256 input pinning.
- Execute a full-year deterministic rule simulation (`run_settings`) and independently verify mass-balance residuals, routing continuity, and audit traces (`verify_run(..., require_offline=True)`).
- Convert simulated storage trajectories (`m³`) into pool elevations (`ft NGVD29`) and visualize 2021 elevation and release-versus-inflow behavior.

## What You Configure, Run, and See

| Stage | Action | Artifact / Output |
| --- | --- | --- |
| **Configure** | Inspect `rule_case.json` geometry, 2-reach Lohmann unit hydrographs, 2021 `inflows.csv` statistics, and Hanasaki `alpha = 0.85` settings | Formatted physical specification and 2021 inflow summary |
| **Operate** | Write a 365-day (`2021-01-01`–`2021-12-31`) YAML config inside `tempfile.TemporaryDirectory()` and call `load_settings` | Validated offline plan (`planned_llm_calls = 0`) |
| **Execute** | Run `run_settings(..., allow_network=False)` and audit with `verify_run(..., require_offline=True)` | `status = PASS`, `observed_network_calls = 0`, mass-balance residual `< 1e-8 m³`, final storage |
| **Inspect & Plot** | Read `reservoir_trajectory.csv` and convert storage via `study/elevation_storage.csv` | Quarterly balance table + 2-panel 2021 pool elevation (`ft`) and release vs. inflow (`cfs`) plot |

## Inputs & Files Used

- [`01_setup_and_rule_baseline.ipynb`](01_setup_and_rule_baseline.ipynb) — pre-executed hands-on notebook
- [`examples/fe_walter/rule_case.json`](../../examples/fe_walter/rule_case.json) — physical reservoir & downstream Lohmann routing network
- [`examples/fe_walter/inflows.csv`](../../examples/fe_walter/inflows.csv) — daily local incremental inflows (`2021–2025`)
- [`examples/fe_walter/rule_based.yaml`](../../examples/fe_walter/rule_based.yaml) — Hanasaki rule configuration (`alpha = 0.85`, `max_calls = 0`)
- [`examples/fe_walter/study/elevation_storage.csv`](../../examples/fe_walter/study/elevation_storage.csv) — F.E. Walter elevation–storage rating curve (`ft NGVD29`)

## How to Run

From the repository root (with `.venv` activated):

```sh
python -m jupyterlab tutorials/01_setup_and_first_run/01_setup_and_rule_baseline.ipynb
```

Select the `.venv` Python kernel and choose **Run → Run All Cells**. All outputs are written inside `tempfile.TemporaryDirectory()` and cleaned up automatically.

## Next Module

Continue to **[Module 02: LLM Prompt Engineering & Operational Knowledge (DKP)](../02_prompt_and_knowledge_design/README.md)** to compare **Without operational knowledge** (`seasonal_target.yaml`) against **With operational knowledge** (`dkp.yaml`).
