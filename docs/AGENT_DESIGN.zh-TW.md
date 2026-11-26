# 操作員與 LLM 代理人設計

<div class="hero-band" markdown="1">

HydroReOpLLM 將 **「操作決策」**（決定性規則或 LLM 操作策略）與 **「物理水量平衡」**（共用的 HydroCNHS `Dam` 質量平衡與河道演算引擎）清楚分離。規則式與 LLM 操作員觀測完全相同的水庫狀態、回傳以 `m³/s` 計量的請求放流量，並遵守完全一致的放水設施上下限、呆庫容保護與溢流物理機制。

</div>

## 與 HydroCNHS 的架構邊界

HydroReOpLLM 封裝了 HydroCNHS 的代理人建模（`ABM`）水庫介面（`examples/llm_reservoir_abm.py`）。每座受控水庫從 HydroCNHS 接收演算後的入流歷線，將當期期初蓄水量與可行放流上下限提供給指派的操作員，最後把 `controlled_release_cms + spill_cms` 回傳給 HydroCNHS 進行下游河道演算。

由於決策後端只負責提出目標放流量、從不直接修改蓄水量或河道演算，因此您可以在完全相同的集水區水文條件下比較 **Hanasaki 規則**、**自訂 Python 運轉規線**與 **LLM 操作員**，無須更動任何一項水文參數。

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="整合 HydroCNHS 與 LLM／規則操作員的閉迴路水庫操作架構圖">
  <figcaption><strong>圖 1.</strong> 閉迴路水庫操作架構：集水區逕流進入水庫後，操作員評估當期蓄水、入流、預報／觀測資料或操作知識（DKP）以提出放流量，再由主機物理核心落實操作限制與水量守恆後進行下游演算。</figcaption>
</figure>

<figure class="figure-card">
  <img src="assets/diagrams/framework.png" alt="連接水文輸入、操作員、稽核器與 HydroCNHS 演算的模擬流程圖">
  <figcaption><strong>模擬模組工作流程。</strong> 說明實驗設定、因果資訊檢索、規則或 LLM 決策後端、診斷稽核器與 HydroCNHS 河道演算如何在每個時間步協同運作。</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. 集水區入流</strong>區域逕流 + 延遲上游出流（m³/s）</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 水庫狀態</strong>期初蓄水量（m³）與可行上下限</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 資訊與 DKP</strong>測站、預報、目標與手冊條文</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 提示詞組裝</strong>填入系統與每日使用者範本</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 決策計算</strong>規則公式或 LLM 推論</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 解析與換算</strong>擷取 JSON 並換算為 m³/s</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. 稽核檢查</strong>標記越界或範圍異常</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. 物理與演算</strong>呆庫容保護、溢流與下游演算</div>
</div>

## 逐時間步耦合資料流

在每個時間步 `t`（由上游至下游依序推進整個流域），每座受控水庫都會執行以下八個步驟：

| 階段 | 水文與操作流程 | 輸入 | 輸出 | 單位 |
| --- | --- | --- | --- | --- |
| 1. 集水區與上游入流 | 將子集水區區域逕流與上游水庫延遲抵達的放流量相加。 | `inflows.csv` + 上游 `total_outflow_cms` | 演算後水庫入流量 `inflow_cms` | `m³/s`（時段平均） |
| 2. 水庫狀態觀測 | 擷取當期期初蓄水量與可行放水設施上限。 | `storage_m3`、`inflow_cms`、`PhysicalConfig` | 觀測快照與 `release_upper_bound_cms` | `m³`、`m³/s` |
| 3. 資訊與 DKP 檢索 | 附加符合因果時序的觀測、預報、運轉規線或適用 DKP 條文。 | `information` 設定檔／`context_providers` | 唯讀決策情境 | 宣告的場址單位或 SI 單位 |
| 4. 提示詞格式化 | 將當期狀態、先前已執行放流與操作知識填入提示詞範本。 | 系統與使用者提示詞檔 + 歷史紀錄 | 組裝完成之提示詞訊息（LLM 用） | 純文字 |
| 5. 操作員決策 | 計算規則公式或查詢指定的 LLM 模型服務。 | 觀測快照（規則）或提示詞訊息（LLM） | 建議放流決策 | `m³/s` 或場址單位（如 `cfs`） |
| 6. 解析與單位換算 | 從 JSON 回覆擷取放流數值並由場址單位換算為 SI。 | 結構化 JSON 回覆 | 請求控制放流量 `target_release_cms` | `m³/s` |
| 7. 診斷稽核 | 檢查請求放流量是否超出上下限或自訂門檻。 | 觀測快照 + 請求放流量 | `PASS`、`WARN`、`FAIL` 或 `UNKNOWN`（不改寫流量） | 僅供診斷 |
| 8. 主機物理與演算 | 套用 `[min, max]` 限制、保護 `dead_storage_m3`、計算 `spill_cms` 並演算至下游。 | `storage_start_m3`、`inflow_cms`、`target_release_cms` | `controlled_release_cms`、`spill_cms`、`storage_end_m3` | `m³/s`、`m³` |

## 規則式操作員與 Python 擴充套件

需要決定性水文基準與對照組時請使用 `type: rule_based`，進行模型驅動水庫操作時則使用 `type: llm`：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based`（決定性規則）

- **必填欄位**：`reservoir_id`、`type: rule_based`、`rule`，選填 `rule_parameters`、`auditors` 與 `customization.information`。
- **網路使用**：嚴格為 `0` 次模型呼叫（`max_calls: 0` 或 `null`）。
- **適用情境**：Hanasaki 滯洪基準、季節運轉規線或自訂 Python 水文操作規則。

</div>
<div class="panel-card" markdown="1">

### `type: llm`（模型驅動操作員）

- **必填欄位**：`reservoir_id`、`type: llm`、`model_profile`、`prompt_file`，選填 `auditors` 與 `customization:`。
- **網路使用**：即時推論（`customization.execution: live`）須加上 `--allow-network`；離線重播（`execution: replay`）則為 `0` 次呼叫。
- **適用情境**：權衡多目標運轉、結合預報資訊與閱讀結構化／非結構化水庫運用要點（DKP）。

</div>
</div>

### 內建與擴充 Hanasaki 規則

**Hanasaki** 滯洪基準（`examples/fe_walter/rule_based.yaml`、`examples/fe_walter/study/rule/__init__.py`）依據水庫的調蓄程度與年度蓄水狀態決定每日放流量：

- **調蓄度（Regulation ratio）**：γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>)，比較水庫總容量 <i>C</i>（m³）與長期平均入流量 <i>Q&#772;</i><sub>in</sub>（m³/s）對應的年平均入流體積。蓄水相對於入流較大的水庫會以年度蓄水進行平滑調節；當 γ &lt; 0.5（較接近川流式）時，則提高當日入流量的權重。
- **年度放流係數**：<code>k_rls</code> = <i>S</i><sub>year_start</sub> / (α · <i>C</i>)，於每個日曆年的第一個時間步更新年度快照，並以 α · <i>C</i> 作為滯洪蓄水上限（預設 α = 0.85）。
- **操作下限與上限**：維持至少 0.1 · <i>Q&#772;</i><sub>in</sub> 的生態基流量；當蓄水超過 α · <i>C</i> 時增加放流以保留滯洪空間；同時保護 0.1 · <i>C</i> 的最低蓄水量。

```yaml
# examples/fe_walter/rule_based.yaml（節錄）
agents:
  walter_operator:
    reservoir_id: FEWalter
    type: rule_based
    rule: hanasaki
    rule_parameters:
      purpose: flood_control
      alpha: 0.85
      inflow_statistics_file: rule_statistics.json   # 1996-2015 參考入流統計（或改填 mean_inflow_cms）
    auditors: [release_bounds]
extensions:
  hanasaki: study/rule/__init__.py
```

<div class="callout callout-info" markdown="1">

**上游來源說明。** `examples/fe_walter/study/rule/__init__.py` 中的 `flood_control_step` 實作依循 Hanasaki et al. (2006) / Abeshu et al. (2023)，並與 `RiverAI-Project/MOSART-Urban` 參考公式（`scripts/verify_hanasaki_rule.py`、`THIRD_PARTY_NOTICES.md`）在 HydroReOpLLM 的中立 SI 核心中維持一致。

</div>

### 自訂擴充模組掛載契約

若要撰寫自己的季節運轉規線或特定場址 Python 操作規則，請在頂層 `extensions:` 註冊套件資料夾（指向其 `__init__.py`），並實作 `validate_backend`、`build_backend` 與回傳 `{"release_cms": ...}` 的 `decide(observation)`（須包含 `network_calls = 0`）：

```python
# my_rules/__init__.py — 約 15 行的極簡自訂運轉規線範例
class GuideCurveRule:
    network_calls = 0  # 必要安全宣告：確認此規則絕不呼叫 LLM

    def __init__(self, target_storage_m3, base_release_cms):
        self.target = target_storage_m3
        self.base = base_release_cms

    def decide(self, observation):
        storage = observation["state"]["storage_m3"]
        inflow = observation["inflow_cms"]
        # 高於目標蓄水時至少放流等於入流量；低於目標蓄水時減半基流以蓄水
        release = max(inflow, self.base) if storage > self.target else self.base * 0.5
        return {"release_cms": release}

def validate_backend(spec, **kwargs):
    return {"rule_parameters": spec.get("rule_parameters", {})}, {}

def build_backend(settings, **kwargs):
    p = settings["rule_parameters"]
    return GuideCurveRule(p["target_storage_m3"], p["base_release_cms"])
```

選填的擴充功能還包含 `rebase_agent`（解析 `rule_parameters` 內的相對檔案路徑）、`preview_backend`（自訂第 1 天的離線預覽訊息）、`supported_dt_seconds`（例如逐時模擬宣告 `(3600,)`）以及 `supports_prompt_context = True`（允許規則讀取 `information` 設定檔與 `context_providers`）。

## LLM 操作員 YAML 設定結構

在 `hydroops-coupled-simulation.v2`（或 `v1`）中，於 `agents.<agent_id>` 底下設定每名 LLM 操作員。請將公開欄位（`reservoir_id`、`type`、`model_profile`、`prompt_file`、`customization`）與舊版欄位（`reservoir`、`mode`、`strategy`、`model`、`prompt`）分開使用——切勿在同一個操作員區段內混用。

| 欄位路徑 | 型別／設定值 | 水文與操作功能 |
| --- | --- | --- |
| `reservoir_id` | 水庫鍵名 | 對應 `network.reservoirs` 中的水庫鍵名（每座受控水庫對應一名操作員）。 |
| `type` | `llm` \| `rule_based` | 選擇 LLM 推理或決定性規則。 |
| `model_profile` | `models:` 中的鍵名 | 主要本機或雲端 LLM 設定檔（見[模型服務與可重現性](LLM_MODULES.zh-TW.md)）。 |
| `prompt_file` | 相對 `.txt` 路徑 | 每日／每步使用者提示詞範本，內含 `$observation` 與選用佔位符。 |
| `auditors` | 稽核器 ID 清單 | 包覆此操作員的診斷檢查（例如 `[release_bounds]`）。 |
| `customization.system_prompt_file` | 相對 `.txt` 路徑 | 常駐系統指令：水庫角色、滿庫與呆庫容限制、季節目標與 JSON 輸出格式。 |
| `customization.prompt_version` | 字串（預設 `'1'`） | 用於區分與追蹤不同實驗提示詞修訂版本的標籤。 |
| `customization.prompt_variables` | `{name: value}` | 透過 `$name` 注入的靜態參數（例如目標水位或水庫名稱）。 |
| `customization.context_providers` | `{alias: {extension, config, preview}}` | 動態 Python 檢索器（例如依當日水位篩選適用的 DKP 操作規則）。 |
| `customization.knowledge` | `{pkg_id: path}` | 透過 `$knowledge` 注入的靜態操作手冊文字檔。 |
| `customization.context` / `context_file` | 對應物件或 JSON 路徑 | 附帶於 `$observation`（`static_context`）內的固定場址中繼資料。 |
| `customization.information` | 資訊設定檔鍵名 | 綁定具因果時序的[決策時資訊](INFORMATION.zh-TW.md)設定檔（提示詞須包含 `$information`）。 |
| `customization.response_schema` | schema 名稱 | 自訂結構化 JSON 輸出（例如先輸出推論欄位與 `release_cfs`，再換算為 SI）。 |
| `customization.fallback_models` | 設定檔鍵名清單 | 主模型逾時或回傳無效 JSON 時，依序切換的備援模型設定檔。 |
| `customization.history_steps` | 整數 `>= 0` | 納入 `$completed_history` 的先前連續已提交轉移步數。 |
| `customization.execution` | `live`（預設） \| `replay` | 在即時模型推論與離線決定性重播之間切換（需搭配 `customization.backend`）。 |

```yaml
# 完整附註解的 LLM 操作員設定範例（拆檔式 v2 架構）
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local                # 定義於 models.yaml（例如 Ollama gemma4:12b）
  prompt_file: prompts/operator.txt   # 每日水文狀態與決策提示詞範本
  customization:
    system_prompt_file: prompts/system.txt
    prompt_version: '1'
    history_steps: 2                  # 顯示前兩天的請求放流與實際執行放流
    information: upstream_and_forecast # 來自 information.yaml 的因果測站／預報檢視
    fallback_models: [cloud_backup]
  auditors: [release_bounds]
```

## 提示詞結構與變數替換

好的水庫操作 LLM 提示詞通常結合一份**穩定的 System Prompt**（說明水庫物理限制、防洪與供水優先順序、季節目標水位與 JSON 輸出格式），以及一份在每個時間步透過 `$placeholder` 填入當日水情的**動態 User Prompt**：

| 佔位符 | 決策當下提供的內容 | 典型水文操作用途 |
| --- | --- | --- |
| `$observation` | 當期 `inflow_cms`（m³/s）、期初 `storage_m3`（m³）、可行放流上限與 `static_context`。 | 讓 LLM 掌握確切的當期蓄水量與當日入流量。 |
| `$previous_transition` | 前一步的 `target_release_cms`、`controlled_release_cms`、`spill_cms` 與 `storage_end_m3`（第 0 步為 `null`）。 | 避免閘門開度逐日劇烈震盪，並告知昨日請求是否遭到限幅或發生溢流。 |
| `$completed_history` | 最近 `history_steps` 筆連續已提交的狀態轉移紀錄。 | 提供連續多日的洪水漲落或枯水退水歷線脈絡。 |
| `$information` | 具因果時序的觀測值、預報資料、季節目標與已提交的上游水庫狀態。 | 注入下游水位站流量、入流預報或運轉規線（見[決策時資訊](INFORMATION.zh-TW.md)）。 |
| `$knowledge` | 宣告於 `customization.knowledge` 的檔案內容。 | 提供精簡版常駐標準作業程序（SOP）。 |
| `$<custom>` | 來自 `prompt_variables` 或 `context_providers` 的數值。 | 注入換算後的場址慣用單位（ft、cfs、acre-ft）或檢索出的 DKP 條文。 |

**來自 F.E. Walter 案例的設計經驗（`examples/fe_walter/study/formatter.py`）**：
1. **使用水文學家與操作員熟悉的工程單位**：F.E. Walter 的提示詞組裝程式透過 `study/elevation_storage.csv` 內插計算 `storage_m3`，將庫容顯示為水庫水位（`ft NGVD29`），並將入流與前兩日放流換算為 `cfs` 與 `acre-ft`。
2. **季節目標 vs. DKP**：*無操作知識*（`seasonal_target`）提示詞僅提供當日水位、季節目標水位（冬季 `1,300` ft／夏季 `1,370` ft）與兩日放流歷史；*含操作知識*（`dkp`）提示詞則會依水情從 `dkp.md` 檢索對應條文（`R-RELEASE`、`R-MINNORM`、`R-ATSITE`、`R-ZONE`，以及洪峰滯蓄期的 `R-PLAN` 或 4–10 月的 `R-RECREATION`），引導模型依循真實的水庫運用要點進行推理。

## 結構化 JSON 輸出與單位換算

預設情況下，HydroReOpLLM 要求 LLM 回傳包含 SI 單位放流量的嚴格 JSON 物件：

```json
{"schema_version": "reservoir-action.v1", "release_cms": 12.5}
```

若提示詞採用非 SI 工程單位（例如美國陸軍工兵團常用的 `cfs`），可搭配自訂 `response_schema`（參考 `examples/fe_walter/study/response_schemas.json`）與解析函式，先檢查模型的物理推論欄位，**再**將 `release_cfs` 換算為 SI 單位 `release_cms`：

- **F.E. Walter 回覆 schema 欄位**：`applicable_target_ft`、`pool_position`（`below_target` | `at_target` | `above_target`）、`intended_storage_direction`、`release_relation_to_inflow`（DKP 模式另含 `operating_mode` 與 `rules_applied`）、`reasoning` 以及 `release_cfs`。
- **邊界單位換算**：`_parse_release` 會將 `release_cfs * 0.028316847`（`CFS_TO_CMS`）換算為 `release_cms`，確保底層物理水量平衡核心一律嚴格使用 `m³/s` 與 `m³`。

## 安全閘門、物理限幅與決定性重播

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 閘門一：事前檢查與呼叫預算閘門

- **零成本預覽**：`reservoir-experiment check` 在發出任何 API 請求前，先行組裝第 1 天的提示詞並檢查所有物理邊界與單位。
- **明確網路授權**：僅當您傳入 `--allow-network` 且案例宣告 `"live_readiness": {"ready": true}`（或使用 `synthetic_fixture`）時，才會執行即時 LLM 呼叫。
- **預算上限（`max_calls`）**：限制總模型呼叫次數（含重試與備援），避免設定錯誤導致無上限的 API 費用。

</div>
<div class="panel-card" markdown="1">

### 閘門二：稽核器與物理強制邊界

- **診斷稽核器（`release_bounds`、`field_range`）**：檢查操作員請求的放流量是否落在可行放水設施範圍或自訂區間內，並於 `audit.jsonl` 記錄 `PASS` / `WARN` / `FAIL`，絕不改寫流量。
- **硬性物理限制**：水庫物理引擎一律將 `controlled_release_cms` 限幅於 `[minimum_release_cms, maximum_release_cms]`、防止蓄水跌破 `dead_storage_m3`、將超過 `capacity_m3` 的溢水記為 `spill_cms`，並逐日閉合水量平衡。

</div>
</div>

### 決定性重播與中斷復原

- **離線重播**：封存的 LLM 決策序列（`study/archived_releases.csv` 或 `llm-reservoir-daily`）可透過完全相同的水庫物理與河道演算網路以 `0` 次模型呼叫重播，用於驗證評估指標或測試下游敏感度。
- **中斷續跑**：若多年期 LLM 模擬中途停止，執行 `reservoir-experiment resume` 可保留既有部分輸出、直接重播已完成的決策而不重複呼叫 LLM，並將後續模擬無縫寫入全新的輸出目錄。
