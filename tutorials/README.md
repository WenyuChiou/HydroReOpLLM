# Hands-On Tutorial Curriculum

Learn **HydroReOpLLM** step by step through a progressive, hands-on curriculum inspired by *Machine Learning for Algorithmic Trading (2nd Ed.)*. Every module follows the same practical loop — **Configure → Operate → Execute → Inspect & Plot** — with pre-executed Jupyter notebooks that run **100% offline** in temporary directories so you can inspect exact figures directly on GitHub or re-run every cell locally without leaving files in the repository.

## 5-Module Curriculum

| Module | Topic | Learning Path | Notebook & Guide |
| --- | --- | --- | --- |
| **01** | **Setup & First Offline Rule-Based Baseline** | Inspect F.E. Walter `rule_case.json` & `inflows.csv`, run 2021 Hanasaki (`365` days), verify mass balance (`verify_run`), and plot pool elevation + release vs. inflow. | [Guide](01_setup_and_first_run/README.md) · [Notebook](01_setup_and_first_run/01_setup_and_rule_baseline.ipynb) |
| **02** | **LLM Prompt Engineering & Operational Knowledge (DKP)** | Compare `seasonal_target.yaml` (Without knowledge) vs. `dkp.yaml` (With knowledge), inspect Day-1 prompts, JSON schemas, and `dkp.md` rule retrieval, replay 2021 offline, and score against USGS `01447780` & `01447800`. | [Guide](02_prompt_and_knowledge_design/README.md) · [Notebook](02_prompt_and_knowledge_design/02_llm_prompt_and_knowledge.ipynb) |
| **03** | **Watershed Hydrology, 10-Year C&V & HydroCNHS Coupling** | Load 4-subbasin (`U1, U2, D1, D2`) Xindian River `hydrology.yaml` & `forcing.csv.gz`, validate non-overlapping bindings, verify 10-year C&V (`2016–2025`), and plot 2025 hydrographs + monthly water balance. | [Guide](03_watershed_hydrology_and_cv/README.md) · [Notebook](03_watershed_hydrology_and_cv/03_hydrocnhs_cv_and_coupling.ipynb) |
| **04** | **Multi-Reservoir Hybrid Cascade (Xindian River)** | Configure `feitsui → zhitan → xindian_outlet` with Lohmann UH & 36-dekad MOEA/WRA rule curve, run offline Rule-based + Hybrid LLM replay, verify routing convolution, and plot 3-panel 2025 results vs. TFRA observations. | [Guide](04_multi_reservoir_hybrid_cascade/README.md) · [Notebook](04_multi_reservoir_hybrid_cascade/04_xindian_hybrid_cascade.ipynb) |
| **05** | **ODD+LLM Protocol, Reproducibility & Audit Trails** | Inspect `odd_llm_manifest.json` (Blocks A–E), verify SHA-256 traces, export publication-ready ODD+LLM Markdown reports (`export-odd`), and run offline replay audit checks. | [Guide](05_odd_llm_reproducibility_and_audit/README.md) · [Notebook](05_odd_llm_reproducibility_and_audit/05_odd_llm_reproducibility.ipynb) |
| **All-in-One** | **F.E. Walter End-to-End Walkthrough** | Single consolidated notebook covering architecture, 2021 Paper Figure 3 replay, prompt design, cascade preview, and optional live Ollama execution (`RUN_LLM = True`). | [Notebook (`fe_walter.ipynb`)](fe_walter.ipynb) |

## Setup & Launch JupyterLab

[Clone and install HydroReOpLLM](../docs/GETTING_STARTED.md), activate `.venv`, and launch JupyterLab from the repository root (every notebook automatically locates `REPO_ROOT` whether opened from the root, `tutorials/`, or a module folder):

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab ipykernel
python -m jupyterlab tutorials/01_setup_and_first_run/01_setup_and_rule_baseline.ipynb
```

1. Select the `.venv` Python kernel in the top-right picker (if missing, register it once: `python -m ipykernel install --user --name hydroreopllm --display-name "Python (.venv HydroReOpLLM)"`).
2. Choose **Run → Run All Cells**. All modules default to offline execution (`0` network calls) and write only to `tempfile.TemporaryDirectory()`.

## Where to Go Next

- **Benchmarks & Live Ollama Setup:** [Single-reservoir case (F.E. Walter)](../examples/fe_walter/README.md) and [Multi-reservoir case (Xindian River)](../examples/multi_reservoir/README.md).
- **Reference Manuals:** [Inflows & HydroCNHS](../docs/HYDROLOGY_SETUP.md), [Experiment setup](../docs/CONFIGURATION.md), [Rules & LLM prompts](../docs/AGENT_DESIGN.md), [Multi-reservoir networks](../docs/MULTI_RESERVOIR.md), and [Reading results](../docs/RESULTS_GUIDE.md).
