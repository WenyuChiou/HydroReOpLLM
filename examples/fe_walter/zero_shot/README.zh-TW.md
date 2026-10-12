# HydroOpsLM FE Walter — 本機 Ollama zero-shot

[English](README.md) | [繁體中文](README.zh-TW.md) · [三方法示範](../README.zh-TW.md)

Zero-shot 透過 HydroOpsLM LLM 介面提供操作 prompt 與當前水庫資訊，不檢索
DKP 摘錄。「淺層」只描述這項 context 設計，不代表績效或品質。

## 操作流程

1. 查看共用 [case](../../../cases/fe_walter_ollama_demo/case.json) 與
   [daily 入流](../../../cases/fe_walter_reference/inflows.csv)。
2. 開啟 [experiment.ollama.yaml](experiment.ollama.yaml)。設定為本機 Ollama
   `gemma3:4b`、temperature `0.7`、daily 2016-01-01 至 2016-01-03、
   三次請求且不重試。
3. 查看 [system prompt](../../../prompts/fe_walter_reference/zeroshot_system.txt)
   與[閱讀預覽](prompt_preview.txt)。Runtime 會逐日組合資訊與歷史；修改預覽不會
   改變執行內容。
4. 依下方命令執行本機檢查、模擬與驗證。
5. 查看實際保存的決策 trace。

執行命令前，請留意兩項範圍受限的整合假設：初始蓄水為
**1,992.61 acre-ft**，下游 `UH=[1.0]` 為 identity routing。兩者都不是
現地驗證或策略驗收。Ollama case 是明示的診斷案例，不會把原始 case readiness
從 `false` 改為已通過。

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.ollama.yaml --allow-network
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot-ollama-gemma3-4b-20261012
```

`check` 不執行 inference 或 provider request。`run --allow-network` 明確允許
設定中的本機 Ollama request。這是實際模型 run，因此 `verify` 與 inspector
不加 `--require-offline`。

查看 `summary.json`、`reservoir_trajectory.csv`、`network_flows.csv`、
`audit.jsonl` 與 `raw/`。Trace 將逐日資訊、完整 prompts、模型回覆、正規化
requested release、checker 結果、implemented release、蓄水、routed flow 與
策略 audit 串在一起。成功解析 action、audit 通過及放流物理可行是三項不同判定。

合成[離線 YAML](experiment.hydroopslm.offline.yaml)、保存的回覆 fixtures 與
教學 04／05 仍保留供開發驗證；它們不是預設使用者路徑，也不能衡量真實模型行為。

[Ollama notebook](../../../tutorials/08_ollama_workflow.ipynb) ·
[正式模組手冊](../../../docs/LLM_MODULES.zh-TW.md)
