# 操作員與 LLM 代理人設計

<div class="hero-band" markdown="1">

HydroReOpLLM 將 **「由誰決策」**（規則或 LLM）與 **「水量守恆」**（共用的 HydroCNHS `Dam` 質量平衡與河道演算引擎）清楚分離。

</div>

## 與 HydroCNHS 的架構邊界

HydroReOpLLM 介接 HydroCNHS 的 `Dam` 介面（`examples/llm_reservoir_abm.py`）：HydroCNHS 將演算入流與期初蓄水量交給操作員，再接收 `controlled_release_cms + spill_cms` 往下游演算。由於操作員絕不直接修改蓄水量，您可以在完全相同的集水區條件下自由切換 **Rule-based（Hanasaki 規則）**、**Without operational knowledge（無操作知識）** 與 **With operational knowledge（具操作知識）**。

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="整合 HydroCNHS 與 LLM／規則操作員的閉迴路水庫操作架構圖">
  <figcaption><strong>圖 1.</strong> 閉迴路耦合：集水區逕流進入水庫，規則或 LLM 操作員提出放流建議，主機物理核心落實蓄水與放流限制後再演算至下游。</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. 入流</strong>區域 + 上游逕流（m³/s）</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 狀態</strong>蓄水量（m³）與上下限</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 情境</strong>測站、預報與操作規則</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 提示詞</strong>填入範本</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 決策</strong>規則公式或 LLM</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 解析</strong>JSON 並換算為 m³/s</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. 稽核</strong>檢查邊界條件</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. 物理</strong>限幅、溢流與演算</div>
</div>

## 逐時間步耦合資料流

| 階段 | 水文與操作流程 | 輸出與單位 |
| --- | --- | --- |
| 1. 集水區與上游入流 | 將區域逕流與延遲抵達的上游放流相加。 | `inflow_cms`（`m³/s`） |
| 2. 水庫狀態觀測 | 讀取期初庫容與可行放水設施上限。 | `storage_m3`（`m³`）、`release_upper_bound_cms`（`m³/s`） |
| 3. 資訊與 DKP 檢索 | 附加因果測站觀測、預報或適用 DKP 條文。 | 唯讀決策情境 |
| 4. 提示詞格式化 | 將狀態、歷史放流與情境填入提示詞範本。 | 提示詞訊息（僅限 LLM） |
| 5. 操作員決策 | 計算規則公式或查詢 LLM 模型服務。 | 建議放流量（`m³/s` 或場址單位） |
| 6. 解析與單位換算 | 解析 JSON 並將場址單位（如 `cfs`）換算為 SI。 | `target_release_cms`（`m³/s`） |
| 7. 診斷稽核 | 標記越界或超限狀況，不改動實際流量。 | `PASS` / `WARN` / `FAIL` / `UNKNOWN` |
| 8. 主機物理與演算 | 限幅於 `[min, max]` 與 `dead_storage_m3`、計算 `spill_cms` 並演算至下游。 | `controlled_release_cms`、`spill_cms`、`storage_end_m3` |

## 規則式操作員與 Python 擴充套件

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based`（決定性規則）

- 須填寫 `reservoir_id`、`type: rule_based`、`rule` 與選填 `rule_parameters`。
- 嚴格離線執行（`0` 次呼叫），適合 Hanasaki 基準或自訂 Python 規則。

</div>
<div class="panel-card" markdown="1">

### `type: llm`（模型驅動操作員）

- 須填寫 `reservoir_id`、`type: llm`、`model_profile`、`prompt_file` 與 `customization:`。
- 即時推論（`execution: live`）需加上 `--allow-network`；離線重播（`execution: replay`）則為 `0` 次呼叫。

</div>
</div>

### 內建與擴充 Hanasaki 規則

**Rule-based（Hanasaki 規則）**基準（`examples/fe_walter/rule_based.yaml`）依調蓄度 γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>) 與年度係數 <code>k_rls</code> = <i>S</i><sub>year_start</sub> / (α · <i>C</i>)（每個日曆年更新，預設 α = 0.85）計算每日放流量，並強制維持最低流量 0.1 · <i>Q&#772;</i><sub>in</sub>、最低蓄水 0.1 · <i>C</i> 與滯洪上限 α · <i>C</i>。

```yaml
agents:
  walter_operator:
    reservoir_id: FEWalter
    type: rule_based
    rule: hanasaki
    rule_parameters: { purpose: flood_control, alpha: 0.85, inflow_statistics_file: rule_statistics.json }
    auditors: [release_bounds]
extensions:
  hanasaki: study/rule/__init__.py
```

<div class="callout callout-info" markdown="1">

**來源說明。** `flood_control_step` 依循 Hanasaki et al. (2006) / Abeshu et al. (2023) 實作，並與 `RiverAI-Project/MOSART-Urban` 參考公式一致（`scripts/verify_hanasaki_rule.py`、`THIRD_PARTY_NOTICES.md`）。

</div>

### 自訂擴充模組掛載契約

在 `extensions:` 底下註冊您的規則套件並實作 `validate_backend`、`build_backend` 與 `network_calls = 0`：

```python
class GuideCurveRule:
    network_calls = 0
    def __init__(self, target_storage_m3, base_release_cms):
        self.target, self.base = target_storage_m3, base_release_cms
    def decide(self, observation):
        s, q_in = observation["state"]["storage_m3"], observation["inflow_cms"]
        return {"release_cms": max(q_in, self.base) if s > self.target else self.base * 0.5}

def validate_backend(spec, **kwargs):
    return {"rule_parameters": spec.get("rule_parameters", {})}, {}

def build_backend(settings, **kwargs):
    p = settings["rule_parameters"]
    return GuideCurveRule(p["target_storage_m3"], p["base_release_cms"])
```

## LLM 操作員 YAML 設定結構

請將公開欄位（`reservoir_id`、`type`、`model_profile`、`prompt_file`、`customization`）與舊版欄位（`reservoir`、`mode`、`strategy`、`model`、`prompt`）分開使用。

| 欄位 | 用途 |
| --- | --- |
| `reservoir_id`、`type`、`model_profile`、`prompt_file`、`auditors` | 指定水庫、`llm` 模式、模型設定檔鍵名（[模型服務](LLM_MODULES.zh-TW.md)）、使用者提示詞與稽核器。 |
| `customization.system_prompt_file`、`prompt_version` | 常駐操作規則／JSON 格式指示與修訂版本標籤。 |
| `customization.prompt_variables`、`context` / `context_file` | 固定參數（`$var`）或置於 `$observation` 內的靜態場址 JSON。 |
| `customization.knowledge`、`context_providers` | 操作手冊文字檔（`$knowledge`）或動態規則檢索外掛。 |
| `customization.information` | 因果測站／預報檢視（見[決策時資訊](INFORMATION.zh-TW.md)；提示詞須包含 `$information`）。 |
| `customization.response_schema`、`fallback_models`、`history_steps` | 自訂 JSON schema、備援模型與先前歷史步數（`$completed_history`）。 |
| `customization.execution`（`live` \| `replay`）、`backend`、`parameters` | 在即時推論與自訂後端之決定性離線重播之間切換。 |

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    history_steps: 2
    information: upstream_and_forecast
    fallback_models: [cloud_backup]
  auditors: [release_bounds]
```

## 提示詞結構與變數替換

| 佔位符 | 每步注入的內容 |
| --- | --- |
| `$observation` | 當期 `inflow_cms`（`m³/s`）、`storage_m3`（`m³`）、放流上限與靜態情境。 |
| `$previous_transition`、`$completed_history` | 前一步（或前 `history_steps` 步）之請求放流、實際放流與溢流紀錄。 |
| `$information`、`$knowledge`、`$custom` | 因果測站／預報、靜態操作手冊或自訂工程單位變數。 |

**來自 F.E. Walter 案例的設計經驗（`examples/fe_walter/study/formatter.py`）**：

- **使用場址慣用單位**：透過 `elevation_storage.csv` 將 `storage_m3` 換算為 `ft NGVD29` 水位，並將流量換算為 `cfs` / `acre-ft`。
- **Without operational knowledge**（`seasonal_target.yaml`）：僅提供水庫水位、季節目標水位（冬季 `1,300` ft／夏季 `1,370` ft）與兩日放流歷史。
- **With operational knowledge**（`dkp.yaml`）：從 `dkp.md` 注入對應水情的操作規則條文（`R-RELEASE`、`R-MINNORM`、`R-ATSITE`、`R-ZONE`，以及 `R-PLAN` 或 `R-RECREATION`），引導模型引用手冊規則。

## 結構化 JSON 輸出與單位換算

- 預設回覆格式為 `{"schema_version": "reservoir-action.v1", "release_cms": <float >= 0>}`。
- 自訂 `response_schema`（如 `study/response_schemas.json`）可要求先輸出推理欄位與 `release_cfs`，再於進入物理核心前將 `release_cfs * 0.028316847` 換算為 SI 單位 `release_cms`。

## 安全閘門、物理限幅與決定性重播

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 閘門一：事前檢查與呼叫預算閘門

- `reservoir-experiment check` 以 `0` 成本預覽第 1 天的提示詞。
- 即時推論須同時具備 `--allow-network`、`"live_readiness": {"ready": true}`（或合成測試案例）與 `max_calls`。

</div>
<div class="panel-card" markdown="1">

### 閘門二：稽核器與物理強制邊界

- 稽核器（`release_bounds`、`field_range`）僅記錄 `PASS`/`WARN`/`FAIL`，不會改寫放流量。
- 主機物理核心強制將放流限制在 `[minimum_release_cms, maximum_release_cms]`、保護 `dead_storage_m3` 並計算超過 `capacity_m3` 的溢流。

</div>
</div>

離線零成本重播請使用 `examples/fe_walter/study/replay.py` 或 `llm-reservoir-daily`；中斷續跑請使用 `reservoir-experiment resume`，無須重複呼叫已完成的步驟。
