# 設定說明

<div class="hero-band" markdown="1">

每一項 HydroReOpLLM 研究都從頂層 YAML 設定檔（`experiment.yaml`）開始，用以鎖定物理水系案例、模擬視窗、水文輸入、操作員、模型設定檔、稽核器與輸出目錄。建議先複製 [`examples/template/`](../examples/template/README.zh-TW.md)，或採用本頁說明的拆檔式耦合結構著手。

</div>

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM 套件結構與設定檔關聯圖">
  <figcaption><strong>設定相依關係圖。</strong> 頂層 <code>experiment.yaml</code> 會相對於各宣告檔案所在目錄，依序解析區段設定檔、水系案例、提示詞、知識包與 Python 擴充套件。</figcaption>
</figure>

## 設定格式版本與檔案解析

`read_configuration`（`src/llm_reservoir_agent/configuration.py`）同時支援單檔式（`v1`）與模組化拆檔式（`v2`）設定文件：

| `schema_version` | 輸入模式 | 模組化區段檔案（`{file: ...}`） | 主要用途 |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | 既有入流資料 | 內嵌區段 | 通用範本與 F.E. Walter 範例（`reservoir` + `mode` 或 `normalize_agent`）。 |
| `llm-reservoir-experiment.v2` | 既有入流資料 | `models`、`agents`、`auditors`、`extensions`、`information` | 模組化既有入流研究；載入時會自動展開為等價的 `v1` 結構。 |
| `hydroops-coupled-simulation.v1` | 原生 HydroCNHS | 內嵌區段 | 單檔式 HydroCNHS 水文與水庫操作耦合模擬。 |
| `hydroops-coupled-simulation.v2` | 原生 HydroCNHS | `hydrology`、`models`、`agents`、`auditors`、`extensions`、`information` | 建議用於多水庫串聯與規則＋LLM 混合式研究的模組化設定架構。 |

- **相對路徑解析**：所有資源路徑（`case`、`output`、`prompt_file`、`system_prompt_file`、`knowledge`、`extensions`、CSV 路徑）一律相對於**宣告該路徑的 YAML 檔案**解析。
- **整段取代原則**：`{file: ...}` 參照會取代整個頂層對應區段（而非深層合併）；同一個區段內不可同時混寫 `{file: ...}` 與內嵌鍵值。

## 頂層實驗設定欄位

| 欄位鍵名 | 必填 | 用途與驗證規則（`workflow.py` 與 `coupled.py`） |
| --- | --- | --- |
| `schema_version` | 是 | 選擇 `v1`/`v2` 既有入流或耦合模擬格式。 |
| `run_id` | 是 | 非空追蹤識別碼，會寫入 `summary.json` 與 `decisions.jsonl`。 |
| `output` | 是 | 尚未使用的輸出目錄路徑（相對於 `experiment.yaml`）；若目錄已存在將被拒絕。 |
| `case` | 是 | 指向 `llm-reservoir-network-case.v1`（既有入流）或 `reservoir-physical-case.v1`（耦合模式）。 |
| `start_date`、`end_date` | 逐日模式 | 加引號的 `YYYY-MM-DD` 雙向含括（inclusive）操作日期，須落於入流／水文期間內。 |
| `start_time`、`end_time`、`time` | 次日模式 | UTC 時間戳記（不含終點 `end_time`）搭配 `time: {simulation_step, output_step}`，用於 `v3` 固定時距模擬。 |
| `hydrology` | 僅耦合模式 | HydroCNHS 模式、氣象驅動資料、`inflow_bindings`、`diagnostics` 或 `prepared_from`。 |
| `agents` | 是 | 非空對應表，須 1 對 1 完整覆蓋每座 `controlled` 水庫（見[代理人設計](AGENT_DESIGN.zh-TW.md)）。 |
| `models` | LLM 模擬 | 具名模型服務設定檔（見[模型服務與可重現性](LLM_MODULES.zh-TW.md)）。 |
| `auditors` | 否 | 具名 `release_bounds`、`field_range` 或擴充稽核器設定。 |
| `extensions` | 否 | `<id>: path/to/__init__.py` 對應表，系統會對整個套件子目錄計算 SHA-256 雜湊鎖定。 |
| `information` | 否 | `v2` `{sources, profiles}` 目錄（或 `v1` 的 `information_sources`/`information_profiles`）。 |
| `outcome_checks` | 否 | 河道演算後的下游控制點流量檢查（`minimum_cms`、`maximum_cms` 或動態資訊邊界）。 |
| `max_calls` | 建議設定 | 大於等於 `llm_agent_count * steps` 的整數（或明確設為 `null` 表示不設上限；離線／規則模擬設為 `0`）。 |
| `source_dependencies` | 否 | 明確的 `{relative_path: sha256}` 檔案完整性鎖定表，於載入時逐一驗證。 |

## 設定順序與 YAML 驗證規則

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. 識別碼與日期</strong><code>run_id</code>、全新 <code>output</code>、加引號日期</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 水文／案例</strong><code>inflows.csv</code> 雜湊或 <code>hydrology.yaml</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 水庫網路</strong>庫容、放流上下限、演算單位歷線</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 操作員指派</strong>每座受控水庫配置 1 名操作員</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 資訊與模型</strong><code>models.yaml</code>、提示詞、<code>information</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 離線檢查</strong><code>reservoir-experiment check</code></div>
</div>

<div class="callout callout-warn" markdown="1">

**YAML 驗證常見陷阱（`UniqueLoader`）。** HydroReOpLLM 會拒絕重複的 YAML 映射鍵名，不會默默覆寫先前的設定。此外，科學記號務必加上明確的指數正負號（例如 `8.0e+6` 或 `8000000.0`），因為 PyYAML SafeLoader 會將未帶正負號的 `8.0e6` 解析成字串，導致 `check` 驗證失敗。

</div>

## 操作員、稽核器與結果檢查

- **操作員（`agents`）**：可選擇 `type: rule_based`（例如 `rule: hanasaki`）、`type: llm`（`model_profile` + `prompt_file` + `customization:`）或 `mode: offline`（固定 `release_cms` 測試夾具）。詳見[操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md)。
- **決策稽核器（`auditors`）**：內建 `ConfiguredAudit` 類型包含 `release_bounds`（`tolerance_cms`）與 `field_range`（指定 `observation.*` 或 `action.*` 路徑、`minimum`、`maximum`、`on_violation: FAIL | WARN`）。
- **下游結果檢查（`outcome_checks`）**：於整條河網演算完成後執行評估（`src/llm_reservoir_agent/outcome.py`），依靜態或因果資訊邊界查核匯流點與出口流量。

接下來可繼續閱讀[水庫網路與多庫系統](BUILD_SIMULATION.zh-TW.md)、[時間尺度與單位](TIME_SCALES.zh-TW.md)、[決策時資訊](INFORMATION.zh-TW.md)與[執行、驗證與續跑](RUNNING.zh-TW.md)。
