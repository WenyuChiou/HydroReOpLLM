# Module 05: ODD+LLM Protocol, Reproducibility & Audit Trails

Package verified **HydroReOpLLM** experiments into publication-ready **ODD+LLM** (`odd-llm-reproducibility.v1`) protocol reports, SHA-256 provenance manifests, numerical audit diagnostics, and bit-exact zero-network offline replays.

## Learning Objectives

- Run an offline **F.E. Walter Dam** baseline (`rule_based.yaml`) inside `tempfile.TemporaryDirectory()` and independently verify every trace stream, mass-balance residual, and cryptographic hash with `verify_run(..., require_offline=True)`.
- Load `odd_llm_manifest.json` directly from the run directory and inspect all five CoALA-grounded **ODD+LLM** protocol blocks (`A_cognitive_architecture`, `B_identity`, `C_inference_configuration`, `D_behavioral_submodel`, and `E_validation`).
- Export a standardized publication-ready Markdown report via `export_odd_report(..., markdown_out=...)` (the programmatic counterpart to `reservoir-experiment export-odd`).
- Visualize per-step mass-balance residuals alongside physical clipping, spillway, and audit counts (`reservoir_trajectory.csv` + `audit.jsonl`), and confirm exact hash and score reproduction (`network_calls = 0`) using `examples/multi_reservoir/study/replay.py`.

## What You Configure, Run, and See

| Stage | Action | Artifact / Output |
| --- | --- | --- |
| **Execute & Verify** | Run full-year 2021 F.E. Walter `rule_based.yaml` inside `TemporaryDirectory()` and audit with `verify_run(..., require_offline=True)` | `status = PASS`, `observed_network_calls = 0`, verified SHA-256 pin for `odd_llm_manifest.json` |
| **Inspect & Export** | Load `odd_llm_manifest.json`, walk through Blocks `A`–`E`, and call `export_odd_report(..., markdown_out=...)` | Structured 5-block ODD+LLM summary and publication-ready Markdown report excerpt |
| **Audit & Plot** | Analyze per-step residuals in `reservoir_trajectory.csv` and status counts in `audit.jsonl` | 2-panel figure: daily mass-balance residuals (`10⁻⁹ m³`) + audit/clipping/spill summary |
| **Offline Replay** | Invoke `examples/multi_reservoir/study/replay.py` inside a fresh temporary directory | `status = PASS`, `network_calls = 0`, exact `archived_releases.csv` SHA-256 and 6/6 verified 2025 KGE/NSE/RMSE scores |

## Inputs & Files Used

- [`05_odd_llm_reproducibility.ipynb`](05_odd_llm_reproducibility.ipynb) — pre-executed hands-on notebook
- [`examples/fe_walter/rule_based.yaml`](../../examples/fe_walter/rule_based.yaml) — offline F.E. Walter Hanasaki rule configuration
- [`examples/fe_walter/ODD_LLM.md`](../../examples/fe_walter/ODD_LLM.md) — shipped F.E. Walter ODD+LLM protocol card
- [`examples/multi_reservoir/ODD_LLM.md`](../../examples/multi_reservoir/ODD_LLM.md) — shipped Xindian River ODD+LLM protocol card
- [`examples/multi_reservoir/study/replay.py`](../../examples/multi_reservoir/study/replay.py) — offline zero-network replay verifier for the 2025 Xindian River cascade
- [`examples/multi_reservoir/study/archived_releases.csv`](../../examples/multi_reservoir/study/archived_releases.csv) — SHA-256 pinned archived daily LLM releases (`hybrid_llm`, seed 3)

## How to Run

From the repository root (with `.venv` activated):

```sh
python -m jupyterlab tutorials/05_odd_llm_reproducibility_and_audit/05_odd_llm_reproducibility.ipynb
```

Select the `.venv` Python kernel and choose **Run → Run All Cells**. Every run writes strictly inside `tempfile.TemporaryDirectory()` with `0` network calls.

To export an ODD+LLM bundle for any completed run from the command line:

```sh
reservoir-experiment verify <run_dir> --require-offline
reservoir-experiment export-odd <run_dir> --json-out <run_dir>/odd_export.json --markdown-out <run_dir>/odd_report.md
```

## Next Steps

- Return to the **[Tutorial Curriculum Overview](../README.md)** or try the consolidated **[F.E. Walter End-to-End Walkthrough (`fe_walter.ipynb`)](../fe_walter.ipynb)** (including optional live Ollama execution).
- Consult **[Reading Results & Verification](../../docs/RESULTS_GUIDE.md)** for the full trace stream and SHA-256 schema specification.
