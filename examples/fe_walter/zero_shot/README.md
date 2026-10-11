# FE Walter — Anik V3.7 Zero-shot

[English](README.md) | [繁體中文](README.zh-TW.md) · [All reference settings](../../../cases/fe_walter_reference/README.md)

A concrete example of the generic HydroCNHS reservoir-agent framework.
This is the original Zero-shot strategy with **synthetic offline replies**, not a live LLM run.

1. Input: shared [case JSON](../../../cases/fe_walter_reference/case.json), [daily inflow CSV](../../../cases/fe_walter_reference/inflows.csv), and [reply fixture](../../../cases/fe_walter_reference/zeroshot_responses.json).
2. Settings: commented [experiment.yaml](experiment.yaml), one FE Walter agent, daily 2016-01-01..03, `mode: offline`, `max_calls: 0`.
3. Prompt: [prompt_preview.txt](prompt_preview.txt) shows the complete original English system prompt, first-day state prompt and response schema. It is a **reading snapshot**, not a runtime template. Original builders regenerate the daily state and history; zero-shot does not retrieve DKP excerpts.
4. Knowledge: Public facts and seasonal target; no DKP.
5. Audit: original native strategy audit plus the generic release-bounds auditor. Neither rewrites the model's request; the shared physical solver enforces feasibility.
6. From the installed repository root, run:

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.yaml
python run_experiment.py verify runs/fe-walter-example-zeroshot
```

7. Results: `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, `audit.jsonl` and `raw/`. With these pass-through fixtures: 3 days, 0 model calls, 3 audit PASS, reservoir balance residual 0 m³. These are expected fixture checks based on the preserved offline diagnostic, not newly generated decisions.

**Assumptions:** original initial storage 1,992.61 acre-ft, zero losses, identity downstream reach `[1.0]`; live readiness false. Change `run_id` and `output` before another run. Editing the reading snapshot has no effect on execution. For custom prompts use the generic `configured` strategy. The original reference selector currently supports offline only.

The generic templates under `prompts/` are a separate strategy. This example preserves the original English prompt rather than translating its runtime text. The fixture audit PASS does not approve a real operating strategy.

Prompt system SHA256: `f0999945b989cf1a97e8e7239d78c774baf9c7e82c342ae27551baf56ca45133`. Shared assets and original vendor bytes remain unchanged.
