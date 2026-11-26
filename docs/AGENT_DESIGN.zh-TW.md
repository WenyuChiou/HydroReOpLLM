# 操作規則與 LLM 設計

<div class="hero-band" markdown="1">

HydroReOpLLM 將 **「水庫放流決策」**（操作規則或 LLM）與 **「水量平衡與演算」**（共用的水庫水量平衡引擎與河道演算）分離，確保不同策略在同一物理條件下公平比較。

</div>

## 決策與水量平衡的分工

在每個時間步中，集水區與上游來水先匯入水庫，水庫將期初蓄水量與可行放流上下限交給指派的操作員；操作員只需回傳目標放流量，實際受控放流、呆庫容保護、溢流與下游河道演算一律由水庫水量平衡引擎處理。因此，您可以在同一套集水區條件下自由切換 **Rule-based（Hanasaki 規則）**、**Without operational knowledge（無操作知識）** 與 **With operational knowledge（具操作知識）**。

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="整合 HydroCNHS 與水庫操作規則及 LLM 的閉迴路架構圖">
  <figcaption><strong>圖 1.</strong> 閉迴路模擬流程：集水區入流進入水庫，規則或 LLM 依水情提出目標放流量，再由水庫水量平衡引擎落實物理限制與下游演算。</figcaption>
</figure>

<div class="pipeline-strip">
  <div class="pipeline-step"><strong>1. 入流</strong>區域 + 上游來水（m³/s）</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>2. 狀態</strong>期初蓄水（m³）與上下限</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>3. 水情與知識</strong>測站、預報與操作手冊</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>4. 提示詞</strong>填入系統與每日範本</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>5. 決策</strong>操作規則或 LLM 推論</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>6. 解析</strong>擷取 JSON 並換算為 m³/s</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>7. 稽核</strong>檢查放流是否越界</div>
  <div class="pipeline-arrow">→</div>
  <div class="pipeline-step"><strong>8. 水量平衡</strong>限幅、溢流與下游演算</div>
</div>

在設計 LLM 操作員時，除了當日蓄水與入流外，還可提供**操作知識（operational knowledge）**——例如從真實水庫運用要點整理出的結構化條文（如 F.E. Walter 的 `dkp.md`）。系統可在每個時間步自動篩選符合當日水情的條文，連同測站與預報資料一併送入決策流程。

| 階段 | 水文與操作內容 | 輸出與單位 |
| --- | --- | --- |
| 1. 集水區與上游入流 | 將區域逕流加上延遲抵達的上游放流量。 | `inflow_cms`（`m³/s`） |
| 2. 水庫狀態觀測 | 讀取期初蓄水量與當步可行放流上限。 | `storage_m3`（`m³`）、`release_upper_bound_cms`（`m³/s`） |
| 3. 水情資訊與操作知識檢索 | 附加不洩漏未來水情之測站、預報或適用操作手冊條文。 | 唯讀決策情境 |
| 4. 提示詞組裝 | 將狀態、歷史放流與水情填入提示詞範本。 | 提示詞訊息（僅限 LLM） |
| 5. 操作員決策 | 計算水庫操作規則或查詢 LLM 模型服務。 | 建議放流量（`m³/s` 或場址單位） |
| 6. 解析與單位換算 | 解析 JSON 回覆並將場址單位（如 `cfs`）換算為 SI。 | `target_release_cms`（`m³/s`） |
| 7. 診斷稽核 | 標記越界或超限狀況，不改動實際放流。 | `PASS` / `WARN` / `FAIL` / `UNKNOWN` |
| 8. 水量平衡與河道演算 | 限幅於 `[min, max]` 與 `dead_storage_m3`、計算 `spill_cms` 並演算至下游。 | `controlled_release_cms`、`spill_cms`、`storage_end_m3` |

## 操作規則與自訂 Python 規則

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `type: rule_based`（水庫操作規則）

- 須設定 `reservoir_id`、`type: rule_based`、`rule` 與選填 `rule_parameters`。
- 全程離線執行（`0` 次模型呼叫），適合 Hanasaki 基準或自訂 Python 運轉規線。

</div>
<div class="panel-card" markdown="1">

### `type: llm`（LLM 操作員）

- 須設定 `reservoir_id`、`type: llm`、`model_profile`、`prompt_file` 與 `customization:`。
- 即時推論（`execution: live`）需傳入 `--allow-network`；離線重播（`execution: replay`）則為 `0` 次呼叫。

</div>
</div>

### Hanasaki 滯洪運轉規則

**Rule-based（Hanasaki 規則）**（`examples/fe_walter/rule_based.yaml`）透過以下五項水文參數決定每日放流量：

| 項目 | 公式或門檻 | 水文意義 |
| --- | --- | --- |
| 調蓄度 | γ = <i>C</i> / (<i>Q&#772;</i><sub>in</sub> · <code>SECONDS_PER_YEAR</code>) | 比較水庫容量 <i>C</i> 與年平均入流體積；γ &lt; 0.5 時提高當日入流權重。 |
| 年度放流係數 | <code>k_rls</code> = <i>S</i><sub>year_start</sub> / (α · <i>C</i>) | 每年第一個時間步依年初蓄水更新（預設 α = 0.85）。 |
| 生態基流下限 | 0.1 · <i>Q&#772;</i><sub>in</sub> | 枯水期維持最低河川基流量。 |
| 最低蓄水保護 | 0.1 · <i>C</i> | 避免水庫過度放空。 |
| 滯洪蓄水上限 | α · <i>C</i> | 超過上限時增加放流，預留防洪滯蓄空間。 |

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

**來源說明。** `flood_control_step` 依循 Hanasaki et al. (2006) / Abeshu et al. (2023) 實作，並與 `RiverAI-Project/MOSART-Urban` 參考公式維持一致（見 `scripts/verify_hanasaki_rule.py` 與 `THIRD_PARTY_NOTICES.md`）。

</div>

### 撰寫自訂 Python 操作規則

在 `extensions:` 註冊自訂 Python 資料夾（指向 `__init__.py`），並提供 `validate_backend`、`build_backend` 與 `network_calls = 0`，即可執行自己的水庫運轉規線：

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

## LLM 操作員 YAML 設定

請將公開欄位（`reservoir_id`、`type`、`model_profile`、`prompt_file`、`customization`）與舊版欄位（`reservoir`、`mode`、`strategy`、`model`、`prompt`）分開使用，切勿在同一個操作員內混寫。

| 欄位 | 用途 |
| --- | --- |
| `reservoir_id` | 指定受控水庫鍵名（須對應水系中的水庫）。 |
| `type` | 設為 `llm` 或 `rule_based`。 |
| `model_profile` | 參照 `models.yaml` 中的模型設定檔（見[模型服務設定](LLM_MODULES.zh-TW.md)）。 |
| `prompt_file` | 每日／每步使用者提示詞範本路徑。 |
| `customization.system_prompt_file` | 常駐系統提示詞（水庫目標、限制與 JSON 格式說明）。 |
| `customization.prompt_variables` / `context` | 靜態參數（`$var`）或附帶於 `$observation` 的固定場址資訊。 |
| `customization.knowledge` / `context_providers` | 靜態操作手冊文字檔（`$knowledge`）或動態規則檢索外掛。 |
| `customization.information` | 綁定不洩漏未來水情之測站與預報（見[水情測站與預報](INFORMATION.zh-TW.md)）。 |
| `customization.history_steps` | 注入 `$completed_history` 的先前已執行步數。 |
| `customization.response_schema` | 自訂結構化 JSON 回覆格式（如先輸出 `release_cfs` 再換算）。 |
| `customization.fallback_models` | 主模型失敗時依序切換的備援模型設定檔清單。 |
| `customization.execution` | 設為 `live`（即時推論）或 `replay`（離線重播）。 |
| `auditors` | 套用於請求放流量的診斷稽核器清單（如 `[release_bounds]`）。 |

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

## 具體提示詞與 JSON 回覆範例

以下三段範例展示如何將系統提示詞、每日使用者提示詞與結構化 JSON 回覆串接起來：

**1. 系統提示詞（`prompts/system.txt`）**

```text
You operate Lake A (capacity 10,000,000 m3, dead storage 1,000,000 m3, outlet 1-50 m3/s).
Maintain seasonal target storage around 6,000,000 m3 while avoiding sudden downstream surges.
Return JSON only: {"schema_version": "reservoir-action.v1", "release_cms": <number>}.
```

**2. 每日使用者提示詞（`prompts/operator.txt`）**

```text
Current reservoir state: $observation
Previous day release and result: $previous_transition
Forecast and gauge information: $information
Operating manual guidance: $knowledge
Decide today's release in m3/s and return JSON only.
```

**3. 結構化 JSON 回覆與單位換算**

- 預設 SI 回覆：`{"schema_version": "reservoir-action.v1", "release_cms": 12.5}`。
- 場址工程單位回覆（如 F.E. Walter 的 `study/response_schemas.json`）：模型輸出 `{"applicable_target_ft": 1300.0, "pool_position": "above_target", "reasoning": "...", "release_cfs": 450.0}`，再由解析函式將 `release_cfs × 0.028316847` 自動換算為 SI 單位 `release_cms` 送入水量平衡引擎。

### 提示詞常用佔位符

| 佔位符 | 每步注入內容 |
| --- | --- |
| `$observation` | 當期 `inflow_cms`（`m³/s`）、期初 `storage_m3`（`m³`）、可行放流上限與靜態情境。 |
| `$previous_transition` | 前一步的請求放流、實際執行放流、溢流與期末蓄水量。 |
| `$completed_history` | 最近 `history_steps` 步的連續已執行紀錄。 |
| `$information` | 不洩漏未來水情之測站觀測、預報與上游水庫狀態。 |
| `$knowledge` | `customization.knowledge` 指定的靜態操作手冊文字。 |
| `$<custom>` | 自訂變數或換算為場址工程單位（`ft`、`cfs`）的內容。 |

**來自 F.E. Walter 案例的設計重點（`examples/fe_walter/study/formatter.py`）**：

- **使用熟悉工程單位**：透過 `elevation_storage.csv` 將 `storage_m3` 轉為 `ft NGVD29` 水位，並將流量轉為 `cfs` 與 `acre-ft`。
- **Without operational knowledge（無操作知識）**（`seasonal_target.yaml`）：僅提供當日水位、季節目標水位（冬季 `1,300` ft／夏季 `1,370` ft）與兩日放流歷史。
- **With operational knowledge（具操作知識）**（`dkp.yaml`）：從 `dkp.md` 注入符合當日水情的操作規則（`R-RELEASE`、`R-MINNORM`、`R-ATSITE`、`R-ZONE`，以及 `R-PLAN` 或 `R-RECREATION`）供模型引用。

## 安全檢查、物理限制與離線重播

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 閘門一：事前檢查與預算控管

- `reservoir-experiment check` 以 `0` 成本預覽第 1 天提示詞。
- 即時 LLM 呼叫須同時具備 `--allow-network`、`"live_readiness": {"ready": true}`（或合成測試案例）與 `max_calls`。

</div>
<div class="panel-card" markdown="1">

### 閘門二：診斷稽核與水量平衡保護

- 稽核器（`release_bounds`、`field_range`）僅記錄 `PASS`/`WARN`/`FAIL`，不會改寫放流量。
- 水庫水量平衡引擎強制限幅 `[minimum_release_cms, maximum_release_cms]`、保護 `dead_storage_m3` 並計算超過 `capacity_m3` 的溢流。

</div>
</div>

離線重播請使用 `examples/fe_walter/study/replay.py` 或 `llm-reservoir-daily`；中斷續跑請使用 `reservoir-experiment resume`，無須重複呼叫已完成的時間步。
