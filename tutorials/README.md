# Daily reservoir tutorial

[English](README.md) | [繁體中文](README.zh-TW.md)

Start at 00, then follow the notebooks in order. Each lesson has a goal, setup,
steps, checks and next steps. The notebook prose is English; this page and the
settings guide provide Traditional Chinese navigation. Install from the root README first.

| Order | Notebook |
|---|---|
| 00 | [Architecture / 原版與升級架構](00_overview.ipynb) |
| 01 | [Input and GIS / 入流與地圖](01_input_and_map.ipynb) |
| 02 | [YAML and agents / 設定與 agent](02_yaml.ipynb) |
| 03 | [Rule benchmark / 規則基準](03_benchmark.ipynb) |
| 04 | [Zero-shot](04_zero_shot.ipynb) |
| 05 | [DKP](05_dkp.ipynb) |
| 06 | [Audit and trace](06_audit_trace.ipynb) |
| 07 | [Multiple reservoirs and own data / 多庫與自己的資料](07_multi_and_custom.ipynb) |

## Execute offline without a notebook server

```powershell
python tutorials/build_notebooks.py --execute
```

This executes every pure-Python code cell in order and saves actual stdout in the
notebooks. It is not a Jupyter kernel test. A notebook server may also open these
standard nbformat 4 files. Existing run directories are verified and reused;
absent directories are created offline. There are 23 code cells across eight lessons.

These are repository-native HydroCNHS examples. The [FE Walter entry](../examples/fe_walter/README.md)
explains the common simulation path and separates strategy provenance from execution.

## Run each method directly

| Method | check/run YAML | verify output |
|---|---|---|
| Benchmark | `examples/fe_walter/benchmark/experiment.yaml` | `runs/fe-walter-benchmark-tutorial` |
| Zero-shot | `examples/fe_walter/zero_shot/experiment.tutorial.yaml` | `runs/fe-walter-tutorial-zeroshot` |
| DKP | `examples/fe_walter/dkp/experiment.tutorial.yaml` | `runs/fe-walter-tutorial-dkp` |
| 31-day network | `tutorials/config/multi_reservoir.offline.yaml` | `runs/three-reservoir-tutorial-31d` |

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.tutorial.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.tutorial.yaml
python run_experiment.py verify runs/fe-walter-tutorial-zeroshot --require-offline
```

Substitute the table's paths for the other methods. The command runner refuses to
overwrite an existing output; use `verify`, or select new IDs/output for a new run.
Notebook reuse also checks current YAML, input and implementation hashes. A mismatch
stops with an instruction to select new IDs/output; historical `verify` inspects saved evidence.
The three FE samples cover 2016-01-01–03. The network covers January 2016.

Input CSV columns are `date,node,local_inflow_cms`. Export Excel to UTF-8 CSV
without BOM, use ISO dates and m³/s, and record its SHA256 in the case.
These FE inputs are simulated, already upstream-routed reservoir inflow; do not
route or inject that same inflow a second time. Full natural runoff requires the
[native hydrology setup](../docs/HYDROLOGY_SETUP.md), followed by operations coupling.

In the network, FE Walter and Beltzville join on Lehigh contributions; Prompton
uses a passive outlet on Lackawaxen contributions. This is not a serial cascade
or full Delaware discharge. `UH=[1]` tests connectivity, not calibrated travel time.
Lesson 07 and tests cover true cascades, confluences, delays and channel storage.

The earlier Demo lessons remain a [source reference](https://github.com/WenyuChiou/HydroCNHS-Delaware-Demo);
the upgraded lessons preserve their input → setup → run → results teaching sequence
and reuse its frozen GIS. [Map sources](../data/figures/SOURCES.md) list exact provenance.
[Figure sources](../docs/figures/source/README.md) explain editing and regeneration.
