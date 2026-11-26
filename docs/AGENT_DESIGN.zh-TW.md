# 操作員與 LLM 代理人設計

<div class="hero-band" markdown="1">

HydroReOpLLM 將 **「由誰做決策」**（決定性規則或 LLM 操作策略）與 **「如何維持水量守恆」**（共用的 HydroCNHS `Dam` 質量平衡與河道演算核心）明確分離。兩類操作員接收完全相同的 `ReservoirObservation`，以 `m3/s` 回傳請求的 `ReservoirAction`，並通過相同的稽核器與物理上下限檢查。

</div>

## 與 HydroCNHS 的架構邊界

HydroReOpLLM 透過 [`examples/llm_reservoir_abm.py`](../examples/llm_reservoir_abm.py) 封裝 HydroCNHS 的代理人建模（`ABM`）介面，將 `LLMReservoirAgent`（`src/llm_reservoir_agent/agent.py`）註冊為 HydroCNHS 的 `DamAPI` 類別。當 `network.py` 呼叫 `build_network_model` 時，每座受控水庫都會獲得以下配置：

- `WaterSystem.ABM`：`Modules: ["llm_reservoir_abm.py"]` 與 `DamAPI: ["LLMReservoirAgent"]`。
- `ABM.LLMReservoirAgent.<name>.Inputs.Links`：嚴格對應一個 `-1` 入流節點（`inflow_node`）與一個 `+1` 出流節點（`<name>`）。
- `ABM.LLMReservoirAgent.<name>.Attributes`：`Physical`（`PhysicalConfig`）、`Context` 與 `Policy`。

由於 `LLMReservoirAgent` 將決策邏輯委派給獨立隔離的 `decide(observation)` 後端，而自身僅負責執行 `apply_transition` 水量平衡演算（`src/llm_reservoir_agent/physics.py`），因此在規則基準與 LLM 代理人之間切換時，**只需要更動操作員設定**——水文河道演算與物理邊界條件完全維持不變。

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="整合 HydroCNHS 與 LLM／規則操作員的閉迴路水庫操作架構圖">
  <figcaption><strong>圖 1.</strong> 概念閉迴路架構：HydroCNHS 將集水區逕流演算成水庫觀測狀態；規則式或 LLM 操作員讀取決策時資訊或決策知識包（DKP），輸出結構化放流請求；主機物理核心依序落實放流量上下限、呆庫容保護與溢流計算，再進行下游河道演算。</figcaption>
</figure>

<figure class="figure-card">
  <img src="assets/diagrams/framework.png" alt="設定檔、後端、稽核器與 HydroCNHS 主機之間的軟體模組資料流圖">
  <figcaption><strong>軟體耦合視圖。</strong> 資料依序流經 <code>configuration.py</code>、<code>workflow.py</code>、<code>information.py</code>、<code>configured_backend.py</code>／<code>rule_based.py</code>、<code>auditor.py</code>，以及位於 <code>network.py</code> 的 HydroCNHS 主機執行迴圈。</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. HydroCNHS 入流</strong>時間步 <code>t</code> 的演算入流 <code>Q_routed</code> (m3/s)</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 物理觀測</strong><code>ReservoirObservation</code>（<code>storage_m3</code>、上下限）</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 資訊與 DKP</strong><code>InformationCatalog</code> 與 <code>context_providers</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 提示詞組裝</strong><code>ConfiguredBackend</code> / <code>StudyBackend</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 決策推論</strong>LLM 模型服務或決定性規則</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 解析與換算</strong>嚴格 JSON 解析並換算為 <code>m3/s</code></div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. 稽核檢查</strong><code>AuditedBackend</code> 查核邊界與欄位範圍</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. 物理與演算</strong><code>apply_transition</code> + 下游單位歷線</div>
</div>

## 逐時間步耦合資料流

在每個操作時間步 `t`（依水庫與匯流點的拓樸順序依序執行），執行期會依序完成以下八個決定性階段：

| 階段 | 模組／類別 | 輸入 | 輸出 | 原生單位與不變量 |
| --- | --- | --- | --- | --- |
| 1. 集水區／上游入流 | `network.py` / `interval_network.py` | 區域 `inflows.csv` + 經 `unit_hydrograph` 演算之上游 `total_outflow_cms` | `Q_routed[inflow_node][t]` | 時段平均 `m3/s`；區域入流量不得重複計入上游放流量。 |
| 2. 物理觀測封裝 | `agent.py`（`LLMReservoirAgent`） | 期初 `storage_m3`、`inflow_cms`、`PhysicalConfig` | `ReservoirObservation`（`reservoir-observation.v1`） | `storage_m3` 單位為 `m3`；`release_upper_bound_cms` 為該步物理可行最大受控放流量（`m3/s`）。 |
| 3. 資訊與情境檢索 | `information_runtime.py` / `context.py` | 因果 `InformationCatalog` + 惰性 `context_providers` | `observation.context["decision_information"]` + `ContextValue` | `valid_time` / `available_at` / `issued_at <= clock`；唯讀凍結 JSON。 |
| 4. 提示詞格式化 | `configured_backend.py`（`ConfiguredBackend`） | `PromptSpec`、`knowledge`、`previous_transition`、`completed_history` | `PromptRequest`（`messages`、`request_sha256`） | 每次決策僅組裝一次；重試與備援模型皆共用完全相同的訊息。 |
| 5. 策略決策 | `ConfiguredBackend` / `RuleBasedBackend` | `PromptRequest` 或 `ReservoirObservation` | 原始回覆 JSON 或 `ReservoirAction` | LLM 需明確傳入 `--allow-network`；規則式強制要求 `network_calls == 0`。 |
| 6. JSON 解析與單位換算 | `contracts.py` / `response_extension` | 模型服務回覆文字或自訂 JSON schema | `ReservoirAction`（`reservoir-action.v1`） | 將場址單位（例如 `release_cfs * 0.028316847`）顯式換算為 `release_cms`（`m3/s`）。 |
| 7. 決策稽核 | `auditor.py`（`AuditedBackend`） | `reservoir-audit-input.v1`（`observation`、`action`、追蹤紀錄） | 診斷結果 `PASS` / `WARN` / `FAIL` / `UNKNOWN` | 在物理更新前檢視 `action`；**絕不竄改** `release_cms`。 |
| 8. 質量平衡與河道演算 | `physics.py`（`apply_transition`） | `storage_start_m3`、`inflow_cms`、`target_release_cms` | `Transition`（`controlled_release_cms`、`spill_cms`、`storage_end_m3`） | 截幅至 `[min, max]` 與呆庫容保護線；`residual <= 1e-6 + 1e-12 * scale`；將 `total_outflow_cms` 送往下游。 |

## 規則式操作員與 Python 擴充套件

`src/llm_reservoir_agent/agent_configuration.py` 將公開的操作員方法區分為兩種明確類型（`type: rule_based` 與 `type: llm`），另保留 `mode: offline` 搭配固定放流量 `release_cms` 供快速流程煙霧測試使用。

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based`（決定性規則擴充）

- **必填 YAML 欄位**：`reservoir_id`、`type: rule_based`、`rule`，選填 `rule_parameters`、`auditors` 與 `customization.information`。
- **執行方式**：一律離線執行（`mode: offline`）。由 `RuleBasedBackend`（`src/llm_reservoir_agent/rule_based.py`）封裝，於每次 `decide(observation)` 前後核對 `network_calls == 0`，並綁定 `no_model_transport`。
- **禁用欄位**：不可宣告 `model_profile`、`prompt_file` 或任何 LLM 專用客製化欄位。

</div>
<div class="panel-card" markdown="1">

### `type: llm`（模型驅動操作員）

- **必填 YAML 欄位**：`reservoir_id`、`type: llm`、`model_profile`、`prompt_file`，選填 `auditors` 與 `customization:`。
- **執行方式**：預設為 `customization.execution: live`（`mode: llm`）。若設定 `execution: replay`（`mode: offline`），則改以離線方式重播既定回覆，不呼叫模型服務。
- **禁用欄位**：不可宣告 `rule` 或 `rule_parameters`；在 `llm` 模式下不可設定固定備援放流量 `release_cms`。

</div>
</div>

### 內建與擴充 Hanasaki 規則

HydroReOpLLM 以兩種方式支援 **Hanasaki** 滯洪／水庫操作公式：

1. **擴充套件形式（`type: rule_based` + `rule: hanasaki`）** —— 見於 [`examples/fe_walter/rule_based.yaml`](../examples/fe_walter/rule_based.yaml) 與 [`examples/fe_walter/study/rule/__init__.py`](../examples/fe_walter/study/rule/__init__.py)（`HanasakiBackend`，`policy_id = "hanasaki_flood_control"`）：
   - 計算調蓄度 γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>) 與年度放流係數 <i>k</i><sub>rls</sub> = <i>S</i><sub>year_start</sub> / (α<i>C</i>)，並於每個日曆年的第一個時間步更新年度快照。
   - 套用生態基流量下限 0.1 <i>Q&#772;</i><sub>in</sub>、操作蓄水上限 α<i>C</i> 與最低蓄水門檻 0.1 <i>C</i>。
   - 每次決策皆與主機 `apply_transition` 比對物理一致性（若發生衝突則在推進狀態前拋出 `physical_conflict` 例外）。
   - 透過 `rule_parameters` 設定：`purpose: flood_control`、`alpha: 0.85`，以及 `inflow_statistics_file`（具 SHA-256 驗證之 `reservoir-benchmark-statistics.v1` JSON，標明 `reference_mode: pre_simulation | retrospective`）或 `mean_inflow_cms`。
2. **內建舊版 `strategy: benchmark`** —— 實作於 `src/llm_reservoir_agent/benchmark.py`（`BenchmarkBackend`）與 `benchmark_config.py`（`load_benchmark`），支援搭配 12 個月氣候平均值的逐日 Hanasaki 放流計算及模擬前資料洩漏檢查（`reference_end < simulation_start`）。

<div class="callout callout-info" markdown="1">

**上游來源說明。** `examples/fe_walter/study/rule/__init__.py` 中的 `flood_control_step` 實作重現了 Hanasaki et al. (2006) / Abeshu et al. (2023) 的 Hanasaki 滯洪運轉公式（`HanasakiBackend`），並與鎖定版本的 `RiverAI-Project/MOSART-Urban` 參考實作（見 `scripts/verify_hanasaki_rule.py` 與 `THIRD_PARTY_NOTICES.md`）維持數值等價，同時完整保留 HydroReOpLLM 的中立 SI 物理核心。

</div>

### 自訂擴充模組掛載契約

在頂層設定 `extensions:` 中以 `<extension_id>: path/to/__init__.py` 註冊外部 Python 套件。`src/llm_reservoir_agent/extensions.py`（`load_extension`、`extension_registry`）會為套件目錄下所有 `.py` 檔案計算 SHA-256 雜湊值，並載入至雜湊隔離命名空間 `_hydroops_extension_<signature>`，確保修改原始碼後不會誤用舊版快取模組。

| 掛載函式／屬性 | 適用對象 | 函式簽章與職責說明 |
| --- | --- | --- |
| `validate_backend(...)` | 規則與 LLM 後端擴充 | `(spec, *, base_path, runtime_root, physical, mode, days\|steps, dt_seconds, model, auditor_settings, [simulation_start]) -> (normalized_dict, file_pins)` |
| `build_backend(...)` | 規則與 LLM 後端擴充 | `(settings, *, physical, runtime_root, mode, model, transport, [agent_id, context_providers]) -> backend_with_decide` |
| `rebase_agent(spec, *, base_path)` | 選填（強烈建議） | 相對於宣告該設定的 YAML 目錄，解析 `rule_parameters` 或自訂欄位內的相對資源路徑（`configuration.py`）。 |
| `preview_backend(settings, *, physical, runtime_root)` | 選填 | 當擴充模組不使用 `prompt_file` 而自行組裝提示詞時，回傳離線預覽酬載（參考 `examples/fe_walter/study/__init__.py`）。 |
| `supported_dt_seconds` | 時距（`v3` / 逐時）擴充 | 支援的整數時間步長（秒）清單或元組（例如 `(3600,)`）。 |
| `supports_prompt_context = True` | 支援情境提示詞的擴充 | 宣告啟用 `information` 設定檔注入與 `context_providers` 回呼功能。 |
| `validate_context` / `build_context` / `rebase_context` | `context_providers` 擴充 | 驗證設定、回傳 `ContextProvider(DecisionContext) -> ContextValue` 可呼叫物件，並重新定址相對路徑。 |
| `validate_auditor` / `build_auditor` / `rebase_auditor` | 自訂稽核器擴充 | 回傳提供 `AuditSpec`（`auditor_id`、`version`、`rubric`）與 `audit(context)` 方法的 `AuditPlugin` 實例。 |

## LLM 操作員 YAML 設定結構

在 `hydroops-coupled-simulation.v2`（或使用 `normalize_agent` 的 `v1` 設定）中，於 `agents.<agent_id>` 底下宣告個別操作員。**切勿在同一個操作員區段內混用**公開欄位（`reservoir_id`、`type`、`model_profile`、`prompt_file`、`customization`）與舊版欄位（`reservoir`、`mode`、`strategy`、`model`、`prompt`）。

| 欄位路徑 | 型別／允許值 | 用途與程式碼對應 |
| --- | --- | --- |
| `reservoir_id` | 非空字串 | 對應 `network.reservoirs` 中的水庫鍵名（所有 `controlled` 水庫皆須 1 對 1 完整覆蓋）。 |
| `type` | `llm` \| `rule_based` | 選擇 LLM 或決定性規則處理管線（`agent_configuration.py`）。 |
| `model_profile` | `models:` 內的字串鍵名 | 主要模型服務設定檔（由 `validate_model_settings` 驗證）。 |
| `prompt_file` | 相對路徑（UTF-8 純文字） | 使用者提示詞範本（`PromptSpec.template`）；除非由 `customization.backend` 自行組裝提示詞，否則為必填。 |
| `auditors` | 不重複的稽核器 ID 清單 | `auditors:` 底下宣告的鍵名，透過 `AuditedBackend` 包覆此操作員。 |
| `customization.system_prompt_file` | 相對路徑（UTF-8 純文字） | 系統提示詞（`PromptSpec.system_template`）；納入 `content_sha256` 雜湊計算。 |
| `customization.prompt_version` | 字串（預設 `'1'`） | 記錄於 `PromptSpec` 來源追蹤資訊中的人類可讀範本版本標籤。 |
| `customization.prompt_variables` | `{identifier: JSON}` 對應 | 注入至 `$<identifier>` 佔位符的靜態變數（不可覆寫內建保留名稱）。 |
| `customization.context_providers` | `{alias: {extension, config, preview}}` 對應 | 回傳 `ContextValue` 的惰性執行期檢索回呼；離線 `check` 時會改用 `preview` 內容。 |
| `customization.knowledge` | `{pkg_id: path}` 對應 | 靜態文字檔案（例如 DKP 手冊），逐檔計算雜湊並以 JSON 格式注入 `$knowledge`。 |
| `customization.context` / `context_file` | 對應物件或 JSON 檔案路徑 | 嵌入於 `$observation` 的 `"static_context"` 欄位中之靜態 JSON，兩者最多擇一。 |
| `customization.information` | `information.profiles` 內的字串鍵名 | 綁定具因果時序的 `InformationCatalog` 設定檔；通用 LLM 代理人提示詞須包含 `$information`。 |
| `customization.response_schema` | 字串（預設 `reservoir-action.v1`） | 非預設 schema 須對應已註冊的 `extensions.<response_schema>` 解析器（`parse_response`）。 |
| `customization.fallback_models` | `models:` 中的設定檔鍵名清單 | 依序排列的備援設定檔（不可重複且不可與主 `model_profile` 相同），於 HTTP 429/5xx、逾時、連線異常或 JSON 解析失敗時啟用。 |
| `customization.history_steps` | 整數 `>= 0`（預設 `0`） | 保留於 `$completed_history` 中的最近連續已提交狀態轉移步數。 |
| `customization.execution` | `live`（預設） \| `replay` | 須搭配 `customization.backend`。將 LLM 架構識別與即時推論／離線重播模式解耦。 |
| `customization.backend` 與 `parameters` | 已註冊擴充 ID 與參數對應 | 將執行委派給 `extensions:` 註冊的套件；`parameters` 不得覆寫受保護的代理程式核心欄位。 |

混合式拆檔設定範例（取自 `tests/fixtures/examples/multiple_reservoirs/agents.llm.yaml`）：

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    prompt_version: '1'
    prompt_variables:
      purpose: demonstrate an independently configured operator
    context_providers:
      guidance:
        extension: local_retrieval
        config:
          documents: knowledge/guidance.json
        preview: 'Offline preview: use only the supplied state and local operating guidance.'
  auditors:
  - bounds
```

## 提示詞結構與變數替換

`ConfiguredBackend`（`src/llm_reservoir_agent/configured_backend.py`）使用 Python `string.Template`（`$placeholder` 語法）渲染提示詞範本。`prompt_file` 與 `system_prompt_file` 中的每一個佔位符都會在 `load_settings` 階段即完成檢查；任何未宣告的佔位符會在發出 API 請求前直接驗證失敗。

| 佔位符 | 來源 | 決策時注入結構 |
| --- | --- | --- |
| `$observation` | `ReservoirObservation` + `context` | 標準 JSON `{"observed_hydrology": {...}, "static_context": {...}}`（`inflow_cms` 單位為 `m3/s`、`storage_m3` 單位為 `m3`）。 |
| `$previous_transition` | `record_transition()` | 最近一次已提交的 `{observation, action, transition}` JSON，於 `timestep == 0` 時為 `null`。 |
| `$completed_history` | `history_steps` 環形緩衝區 | 由最近 `history_steps` 筆連續已提交轉移紀錄組成的 JSON 清單。 |
| `$knowledge` | `customization.knowledge` | `{package_id: text}` JSON 對應表，並依 `PromptSpec` 中的 SHA-256 進行驗證。 |
| `$information` | `InformationCatalog` | 來自 `observation.context` 的選定 `decision_information` 快照（須設定 `customization.information`）。 |
| `$agent_id` | 代理人 YAML 鍵名 | JSON 編碼的操作員識別字串。 |
| `$<custom>` | `prompt_variables` 或 `context_providers` | 原始字串（當 `available` 且型別為 `str`）或標準 JSON（若不可用則為 `null`）。 |

在 **F.E. Walter** 案例研究（`examples/fe_walter/study/__init__.py` 與 `formatter.py`）中，`StudyBackend` 繼承了 `ConfiguredBackend`，內建等價於 `history_steps` 的 `deque(maxlen=2)` 回饋視窗，並透過動態 `$study_message` 回呼執行三項工作：
1. 依 `elevation_storage.csv` 將期初 `storage_m3` 換算為水庫水位（`ft NGVD29`），並將入流量換算為 `cfs`。
2. 整理前兩日已提交的決策與實際執行結果（並列比較 `decided` 與 `actually released`，並註記呆庫容限制或溢流情況）。
3. 在 `study_method: dkp` 條件下，從 `dkp.md` 檢索當日適用規則（常駐納入 `R-RELEASE`、`R-MINNORM`、`R-ATSITE`、`R-ZONE`，並依水位超過季節目標與 4–10 月期間條件式納入 `R-PLAN` 與 `R-RECREATION`）。

## 結構化 JSON 輸出與單位換算

只要在設定中提供 `response_json_schema`，模型服務轉接器（`src/llm_reservoir_agent/providers.py`）便會向各家模型服務請求原生結構化 JSON 輸出（Ollama 使用 `format`、`openai_compatible` 使用 `response_format.json_schema`、`openai` 使用 `text.format`、`anthropic` 使用 `output_config.format`、`gemini` 使用 `generationConfig.responseJsonSchema`）。

- **標準契約（`reservoir-action.v1`）**：`ACTION_JSON_SCHEMA` 嚴格要求 `{"schema_version": "reservoir-action.v1", "release_cms": <number >= 0>}`，且設定 `additionalProperties: false`。
- **場址慣用單位 schema（`response_schema` / `response_extension`）**：採用非 SI 單位（如美國陸軍工兵團常用的 `cfs` 與 `ft NGVD29`）的研究案例，可提供專屬的領域 JSON schema，並在 `parse_response` 內進行明確換算後再回傳 `{"schema_version": "reservoir-action.v1", "release_cms": ...}` 給主機核心。
  - 例如 `examples/fe_walter/study/response_schemas.json` 要求模型輸出 `applicable_target_ft`、`pool_position`、`intended_storage_direction`、`release_relation_to_inflow`（`dkp` 模式另須包含 `operating_mode` 與 `rules_applied`）、`reasoning` 及 `release_cfs`，再由 `_parse_release` 將 `release_cfs * 0.028316847` 換算為 `release_cms`。
- **嚴格 JSON 解碼**：`_strict_json` 會拒絕重複的 JSON 鍵名、`NaN`、`Infinity`、遭截斷的回覆（`finish_reason == "length"` / `MAX_TOKENS`）以及模型服務的拒答回應。

## 安全閘門、物理限幅與決定性重播

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 閘門一：事前檢查與呼叫預算閘門（`workflow.py`）

- **離線預覽**：`reservoir-experiment check` 以 `0` 次網路呼叫執行 `ConfiguredBackend.preview()`，產出第 0 步的完整訊息與 SHA-256 請求雜湊值。
- **明確網路授權**：執行 `run` 時，必須同時傳入 `--allow-network` **且** `case.json` 設定 `"live_readiness": {"ready": true}`（或 `data_kind: synthetic_fixture`），否則系統會拒絕連線。
- **預算上限**：`max_calls` 必須足以涵蓋 `llm_agent_count * steps`；每次主要嘗試、重試與備援呼叫前，都會先在 `provider_attempts.jsonl` 以 append-fsync 寫入一筆 `STARTED` 預約紀錄。

</div>
<div class="panel-card" markdown="1">

### 閘門二：稽核器與物理強制邊界（`auditor.py`、`physics.py`）

- **稽核器（`ConfiguredAudit`）**：`release_bounds`（`tolerance_cms`）檢查 `0 <= release_cms <= release_upper_bound_cms + tolerance_cms`；`field_range` 檢查以點號分隔的 `observation.*` 或 `action.*` 欄位是否落於 `[minimum, maximum]`。稽核結果（`PASS`/`WARN`/`FAIL`/`UNKNOWN`）僅供診斷參考，絕不改寫原始放流請求。
- **主機物理核心（`apply_transition`）**：將 `target_release_cms` 限幅於 `[minimum_release_cms, maximum_release_cms]`、限制放流水量不得低於 `dead_storage_m3`、將超過 `capacity_m3` 的多餘水量記為 `spill_cms`，並驗證水量平衡誤差在 `1e-6 + 1e-12 * scale` m3 以內。

</div>
</div>

### 決定性重播與中斷續跑

- **離線重播（`llm-reservoir-daily` / `RecordedResponseBackend`）**：將封存的放流序列（`recorded_llm_response`）送入完全相同的 `run_network` 主機、`apply_transition` 核心與河道演算檢查流程，過程中維持 `0` 次模型服務呼叫（見 `examples/fe_walter/study/replay.py`）。
- **中斷續跑（`reservoir-experiment resume`）**：`RecoveryTape`（`src/llm_reservoir_agent/recovery.py`）會核對輸入檔案與執行環境雜湊值是否一致，將先前已完成的回覆與檢索資訊重播至全新的 `--output` 目錄，逐日重算並驗證物理轉移紀錄，同時保留原本計入 `max_calls` 的 `STARTED` 呼叫次數。
