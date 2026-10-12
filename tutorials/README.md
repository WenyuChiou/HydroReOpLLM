# HydroOpsLM step-by-step tutorials

[English](README.md) | [繁體中文](README.zh-TW.md)

Install from the [framework README](../README.md). Start at 00 to understand the
LLM decision path, then prepare inputs, configure agents and run an offline example.
Each notebook has English/Traditional Chinese guidance and shared executable cells.
Runtime prompts retain their original English bytes.

| Order | Notebook | What you will inspect |
|---|---|---|
| 00 | [LLM architecture](00_overview.ipynb) | Info → prompt → proposal → checker → execution, audit/trace and feedback |
| 01 | [Input and map](01_input_and_map.ipynb) | Inflow, units, initial state and GIS |
| 02 | [Agent settings](02_yaml.ipynb) | YAML, models, prompts, knowledge and auditors |
| 03 | [Rule benchmark](03_benchmark.ipynb) | Deterministic requested release using common physics/routing |
| 04 | [Zero-shot](04_zero_shot.ipynb) | Full prompt, synthetic reply and complete decision chain |
| 05 | [DKP](05_dkp.ipynb) | Retrieved knowledge, full prompt and complete decision chain |
| 06 | [Audit and trace](06_audit_trace.ipynb) | Original verdict, bound physics and actual next-day history |
| 07 | [Multiple reservoirs / your own data](07_multi_and_custom.ipynb) | Topology, state isolation, passive outlets and 31-day flow |

[Generic settings](../docs/USER_GUIDE.md) and [LLM modules](../docs/LLM_MODULES.md)
are formal manuals. [Examples](../examples/README.md) contain the three concrete methods.

## Execute offline

```powershell
python tutorials/build_notebooks.py --execute
```

This executes 28 pure-Python code cells across eight lessons and saves actual
stdout; it does not test a Jupyter kernel. The builder blocks HTTP/socket connects.
Existing runs are verified and reused only if current YAML/input/implementation
hashes match. Missing runs are created offline; a mismatch stops rather than overwrites.

| Method | check/run YAML | verify output |
|---|---|---|
| Benchmark | `examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml` | `runs/hydroopslm-fe-walter-benchmark` |
| Zero-shot | `examples/fe_walter/zero_shot/experiment.hydroopslm.offline.yaml` | `runs/hydroopslm-fe-walter-zero-shot` |
| DKP | `examples/fe_walter/dkp/experiment.hydroopslm.offline.yaml` | `runs/hydroopslm-fe-walter-dkp` |
| 31-day network | `tutorials/config/multi_reservoir.hydroopslm.offline.yaml` | `runs/hydroopslm-three-reservoir-31d-v2` |

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot --require-offline
```

Substitute the table's paths for other methods. Existing output is refused;
verify it or choose new IDs/output. The FE samples cover 2016-01-01–03.

## Inspect a complete decision

After the offline example exists, display a day without rerunning a simulation:

```powershell
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-dkp --timestep 1
```

The inspector verifies offline evidence, then shows **info, full system/user
prompt, synthetic reply, normalized proposal, action-contract recheck, original
audit, committed physics, next-day info and trace paths**. The recheck is current;
it does not invent a historical checker event. Lessons 04/05 also demonstrate
rejection of a negative proposal without calling physics or changing saved state.
Checker acceptance, strategy audit and physical balance are separate outcomes.

The generic fixed-release offline backend bypasses prompt/model execution.
The two reference offline cases assemble prompts and parse supplied replies;
all replies are synthetic and cannot measure real LLM policy quality.

## Use your data and design an experiment

Export Excel to UTF-8 CSV without BOM: `date,node,local_inflow_cms`, ISO dates,
m³/s and a recorded SHA256. These FE inputs are simulated, already upstream-routed
reservoir inflow; insert them once. Native runoff setup is linked from the manual.

The January 2016 network joins FE Walter/Beltzville on Lehigh contributions and
uses a passive Prompton outlet on Lackawaxen contributions. It is not a serial
cascade or full river discharge. `UH=[1]` tests connectivity, not calibrated travel time.
Lesson 07 covers own-case preparation; tests cover cascades, confluences and delays.

Keep shared inputs, initial states, physics and routing fixed when comparing
methods. Version each changed prompt/knowledge/auditor and save a new run.
Read [live readiness](../docs/LIVE_READINESS.md) before real-provider experiments.

[Earlier Demo](https://github.com/WenyuChiou/HydroCNHS-Delaware-Demo) ·
[Map sources](../data/figures/SOURCES.md) · [Editable figures](../docs/figures/source/README.md)
