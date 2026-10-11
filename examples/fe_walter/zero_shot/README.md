# FE Walter — Anik V3.7 Zero-shot

English / 繁體中文 · [All reference settings / 完整原版設定](../../../cases/fe_walter_reference/README.md)

A concrete example of the generic HydroCNHS reservoir-agent framework.
This is the original Zero-shot strategy with **synthetic offline replies**, not a live LLM run.

1. Input: shared [case JSON](../../../cases/fe_walter_reference/case.json), [daily inflow CSV](../../../cases/fe_walter_reference/inflows.csv), and [reply fixture](../../../cases/fe_walter_reference/zeroshot_responses.json).
2. Settings: commented [experiment.yaml](experiment.yaml), one FE Walter agent, daily 2016-01-01..03, `mode: offline`, `max_calls: 0`.
3. Prompt: [prompt_preview.txt](prompt_preview.txt) shows the complete original system prompt, first-day state prompt and response schema. It is a **reading snapshot**, not a runtime template. Original builders regenerate state/history/retrieval each day.
4. Knowledge: Public facts and seasonal target; no DKP. / 公開資訊與季節目標，不使用 DKP。
5. Audit: original native strategy audit plus the generic release-bounds auditor. Neither rewrites the model's request; the shared physical solver enforces feasibility.
6. From the installed repository root, run:

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.yaml
python run_experiment.py verify runs/fe-walter-example-zeroshot
```

7. Results: `summary.json`, `reservoir_trajectory.csv`, `network_flows.csv`, `audit.jsonl` and `raw/`. With these pass-through fixtures: 3 days, 0 model calls, 3 audit PASS, reservoir balance residual 0 m³. These are expected fixture checks based on the preserved offline diagnostic, not newly generated decisions.

**Assumptions:** original initial storage 1,992.61 acre-ft, zero losses, identity downstream reach `[1.0]`; live readiness false. Change `run_id` and `output` before another run. Editing the reading snapshot has no effect on execution. For custom prompts use the generic `configured` strategy. The original reference selector currently supports offline only.

**中文操作：**這是一個具體的 Zero-shot 案例，input／物理資料共用，策略與測試回覆分開。依序查看 input、修改有註解的 YAML、閱讀完整 prompt，再執行上面的 `check → run → verify`。本案例不指定 DKP；各項旗標在 YAML 中，每日狀態由原版 builder 動態產生，不讀取 `prompt_preview.txt`。結果使用上述 CSV／JSON 查看；3 PASS 僅是這組合成回覆的檢查，不代表真實操作策略通過。初始蓄水是假設，routing 是測試河段，尚不能直接切換真實 LLM。

Prompt system SHA256: `f0999945b989cf1a97e8e7239d78c774baf9c7e82c342ae27551baf56ca45133`. Shared assets and original vendor bytes remain unchanged.
