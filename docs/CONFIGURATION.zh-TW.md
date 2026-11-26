# 設定說明

<div class="hero-band" markdown="1">

每一項 HydroReOpLLM 研究都從頂層的 `experiment.yaml` 開始，用以串連您的物理水庫網路、水文入流資料、操作規則或 LLM 代理人、模型設定檔以及輸出目錄。若使用既有入流資料，建議從複製 [`examples/template/`](../examples/template/README.zh-TW.md) 開始；若是耦合 HydroCNHS 研究，則建議採用下方介紹的模組化拆檔架構。

</div>

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM 設定檔結構圖，連接 experiment.yaml、case、hydrology、agents、models 與 information">
  <figcaption><strong>設定檔結構關聯。</strong> 頂層 <code>experiment.yaml</code> 會相對於各宣告檔案所在目錄，依序解析區段設定檔、水庫網路、提示詞、操作手冊與 Python 規則套件。</figcaption>
</figure>

## 設定格式版本與檔案解析

精簡的既有入流設定可選用單檔式（`v1`）；若要建立多水庫耦合研究並將不同設定分開管理，則建議使用模組化拆檔式（`v2`）：

| `schema_version` | 水文輸入方式 | 模組化區段檔案（`{file: ...}`） | 典型用途 |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | 既有入流資料 | 內嵌區段 | 通用範本與 F.E. Walter 案例研究（`inflows.csv` + `case.json`）。 |
| `llm-reservoir-experiment.v2` | 既有入流資料 | `models`、`agents`、`auditors`、`extensions`、`information` | 以獨立 YAML 分檔管理的大型既有入流研究。 |
| `hydroops-coupled-simulation.v1` | 原生 HydroCNHS | 內嵌區段 | 單檔式 HydroCNHS 集水區＋水庫耦合模擬。 |
| `hydroops-coupled-simulation.v2` | 原生 HydroCNHS | `hydrology`、`models`、`agents`、`auditors`、`extensions`、`information` | 建議用於多水庫與規則＋LLM 混合流域的模組化架構。 |

- **相對路徑解析**：所有路徑（`case`、`output`、`prompt_file`、`system_prompt_file`、`knowledge`、`extensions`、CSV 路徑）皆相對於**宣告該路徑的檔案**解析。
- **整段取代原則**：`{file: ...}` 參照會取代整個對應區段（例如 `agents: { file: agents.yaml }`）；請勿在 `{file: ...}` 區塊內同時混寫其他內嵌欄位。

## 頂層實驗設定欄位

| 欄位鍵名 | 必填 | 在模擬中的用途 |
| --- | --- | --- |
| `schema_version` | 是 | 選擇 `v1`/`v2` 既有入流或耦合 HydroCNHS 格式。 |
| `run_id` | 是 | 唯一的實驗識別標籤，保存於 `summary.json` 與決策紀錄中。 |
| `output` | 是 | 全新的輸出目錄路徑（相對於 `experiment.yaml`；絕不覆寫既有模擬成果）。 |
| `case` | 是 | 指向 `case.json` 或 `reservoirs.yaml`，定義水庫容量、放流上下限與河道演算。在既有入流案例中，`case.json` 會指向 `inflows.csv` 及其 `inflow_source.sha256`。 |
| `start_date`、`end_date` | 逐日模式 | 加引號的 `YYYY-MM-DD` 雙向含括（inclusive）操作日期，須位於入流／水文期間內。 |
| `start_time`、`end_time`、`time` | 次日模式 | UTC 時間戳記（不含終點 `end_time`）搭配 `time: {simulation_step, output_step}`，用於逐時模擬。 |
| `hydrology` | 僅耦合模式 | 連接 HydroCNHS 集水區模式、氣象驅動、`inflow_bindings` 與 `diagnostics`。 |
| `agents` | 是 | 為每座受控水庫指派且僅指派一名操作員（`rule_based`、`llm` 或 `offline`）。 |
| `models` | LLM 模擬 | 具名的本機 Ollama 或雲端 LLM 設定檔（見[模型服務與可重現性](LLM_MODULES.zh-TW.md)）。 |
| `auditors` | 否 | 套用於請求放流量的診斷檢查（`release_bounds`、`field_range`）。 |
| `extensions` | 否 | 將自訂規則或檢索名稱（如 `hanasaki`）對應至 Python 套件資料夾。 |
| `information` | 否 | 符合因果時序的測站流量、預報、運轉規線與上游水庫狀態資料（見[決策時資訊](INFORMATION.zh-TW.md)）。 |
| `outcome_checks` | 否 | 河道演算完成後於匯流點或出口檢查下游流量（`minimum_cms`、`maximum_cms` 或動態資訊邊界）。 |
| `max_calls` | 建議設定 | 允許的 LLM 最大總請求次數（離線／規則模擬設為 `0`；即時 LLM 模擬至少設為 `llm_agents * steps`）。 |

## 設定順序與 YAML 驗證規則

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. 識別與視窗</strong><code>run_id</code>、全新 <code>output</code>、加引號日期</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 水文資料</strong><code>inflows.csv</code> 或 <code>hydrology.yaml</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 水庫設定</strong>庫容、放流上下限與演算延遲</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 操作員指派</strong>每座受控水庫配置 1 名操作員</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 資訊與模型</strong><code>models.yaml</code>、提示詞、<code>information</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 離線檢查</strong><code>reservoir-experiment check</code></div>
</div>

<div class="callout callout-warn" markdown="1">

**兩個常見的 YAML 陷阱。** HydroReOpLLM 會拒絕任何重複出現的 YAML 鍵名，防止誤寫的重複水庫或模型設定默默覆蓋先前內容。此外，科學記號務必加上明確的 `+` 或 `-` 符號（例如 `8.0e+6` 或 `8000000.0`），否則 PyYAML 會將 `8.0e6` 當成純文字而遭拒絕。

</div>

## 操作員、稽核器與結果檢查

- **操作員（`agents`）**：可選擇 `type: rule_based`（Hanasaki 或自訂 Python 規則）、`type: llm`（提示詞驅動模型）或 `mode: offline`（固定 `release_cms` 測試）。詳見[操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md)。
- **決策稽核器（`auditors`）**：內建稽核器可檢查請求放流量是否落於可行放水設施範圍（`release_bounds`，選填 `tolerance_cms`），或檢查任一觀測／動作欄位是否位於 `[minimum, maximum]` 區間內（`field_range`，`on_violation: FAIL | WARN`）。
- **下游結果檢查（`outcome_checks`）**：在河道演算完成後，檢查下游測站、匯流點或流域出口的流量——非常適合用來標記下游洪災警戒超標或生態基流不足事件。

接下來可繼續閱讀[水庫網路與混合控制](BUILD_SIMULATION.zh-TW.md)、[時間尺度與單位](TIME_SCALES.zh-TW.md)、[決策時資訊](INFORMATION.zh-TW.md)與[檢查、準備、執行與驗證](RUNNING.zh-TW.md)。
