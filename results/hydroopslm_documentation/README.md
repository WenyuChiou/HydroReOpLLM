# HydroOpsLM offline documentation validation

The HydroOpsLM README, formal module/settings guides and eight bilingual notebooks
were checked with Python 3.12 and existing dependencies. No real LLM was called.

| Check | Observed result |
|---|---|
| Related workflow/backend tests | 43 tests and 51 subtests passed |
| Decision-flow inspection tests | 4 tests passed |
| Notebook execution | 8 notebooks, all 28 code cells completed with network blocked |
| FE Walter benchmark / zero-shot / DKP | Each completed 3 daily steps; 0 provider calls |
| Three-reservoir demonstration | 31 days, 93 reservoir-days; 0 provider calls |
| Three-reservoir audit | 62 PASS, 31 UNKNOWN for passive Prompton |
| Maximum reservoir / system balance residual | 3.026798367500305e-9 / 3.725290298461914e-9 m³ |
| Routing replay difference | 0 m³/s |
| Rendered bilingual documents | 10 pairs; 248 local links resolved |
| Preserved dependencies | 825 protected baseline files, 22 upstream manifest entries and 221 prior output files unchanged |

Notebook replies are synthetic fixtures. Physical completion does not establish
LLM decision quality or operating-strategy acceptance. The three-reservoir
demonstration uses identity unit hydrographs for connectivity, not calibrated
downstream travel times. Prompton's strategy status remains UNKNOWN.

Reproduce from a complete checkout with repository dependencies:

```powershell
python tutorials/build_notebooks.py --execute
python -m pytest tests/test_decision_flow_tutorial.py
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-dkp
```

The notebooks create a new offline output only if it is absent. Existing output
must match current inputs and implementation hashes; otherwise verification stops.
New HydroOpsLM teaching YAML files preserve all original tutorial YAML and outputs.
Independent review and publication are recorded separately in the PR and commit.
