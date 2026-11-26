# 疑難排解

<div class="hero-band" markdown="1">

多數設定檔、水文綁定、模型服務與驗證錯誤都會在 `reservoir-experiment check` 階段或狀態提交前即時失敗。請利用下表將各項錯誤追溯回對應的宣告檔案與不變量規則。

</div>

## 常見症狀與排除對策

| 症狀或錯誤訊息 | 常見原因與修正方式 | 參考章節 |
| --- | --- | --- |
| 找不到檔案（`file not found`）或雜湊不相符 | 相對路徑一律相對於**宣告該路徑**的 YAML/JSON 檔案解析，而非目前工作目錄。編輯 CSV 或提示詞後，請重新計算 `inflow_source.sha256` 或 `source_dependencies`。 | [設定說明](CONFIGURATION.zh-TW.md) |
| `YAML keys must be unique strings` 或浮點指數錯誤 | 出現重複的映射鍵名，或科學記號缺少正負號（如 `8.0e6`）。請改寫為 `8.0e+6` 或 `8000000.0`。 | [設定說明](CONFIGURATION.zh-TW.md) |
| `cannot mix public and legacy agent fields` | 同一操作員內不可混用公開欄位（`reservoir_id`/`type`/`model_profile`/`prompt_file`）與舊版欄位（`reservoir`/`mode`/`strategy`/`model`/`prompt`）。 | [代理人設計](AGENT_DESIGN.zh-TW.md) |
| 未知的水庫／節點或覆蓋率錯誤 | `agents` 須 1 對 1 覆蓋每座 `controlled` 水庫；耦合模式 `inflow_bindings` 須完整覆蓋每個 `routing_node`。 | [水庫網路](BUILD_SIMULATION.zh-TW.md) |
| `inflow bindings overlap` 或水量重複計算 | `local_inflow_cms` 與 `inflow_bindings` 僅能代表區域增量逕流，不可包含已演算過的上游放流量。 | [HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md) |
| `Run output already exists` | 已完成的輸出目錄不可變更。請更換全新的 `run_id` 與尚未使用的 `output` 路徑。 | [執行生命週期](RUNNING.zh-TW.md) |
| `LLM run makes N model request(s)...` | 即時模型呼叫須同時提供 `--allow-network`、`"live_readiness": {"ready": true}`（或 `synthetic_fixture`）以及 `max_calls >= planned_llm_calls`。 | [執行生命週期](RUNNING.zh-TW.md) |
| `required API key environment variable is unset` | 請於執行 `run` 前，在作用中的終端環境匯出 `api_key_env` 所指定的環境變數。 | [模型服務](LLM_MODULES.zh-TW.md) |
| `unsupported model settings` 或供應商參數遭拒 | 確認各供應商專屬選項（`num_ctx`/`think`/`keep_alive` 僅限 `ollama`；`seed` 僅限 `ollama`/`openai_compatible`；`anthropic` 必填 `max_tokens`）。 | [模型服務](LLM_MODULES.zh-TW.md) |
| `information profile and $information placeholder must be configured together` | 綁定 `customization.information` 的通用 LLM 代理人必須在提示詞範本中加入 `$information`（反之亦然）。 | [決策時資訊](INFORMATION.zh-TW.md) |
| `information field is unavailable` | 檢查 UTC `Z`/偏移時間戳記、`valid_time <= clock`、`available_at <= clock`、`issued_at <= clock`、`max_age_seconds` 與 `required`。 | [決策時資訊](INFORMATION.zh-TW.md) |
| `Hanasaki parity conflict` | 主機的 `minimum_release_cms`、`maximum_release_cms` 或 `dead_storage_m3` 截幅了 Hanasaki 目標放流量。請使用與 `rule_case.json` 相容的限制，或改用獨立的受限實驗設定。 | [代理人設計](AGENT_DESIGN.zh-TW.md) |
| 耦合輸出缺少 `summary.json` | 前處理準備目錄僅保存 `inflows.csv`，須待 `run` 完成 `<output>/operation/summary.json` 才算完成操作模擬。 | [結果解讀](RESULTS_GUIDE.zh-TW.md) |
| 逐時模擬結果異常 | 請核對累積降雨／PET 水深單位、UTC `timestamp` 連續性、`dt_seconds` 與 GWLF 初始狀態。 | [逐時 GWLF](HOURLY_GWLF.zh-TW.md) |

## 重試前請先保留現場證據

<div class="callout callout-warn" markdown="1">

**切勿刪除中斷的輸出目錄。** 若即時 LLM 模擬中途當機或中斷，請完整保留部分輸出目錄（包含 `provider_attempts.jsonl`、`decisions.jsonl`、`physics.jsonl`），並透過 `reservoir-experiment resume` 將續跑結果寫入全新的 `--output` 目錄，以確保已計費的決策與 `STARTED` 呼叫預約紀錄獲得正確帳務保留。

</div>

修正輸入設定後，請務必重新執行 `reservoir-experiment check <config>`；若已完成模擬的稽核紀錄出現 `WARN`/`FAIL` 結果，請參閱[解讀執行結果](RESULTS_GUIDE.zh-TW.md)。
