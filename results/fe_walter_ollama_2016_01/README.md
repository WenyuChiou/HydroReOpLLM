# FE Walter local Ollama diagnostic

[English](README.md) | [繁體中文](README.zh-TW.md) · [Walkthrough](../../examples/fe_walter/README.md)

Saved actual `gemma3:4b` responses at temperature **0.7**, daily **2016-01-01–03**.
Each method made exactly three requests, with no automatic retries or model downloads.

| Method | Days / requests | Strategy audit | Maximum balance residual | Routing difference |
|---|---|---|---|---|
| Zero-shot | 3 / 3 | 2 PASS, 1 FAIL | 0 m³ | 0 m³/s |
| DKP | 3 / 3 | 3 FAIL | 8.73 × 10⁻¹⁰ m³ | 0 m³/s |

All replies completed and produced valid numeric actions. Requested and implemented
release match; spill is zero. Release plus spill enters routing once, and the
next day's history uses implemented outflow. Zero-shot's final FAIL contradicts
its stated release relation and storage direction. DKP's 50 cfs requests contradict
its claimed equal-to-inflow/hold behavior; later replies also violate the target
logic. These original audit verdicts are retained. **No operating strategy is accepted.**

Initial storage (1,992.61 acre-ft), identity downstream routing `UH=[1]`, and zero
evaporation/seepage are diagnostic assumptions. Frozen simulated reservoir inflow
is reused; rainfall–runoff is not recomputed. These three days do not establish
field accuracy, comparative strategy quality or repeatable stochastic responses.

Inspect the [verification and file hashes](verification.json),
[zero-shot trajectory](zero_shot/reservoir_trajectory.csv),
[DKP trajectory](dkp/reservoir_trajectory.csv), and each method's `audit.jsonl` / `raw/`.
The original run folders and the snapshots have identical file bytes.

```powershell
python run_experiment.py verify results/fe_walter_ollama_2016_01/zero_shot
python run_experiment.py verify results/fe_walter_ollama_2016_01/dkp
python tutorials/inspect_decision_flow.py results/fe_walter_ollama_2016_01/zero_shot --timestep 2
python tutorials/inspect_decision_flow.py results/fe_walter_ollama_2016_01/dkp --timestep 1
```

These inspection commands make no model requests. Checker validity, strategy
audit and physical execution are separate results.
