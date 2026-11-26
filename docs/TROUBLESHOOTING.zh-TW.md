# 疑難排解

<div class="hero-band" markdown="1">

多數路徑、水文綁定、模型服務與水量平衡錯誤都會在執行 `reservoir-experiment check` 時即時攔截。請利用下表將錯誤訊息對應回需要修正的檔案與設定。

</div>

## 常見症狀與排除對策

| 症狀或錯誤訊息 | 常見原因與修正方式 | 參考章節 |
| --- | --- | --- |
| 找不到檔案（`file not found`）或 `inflow_source` 不符 | 相對路徑一律從**宣告該路徑**的 YAML/JSON 檔案解析，而非目前終端機工作目錄。若您編輯過 `inflows.csv`，請更新 `case.json` 中的 `inflow_source.sha256`（見[範本指南](../examples/template/README.zh-TW.md)）。 | [設定說明](CONFIGURATION.zh-TW.md) |
| `YAML keys must be unique strings` 或浮點指數錯誤 | 出現重複的映射鍵名，或科學記號未標示正負號（如 `8.0e6`）。請務必改寫為 `8.0e+6` 或 `8000000.0`。 | [設定說明](CONFIGURATION.zh-TW.md) |
| `cannot mix public and legacy agent fields` | 同一個操作員內不可混用 `reservoir_id`/`type`/`model_profile`/`prompt_file` 與 `reservoir`/`mode`/`strategy`/`model`/`prompt`。 | [代理人設計](AGENT_DESIGN.zh-TW.md) |
| 未知的水庫／節點或覆蓋率錯誤 | 每座 `controlled` 水庫都須在 `agents:` 有一名對應操作員；`reservoirs.yaml` 中的每個入流點、匯流點與出口都須在 `inflow_bindings` 有對應項目。 | [水庫網路](BUILD_SIMULATION.zh-TW.md) |
| `inflow bindings overlap` 或水量重複計算 | `local_inflow_cms` 與 `inflow_bindings` 僅能代表區域增量逕流——絕不可包含已經演算抵達的上游水庫放流量。 | [HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md) |
| `Run output already exists` | 已完成的輸出目錄受到保護不得覆寫。請指定全新的 `run_id` 與尚未使用的 `output` 資料夾。 | [執行生命週期](RUNNING.zh-TW.md) |
| `LLM run makes N model request(s)...` | 即時模擬須同時提供 `--allow-network`、`"live_readiness": {"ready": true}`（或 `synthetic_fixture`）以及 `max_calls >= planned_llm_calls`。 | [執行生命週期](RUNNING.zh-TW.md) |
| `required API key environment variable is unset` | 請於執行前，在作用中的終端機匯出 `api_key_env` 所指定的環境變數。 | [模型服務](LLM_MODULES.zh-TW.md) |
| `unsupported model settings` 或供應商參數遭拒 | 確認各供應商專屬選項（`num_ctx`/`think`/`keep_alive` 僅限 `ollama`；`seed` 僅限 `ollama`/`openai_compatible`；`anthropic` 必填 `max_tokens`）。 | [模型服務](LLM_MODULES.zh-TW.md) |
| `information profile and $information placeholder must be configured together` | 使用 `customization.information` 的通用 LLM 代理人必須在提示詞檔案中加入 `$information`（反之亦然）。 | [決策時資訊](INFORMATION.zh-TW.md) |
| `information field is unavailable` | 檢查 UTC `Z`/偏移時間戳記、`valid_time <= clock`、`available_at <= clock`、`issued_at <= clock`、`max_age_seconds` 與 `required`。 | [決策時資訊](INFORMATION.zh-TW.md) |
| `Hanasaki parity conflict` | 主機的 `minimum_release_cms`、`maximum_release_cms` 或 `dead_storage_m3` 截幅了 Hanasaki 目標放流量。請改用與 `rule_case.json` 相容的限制，或使用獨立的受限設定。 | [代理人設計](AGENT_DESIGN.zh-TW.md) |
| 耦合輸出缺少 `summary.json` | 僅完成前處理的目錄只包含 `inflows.csv`，須待 `run` 寫出 `<output>/operation/summary.json` 才算完成。 | [結果解讀](RESULTS_GUIDE.zh-TW.md) |
| 逐時模擬結果異常 | 請重新確認累積水深單位（`prec`/`pet`）、UTC `timestamp` 連續性、`dt_seconds` 與 GWLF 初始狀態。 | [逐時 GWLF](HOURLY_GWLF.zh-TW.md) |

## 重試前請先保留現場證據

<div class="callout callout-warn" markdown="1">

**切勿刪除中斷的輸出目錄。** 若多年期即時 LLM 模擬中途停止，請完整保留部分輸出目錄（`provider_attempts.jsonl`、`decisions.jsonl`、`physics.jsonl`），並透過 `reservoir-experiment resume` 將續跑寫入全新的 `--output` 資料夾，系統便會直接重播已完成步驟而不重複詢問 LLM。

</div>

編輯輸入後，請重新執行 `reservoir-experiment check <config>`；若已完成模擬在稽核紀錄出現 `WARN`/`FAIL` 提示，請參閱[解讀執行結果](RESULTS_GUIDE.zh-TW.md)。
