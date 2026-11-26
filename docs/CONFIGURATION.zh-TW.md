# 設定說明

<div class="hero-band" markdown="1">

每項實驗都從頂層 `experiment.yaml` 開始，串連物理水庫、入流資料、操作員、模型與輸出資料夾。既有入流請複製 [`examples/template/`](../examples/template/README.zh-TW.md)，耦合 HydroCNHS 研究則建議使用下方的拆檔架構。

</div>

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM 設定檔結構圖，連接 experiment.yaml、case、hydrology、agents、models 與 information">
  <figcaption><strong>設定檔結構關聯。</strong> 每個檔案皆從自身所在目錄解析相對路徑。</figcaption>
</figure>

## 設定格式版本與檔案解析

| `schema_version` | 水文方式 | `{file: ...}` 區段 | 典型用途 |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | 既有入流 | 內嵌 | 通用範本與 F.E. Walter 案例（`inflows.csv` + `case.json`）。 |
| `llm-reservoir-experiment.v2` | 既有入流 | `models`、`agents`、`auditors`、`extensions`、`information` | 分檔管理的模組化既有入流研究。 |
| `hydroops-coupled-simulation.v1` | 原生 HydroCNHS | 內嵌 | 單檔式 HydroCNHS 集水區＋水庫模擬。 |
| `hydroops-coupled-simulation.v2` | 原生 HydroCNHS | `hydrology`、`models`、`agents`、`auditors`、`extensions`、`information` | 建議用於多水庫與混合流域的模組化架構。 |

- 所有路徑（`case`、`output`、`prompt_file`、`knowledge`、CSV）皆相對於**宣告該路徑的 YAML 檔案**解析。
- 每個 `{file: ...}` 參照會取代整個頂層區段；切勿在 `{file: ...}` 區塊內混寫內嵌鍵值。

## 頂層實驗設定欄位

| 鍵名 | 必填 | 用途 |
| --- | --- | --- |
| `schema_version`、`run_id`、`output` | 是 | 格式版本、唯一執行標籤與尚未使用的輸出資料夾路徑。 |
| `case` | 是 | `case.json` 或 `reservoirs.yaml`，定義庫容、放流上下限、演算與 `inflow_source.sha256`（既有入流時）。 |
| `start_date`、`end_date` | 逐日 | 加引號之 `YYYY-MM-DD` 雙向含括操作日期。 |
| `start_time`、`end_time`、`time` | 次日 | UTC 時間戳記（不含終點 `end_time`）搭配 `{simulation_step, output_step}`（逐時用）。 |
| `hydrology` | 耦合 | 原生 HydroCNHS 模式、氣象驅動與 `inflow_bindings`。 |
| `agents` | 是 | 為每座受控水庫指派一名操作員（`rule_based`、`llm` 或 `offline`）。 |
| `models` | LLM | 具名的本機 Ollama 或雲端 LLM 設定檔（[模型服務](LLM_MODULES.zh-TW.md)）。 |
| `auditors`、`extensions` | 否 | 放流／範圍稽核器與註冊的 Python 規則套件（如 `hanasaki`）。 |
| `information`、`outcome_checks` | 否 | 因果測站／預報來源與演算後的下游流量檢查。 |
| `max_calls` | 建議 | LLM 總呼叫上限（離線／規則設 `0`；即時推論須 `>= llm_agents * steps`）。 |

## 設定順序與 YAML 驗證規則

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. 識別與日期</strong><code>run_id</code>、全新 <code>output</code>、加引號日期</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 水文資料</strong><code>inflows.csv</code> 或 <code>hydrology.yaml</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 水庫設定</strong>庫容、上下限與演算延遲</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 操作員</strong>每座受控水庫 1 名操作員</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 資訊與模型</strong><code>models.yaml</code>、提示詞、<code>information</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 檢查</strong><code>reservoir-experiment check</code></div>
</div>

<div class="callout callout-warn" markdown="1">

**常見 YAML 陷阱。** 任何區段出現重複鍵名都會被拒絕，防止誤覆蓋先前設定。科學記號務必加上 `+` 或 `-`（例如 `8.0e+6` 或 `8000000.0`），否則 YAML 會將 `8.0e6` 解析為純文字。

</div>

## 操作員、稽核器與結果檢查

- **操作員（`agents`）**：選用 `type: rule_based`、`type: llm` 或 `mode: offline`（[代理人設計](AGENT_DESIGN.zh-TW.md)）。
- **決策稽核器（`auditors`）**：檢查 `release_bounds`（`tolerance_cms`）或 `field_range`（`path`、`minimum`、`maximum`、`on_violation: FAIL | WARN`），不改寫流量。
- **下游結果檢查（`outcome_checks`）**：在演算完成後標記下游匯流點或出口的洪災超標或低水不足（`minimum_cms`、`maximum_cms` 或動態資訊邊界）。
