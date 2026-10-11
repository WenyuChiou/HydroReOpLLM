# FE Walter — Anik V3.7 DKP

English / 繁體中文 · [All reference settings / 完整原版設定](../../../cases/fe_walter_reference/README.md)

A concrete example of the generic HydroCNHS reservoir-agent framework.
This is the original DKP strategy with **synthetic offline replies**, not a live LLM run.

1. Input: shared [case JSON](../../../cases/fe_walter_reference/case.json), [daily inflow CSV](../../../cases/fe_walter_reference/inflows.csv), and [reply fixture](../../../cases/fe_walter_reference/dkp_responses.json).
2. Settings: commented [experiment.yaml](experiment.yaml), one FE Walter agent, daily 2016-01-01..03, `mode: offline`, `max_calls: 0`.
3. Prompt: [prompt_preview.txt](prompt_preview.txt) shows the complete original system prompt, first-day state prompt and response schema. It is a **reading snapshot**, not a runtime template. Original builders regenerate state/history/retrieval each day.
4. Knowledge: Original DKP v1.2 and conditional excerpt retrieval. / 原版 DKP v1.2 與依情境選取的規則摘錄。
5. Audit: original native strategy audit plus the generic release-bounds auditor. Neither rewrites the model's request; the shared physical solver enforces feasibility.
6. From the installed repository root, run:

```powershell
python run_experiment.py check examples/fe_walter/dkp/experiment.yaml
python run_experiment.py run examples/fe_walter/dkp/experiment.yaml
python run_experiment.py verify runs/fe-walter-example-dkp
```

7. Results: `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, `audit.jsonl` and `raw/`. With these pass-through fixtures: 3 days, 0 model calls, 3 audit PASS, reservoir balance residual 0 m³. These are expected fixture checks based on the preserved offline diagnostic, not newly generated decisions.

**Assumptions:** original initial storage 1,992.61 acre-ft, zero losses, identity downstream reach `[1.0]`; live readiness false. Change `run_id` and `output` before another run. Editing the reading snapshot has no effect on execution. For custom prompts use the generic `configured` strategy. The original reference selector currently supports offline only.

**中文操作：**這是一個具體的 DKP 案例，input／物理資料共用，策略與測試回覆分開。依序查看 input、修改有註解的 YAML、閱讀完整 prompt，再執行上面的 `check → run → verify`。DKP 路徑與各項旗標在 YAML 中；每日狀態與摘錄由原版 builder 動態產生，不讀取 `prompt_preview.txt`。結果使用上述 CSV／JSON 查看；3 PASS 僅是這組合成回覆的檢查，不代表真實操作策略通過。初始蓄水是假設，routing 是測試河段，尚不能直接切換真實 LLM。

Prompt system SHA256: `c018043ce34a6e47024024ce63622d837dffa686a15523eb97d4bdd4ae678352`. Shared assets and original vendor bytes remain unchanged.
