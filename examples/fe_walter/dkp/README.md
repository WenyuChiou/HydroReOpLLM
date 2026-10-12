# HydroOpsLM FE Walter — DKP

[English](README.md) | [繁體中文](README.zh-TW.md) · [All reference settings](../../../cases/fe_walter_reference/README.md)

This repository runs daily Dam coupling, reservoir physics and downstream routing. A policy compatibility adapter supplies prompts, response parsing and strategy audit; the next day uses the physical outcome. See the [shared three-method execution path](../README.md).

A concrete example of the HydroOpsLM reservoir-agent framework.
This is the original DKP strategy with **synthetic offline replies**, not a live LLM run.

1. Input: shared [case JSON](../../../cases/fe_walter_reference/case.json), [daily inflow CSV](../../../cases/fe_walter_reference/inflows.csv), and [reply fixture](../../../tests/fixtures/dkp_responses.json).
2. Settings: commented [experiment.hydroopslm.offline.yaml](experiment.hydroopslm.offline.yaml), one FE Walter agent, daily 2016-01-01..03, `mode: offline`, `max_calls: 0`.
3. Prompt: YAML reads [system instructions](../../../prompts/fe_walter_reference/dkp_system.txt) from `prompts/`. [prompt_preview.txt](prompt_preview.txt) shows the complete original English system prompt, first-day state prompt and response schema. It is a **reading snapshot**, not a runtime template. Original builders regenerate the daily state/history and retrieve relevant DKP excerpts.
4. Knowledge: Original [DKP v1.2](../../../data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md) and conditional excerpt retrieval.
5. Audit: original native strategy audit plus the generic release-bounds auditor. Neither rewrites the model's request; the shared physical solver enforces feasibility.
6. From the installed repository root, run:

```powershell
python run_experiment.py check examples/fe_walter/dkp/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/dkp/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-dkp --require-offline
```

7. Results: `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, `audit.jsonl` and `raw/`. With these pass-through fixtures: 3 days, 0 model calls, 3 audit PASS, reservoir balance residual 0 m³. These are expected fixture checks based on the preserved offline diagnostic, not newly generated decisions.

**Assumptions:** original initial storage 1,992.61 acre-ft, zero losses, identity downstream reach `[1.0]`; live readiness false. Change `run_id` and `output` before another run. Editing the reading snapshot has no effect on execution. For broader prompt/state customization, use the generic `configured` strategy. A separate [live YAML](experiment.llm.yaml) supports the same native strategy; see the [preparation guide](../../../docs/reference_live.md). Its current case remains blocked for live execution. To edit system instructions, copy the file and use `reference.system_prompt_mode: custom`; the trace records a variant. `original` mode verifies parity against the original builder.

Generic synthetic prompt templates are test fixtures under `tests/fixtures/prompts/`; old root files remain compatibility links. This example preserves the original English prompt rather than translating its runtime text. The fixture audit PASS does not approve a real operating strategy.

Prompt system SHA256: `c018043ce34a6e47024024ce63622d837dffa686a15523eb97d4bdd4ae678352`. Shared assets and original vendor bytes remain unchanged.

Strategy provenance: Anik V3.7. Preserved prompts/schema/retrieval and vendor hashes support parity checks; this example executes through this repository's `run_experiment.py`.

## Inspect the complete decision

After the offline output exists, run this read-only inspector or follow [lessons 04/05](../../../tutorials/README.md):

```powershell
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-dkp
```

Read info, prompt variables, full system/user prompt, synthetic reply, normalized proposal, action-contract recheck, original audit, executed release and next-day info. The recheck is not an invented historical event; original FAIL/WARN/UNKNOWN remain, and common physics determines implemented release. The original experiment.tutorial.yaml and historical outputs remain preserved; this entry uses a separate HydroOpsLM run.
