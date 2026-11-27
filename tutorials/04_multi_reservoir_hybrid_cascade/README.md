# Module 04: Multi-Reservoir Hybrid Cascade (`Feitsui → Zhitan`)

Combine watershed hydrology (Module 03), deterministic rules (Module 01), and joint-dispatch LLM prompts (Module 02) on Taiwan's **Xindian River 2-reservoir cascade** (`feitsui → zhitan → xindian_outlet`) across the full **2025** out-of-sample validation year (`365` daily steps).

## Learning Objectives

- Inspect a v2 multi-reservoir cascade (`case.json`) with Lohmann unit-hydrograph routing (`[0.801305, 0.198693, 2e-06]`), the official 36-dekad MOEA/WRA rule curve (`study/rule_curve.csv`), and the joint-dispatch Day-1 LLM prompt (`hybrid_llm.yaml`) incorporating downstream Nanshi Creek lateral inflow.
- Execute both the dual **Rule-based cascade** (`rule_based.yaml`) and the **Hybrid LLM cascade** (`hybrid_llm.yaml` offline replay via `RecordedResponseBackend`) inside `tempfile.TemporaryDirectory()`.
- Independently verify mass balance (`verify_run(..., require_offline=True)`), Lohmann routing convolution parity, and exact 2025 KGE/NSE/RMSE reproduction against `study/expected_scores.csv`.
- Compare 2025 Feitsui water level (+ MOEA/WRA upper limit), Feitsui release, and downstream Xindian River flow against TFRA observations (`study/observations.csv`).

## What You Configure, Run, and See

| Stage | Action | Artifact / Output |
| --- | --- | --- |
| **Configure** | Inspect `case.json`, 36-dekad `study/rule_curve.csv`, and offline `load_settings(hybrid_llm.yaml)` Day-1 prompt | Cascade topology, dekad limits, and joint-dispatch prompt with Nanshi lateral inflow |
| **Operate & Execute** | Run `rule_based.yaml` and offline `hybrid_llm.yaml` replay (`study/archived_releases.csv`) inside `TemporaryDirectory()` | Completed 365-day cascade traces (`0` network calls) |
| **Verify** | Run `verify_run(..., require_offline=True)`, check Lohmann UH convolution, and match `study/expected_scores.csv` | `PASS` on both cascades, `< 1e-10 m³/s` routing parity, verified KGE/NSE/RMSE table |
| **Inspect & Plot** | Plot 3-panel 2025 trajectory comparison against TFRA observations | 3-panel figure: Feitsui water level (+ MOEA/WRA upper limit), Feitsui release, and Xindian outlet flow |

## Inputs & Files Used

- [`04_xindian_hybrid_cascade.ipynb`](04_xindian_hybrid_cascade.ipynb) — pre-executed hands-on notebook
- [`examples/multi_reservoir/case.json`](../../examples/multi_reservoir/case.json) — 2-reservoir cascade topology & Lohmann UH
- [`examples/multi_reservoir/rule_based.yaml`](../../examples/multi_reservoir/rule_based.yaml) — dual Hanasaki cascade configuration
- [`examples/multi_reservoir/hybrid_llm.yaml`](../../examples/multi_reservoir/hybrid_llm.yaml) — joint-dispatch LLM (`feitsui`) + Hanasaki (`zhitan`) configuration
- [`examples/multi_reservoir/study/rule_curve.csv`](../../examples/multi_reservoir/study/rule_curve.csv) — official 36-dekad MOEA/WRA Feitsui rule curve
- [`examples/multi_reservoir/study/archived_releases.csv`](../../examples/multi_reservoir/study/archived_releases.csv), [`study/observations.csv`](../../examples/multi_reservoir/study/observations.csv), & [`study/expected_scores.csv`](../../examples/multi_reservoir/study/expected_scores.csv) — archived replay releases, TFRA observations, and reference metrics

## How to Run

From the repository root (with `.venv` activated):

```sh
python -m jupyterlab tutorials/04_multi_reservoir_hybrid_cascade/04_xindian_hybrid_cascade.ipynb
```

Select the `.venv` Python kernel and choose **Run → Run All Cells** (runs 100% offline in a temporary directory).

## Next Module

Continue to **Module 05: ODD+LLM Protocol, Reproducibility & Audit Trails** (`tutorials/05_odd_llm_reproducibility_and_audit/`) to generate standardized ODD+LLM experiment documentation and reproducible verification bundles.
