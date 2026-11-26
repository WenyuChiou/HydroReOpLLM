# 檢查、準備、執行與驗證

<div class="hero-band" markdown="1">

每一項 HydroReOpLLM 實驗都遵循同一套可重現的命令列生命週期（`src/llm_reservoir_agent/workflow.py`）：`check` →（耦合 HydroCNHS 專用的 `prepare`）→ `run` → `verify`（以及供中斷復原使用的 `resume`）。

</div>

<figure class="figure-card">
  <img src="assets/simulation-stages.png" alt="從設定檔檢查、前處理準備、水庫操作到獨立驗證的執行階段流程圖">
  <figcaption><strong>工作流程生命週期。</strong> 設定驗證、選用的水文前處理、受預算約束的模擬執行與獨立驗證皆共用鎖定的來源檔案雜湊值。</figcaption>
</figure>

## CLI 生命週期與輸出目錄結構

於專案根目錄（或已匯出範例的工作目錄）執行最短完整流程：

```powershell
reservoir-experiment check path/to/experiment.yaml
reservoir-experiment run path/to/experiment.yaml
reservoir-experiment verify path/to/output
```

| 子指令 | 職責 | 是否寫入輸出 | 網路呼叫次數 |
| --- | --- | --- | --- |
| `check <config>` | 驗證設定 schema、SHA-256 鎖定值、綁定關係，並建立離線第 0 步提示詞預覽。 | 否 | `0` |
| `prepare <config>` | 僅限耦合模式（`hydroops-coupled-simulation.v1/.v2`）：執行 HydroCNHS 水文與暖機並鎖定 `inflows.csv`。 | 準備目錄 | `0` |
| `run <config> [--allow-network]` | 視需要執行前處理，再執行水庫代理人與河道演算，寫出耐久日誌。 | 全新 `<output>` | `0`（除非傳入 `--allow-network`） |
| `verify <output> [--require-offline]` | 查核雜湊值、因果追蹤序列、水量平衡、河道演算與選定的決策資訊。 | 否 | `0` |
| `resume <config> --from-run ... --output ... --run-id ...` | 將中斷執行的未變更前段重播至全新目錄，並接續後續步驟。 | 全新 `--output` | 僅針對未完成步驟 |

輸出目錄結構會依據設定檔入口格式而有所不同：

| 輸入模式 | 設定檔的 `output` | 操作紀錄位置 | 驗證目標路徑 |
| --- | --- | --- | --- |
| 耦合 HydroCNHS（`v1`/`v2`） | 準備目錄（`inflows.csv`、`preparation.json`） | `<output>/operation/` | `reservoir-experiment verify <output>`（或 `<output>/operation`） |
| 既有入流資料（`v1`/`v2`） | 操作目錄 | `<output>/` | `reservoir-experiment verify <output>` |

<div class="callout callout-info" markdown="1">

**重複使用水文前處理成果。** 若先執行 `prepare` 並檢視 `inflows.csv`，後續執行 `run` 時會核對 `preparation.json`（`hydrology_signature` 與檔案 SHA-256 雜湊值），確認無誤後即跳過 HydroCNHS 逕流重算。在 `operation/summary.json` 出現且狀態為 `"COMPLETED"` 之前，僅含前處理檔案的準備目錄並不算一次已完成的模擬。

</div>

## 即時模型呼叫與安全閘門

啟用即時 LLM 推論必須同時滿足**三個**明確條件（`workflow.py` 中的 `_live_gate_message`）：

1. **CLI 授權旗標**：於執行 `reservoir-experiment run`（或 `resume`）時明確傳入 `--allow-network`。
2. **案例資料就緒宣告**：非合成資料案例（`observed_local_inflow` 或 `simulated_local_inflow`）必須在 `case.json` / `reservoirs.yaml` 中宣告 `"live_readiness": {"ready": true}`（`synthetic_fixture` 案例無須此欄位即視為就緒）。
3. **呼叫預算上限（`max_calls`）**：必須設定足以涵蓋 `llm_agent_count * steps` 的整數（或明確設為 `null`）。每一次主呼叫、重試（`max_attempts`）與 `fallback_models` 備援呼叫在送出前，都會先在 `provider_attempts.jsonl` 寫入一筆 `STARTED` 預約紀錄。

## 續跑中斷的水庫操作

切勿刪除或更動失敗或中斷的輸出目錄。請將 `resume` 指向中斷目錄（`--from-run`），並指定全新的 `--output` 與 `--run-id`：

```powershell
reservoir-experiment resume path/to/experiment.yaml `
  --from-run path/to/partial-operation `
  --output path/to/new-operation `
  --run-id NEW_RUN_ID
```

`RecoveryTape`（`src/llm_reservoir_agent/recovery.py`）會嚴格要求套件程式碼、HydroCNHS 核心鎖定檔、Python 版本、水系結構與入流檔案完全一致。它會重播已保存的回覆與情境快照、重新建構完全一致的物理狀態轉移，並繼承先前所有已預約的 `STARTED` 呼叫次數計入 `max_calls`。僅在剩餘未完成步驟需要發出新 LLM 請求時，才加上 `--allow-network`。

## 重播已保存的逐日回覆

使用主機物理與河道演算引擎離線重播封存的逐日放流回覆（`recorded_llm_response`）：

```powershell
llm-reservoir-daily --case-root path/to/case-directory `
  --case case.json `
  --responses responses.json `
  --output runs/replay
reservoir-experiment verify runs/replay --require-offline
```

若要重現 F.E. Walter 21 組論文基準模擬，請執行 `python examples/fe_walter/study/replay.py --output runs/walter-paper-replay`（詳見 [F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)）。接著請繼續閱讀[解讀執行結果](RESULTS_GUIDE.zh-TW.md)。
