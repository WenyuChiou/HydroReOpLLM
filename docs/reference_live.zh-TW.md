# FE Walter 原版策略：準備真實 LLM 執行

[English](reference_live.md) | [繁體中文](reference_live.zh-TW.md)

整合版可透過 Ollama 或 OpenAI 相容 chat API 使用 Anik V3.7 原版 zero-shot、DKP 策略。目前驗證只注入測試回覆：**沒有真實 LLM 或 HTTP 呼叫**。

1. 複製 [zero-shot YAML](../examples/fe_walter/zero_shot/experiment.llm.yaml) 或 [DKP YAML](../examples/fe_walter/dkp/experiment.llm.yaml)，保持 `temperature: 0.7`。填入已安裝的模型名稱、provider URL、timeout 與 token 上限。遠端服務的 `api_key_env` 填金鑰環境變數名稱，不要把金鑰值寫入 YAML。OpenAI 相容服務須支援提供的 JSON schema。程式不會自動下載模型。
2. 另外準備 case，包含連續 daily 局部入流 m³/s、核實的初始蓄水、物理限制與適當下游 routing。現有三日 case 保留原版蓄水假設及不延遲測試河段，因此 `live_readiness.ready: false`。處理並記錄這些假設後，才將自己的獨立 case 標記為 ready。增加 agent 時，每個受控水庫須恰好對應一位 agent，每日每位 agent 預留一次呼叫。這個可選原版 profile 支援 FE Walter；其他水庫 profile 請使用通用 `configured` 策略。
3. 保留 `strategy: reference_v3_7`、`mode: llm`、模型 profile ID 與 `system_prompt_mode: original`。Zero-shot 使用原版 system 檔，不含 DKP；DKP 使用其原版 system 檔與 `reference.dkp`。原版 builder 每天產生狀態／歷史並檢索 DKP 摘錄。真實模式禁止 `responses` 測試回覆檔。原版 schema 與放流單位仍是 cfs，由 adapter 轉成 m³/s。原版 audit 使用 record 模式，audit 修正次數為零；策略 FAIL 會保存，不改寫候選決策。Transport／JSON／schema 錯誤會在物理計算前中止，不重試、不使用備援放流。
4. 更改 `run_id` 與 `output`，既有輸出會被拒絕。`max_calls` 須涵蓋選定日期與受控 agents。目前只執行以下離線檢查。日後經授權執行真實模型，還需要明確的 `--allow-network` 與已就緒 case；現有 case 的 readiness 保持不變。

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.llm.yaml
python run_experiment.py check examples/fe_walter/dkp/experiment.llm.yaml
```

`check` 不建立 provider、不呼叫網路。每份 YAML 的計畫為三次呼叫、設定 temperature 0.7，固定 input／prompt／DKP／vendor hashes，readiness 為 false。檢查成功代表設定有效，不代表操作條件已就緒或模型可用。

日後經授權執行後，查看 `summary.json`、`reservoir_trajectory.csv`、`network_flows.csv`、`audit.jsonl`、`decisions.jsonl`、`backend_events.jsonl`。完整 `raw/` payload 保存實際 system／state prompt、原版 schema、request payload／hash、provider reply、服務有提供時的 request ID／usage、原版 audit 與版本化 audit 綁定，不保存金鑰。物理程式實施可行 controlled release、spill 與蓄水；放流加溢流只注入下游 routing 一次，下一次決策使用實施後的狀態。離線測試或替身回覆的 audit PASS 不證明真實操作策略通過。
