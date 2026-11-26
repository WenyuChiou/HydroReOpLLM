# 常見問題與排解

<div class="hero-band" markdown="1">

多數路徑、水文、模型服務與水量平衡錯誤都會在 `reservoir-experiment check` 階段即時攔截。對照下表即可快速找到需要修正的設定檔。

</div>

## 常見症狀與排解方式

| 症狀或錯誤 | 常見原因與修正方式 | 參考 |
| --- | --- | --- |
| 找不到檔案或 `inflow_source` 不符 | 相對路徑從**宣告該路徑**的 YAML/JSON 解析，而非終端機工作目錄。修改 `inflows.csv` 後請更新 `case.json` 中的 `inflow_source.sha256`（見[多水庫串聯案例](../examples/multi_reservoir/README.zh-TW.md)）。 | [實驗設定檔](CONFIGURATION.zh-TW.md) |
| `YAML keys must be unique strings` 或浮點數錯誤 | 重複的 YAML 鍵名，或科學記號未寫正負號（如 `8.0e6`）。請改寫為 `8.0e+6` 或 `8000000.0`。 | [實驗設定檔](CONFIGURATION.zh-TW.md) |
| `cannot mix public and legacy agent fields` | 請將 `reservoir_id`/`type`/`model_profile`/`prompt_file` 與 `reservoir`/`mode`/`strategy`/`model`/`prompt` 分開使用。 | [操作規則與 LLM 設計](AGENT_DESIGN.zh-TW.md) |
| 未知的水庫／節點或覆蓋率錯誤 | 每座 `controlled` 水庫須對應一名操作員；`reservoirs.yaml` 中每個入流口、匯流點與出口皆須對應一筆 `inflow_bindings`。 | [多水庫河網串接](MULTI_RESERVOIR.zh-TW.md) |
| `inflow bindings overlap` / 水量重複計算 | 區域入流與 `inflow_bindings` 不得包含已演算過的上游水庫放流。 | [入流與 HydroCNHS 設定](HYDROLOGY_SETUP.zh-TW.md) |
| `Run output already exists` | 已完成的輸出受保護不可覆寫；請設定新的 `run_id` 與未使用的 `output` 資料夾。 | [執行、驗證與續跑](RUNNING.zh-TW.md) |
| `LLM run makes N model request(s)...` | 即時模擬須同時提供 `--allow-network`、`"live_readiness": {"ready": true}`（或合成測試案例）與 `max_calls`。 | [執行、驗證與續跑](RUNNING.zh-TW.md) |
| `required API key environment variable is unset` | 執行前請在作用中的終端機匯出 `api_key_env` 指定的環境變數。 | [模型服務設定](MODEL_PROVIDERS.zh-TW.md) |
| `unsupported model settings` / 選項遭拒 | 檢查供應商適用範圍（`num_ctx`/`think`/`keep_alive` 僅限 `ollama`；`seed` 僅限 `ollama`/`openai_compatible`；`anthropic` 必填 `max_tokens`）。 | [模型服務設定](MODEL_PROVIDERS.zh-TW.md) |
| `$information` 不相符 | `customization.information` 綁定與提示詞中的 `$information` 須成對設定。 | [水情測站與預報](INFORMATION.zh-TW.md) |
| `information field is unavailable` | 檢查 UTC `Z`/偏移水情時間戳記、`valid_time <= clock`、`available_at <= clock`、`issued_at <= clock`、`max_age_seconds` 與 `required`。 | [水情測站與預報](INFORMATION.zh-TW.md) |
| `Hanasaki parity conflict` | 水庫物理限制（`minimum_release_cms`、`maximum_release_cms`、`dead_storage_m3`）截幅了 Hanasaki 目標；請使用 `rule_case.json` 相容限制。 | [操作規則與 LLM 設計](AGENT_DESIGN.zh-TW.md) |
| 耦合輸出缺少 `summary.json` | 僅完成前處理的資料夾只含 `inflows.csv`，須待 `run` 寫入 `<output>/operation/summary.json`。 | [結果判讀與水量平衡](RESULTS_GUIDE.zh-TW.md) |
| 逐時模擬結果異常 | 重新核對累積水深單位（`prec`/`pet`）、UTC 時間戳記、`dt_seconds` 與 GWLF 初始狀態。 | [逐時 GWLF（實驗性）](HOURLY_GWLF.zh-TW.md) |

## 重試前先保留中斷目錄

<div class="callout callout-warn" markdown="1">

**切勿刪除中斷的模擬目錄。** 保留原本的部分輸出資料夾，並使用 `reservoir-experiment resume` 將續跑寫入全新的 `--output` 資料夾，系統便會直接重播已完成步驟而不重複詢問 LLM。

</div>

修正輸入後請重跑 `reservoir-experiment check <config>`，完成後可參閱[結果判讀與水量平衡](RESULTS_GUIDE.zh-TW.md)。
