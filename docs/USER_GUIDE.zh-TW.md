# HydroOpsLLM 設定手冊

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

先閱讀[建立模擬](BUILD_SIMULATION.zh-TW.md)，再透過
[FE Walter 案例](../examples/fe_walter/README.zh-TW.md)查看這些設定的實際用法。
本頁是通用 `configured` 策略的正式手冊。
[LLM 模組](LLM_MODULES.zh-TW.md)解釋決策介面；方法專用設定放在
[FE Walter 範例](../examples/fe_walter/README.zh-TW.md)。

## 1. 準備檔案

| 檔案 | 責任 |
|---|---|
| Experiment YAML | 日期、輸出、agents、models、prompts 與 auditors |
| Case JSON | 水庫、河網、物理、初始狀態與入流／hash |
| 入流 CSV | `date,node,local_inflow_cms`；ISO 日期，daily 局部入流 m³/s |
| Prompt TXT | 獨立 UTF-8 指示模板 |
| Knowledge TXT／MD，選填 | 有 ID 與版本的局部文件 |
| Context JSON，選填 | 固定的補充資料 |
| Information CSV，選填 | 依 profile 選取、附時間戳的觀測或預報 |

將 Excel 匯出成不含 BOM 的 UTF-8 CSV。cfs 乘 `0.028316846592` 轉為 m³/s。
每天須包含全部 routing nodes，包括零流量節點。
已 routing 的總入流不能再次作為局部新增入流加入。
將 CSV SHA256 記入 case，詳見[輸入準備](../tutorials/main.ipynb)。

## 2. 對應 agent 與水庫

每座受控水庫恰好配置一個獨立 agent；被動出口不配置。
`agents` 的項目數就是 agent 數量，沒有 `n_agents` 欄位。
模型 profile 可共用，backend、feedback 與 auditor 狀態則各庫獨立。
下游影響由河網決定。目前 runner 使用 daily，沒有中央聯合規劃 agent。

以下是供**自己的 case 與 prompt**修改的設定形狀，
並非第四種正式方法或可直接執行的資料 bundle：

```yaml
schema_version: llm-reservoir-experiment.v1 # 支援的 YAML 契約。
case: ../my_case/case.json                 # 自己的河網、物理、輸入／hash。
run_id: my-daily-test                    # 每次新實驗更改。
output: ../runs/my-daily-test            # 目錄須尚未存在。
max_calls: 3                              # 三日 × 一個 LLM agent。
models:
  reservoir_model:
    provider: ollama
    model: gemma3:4b                        # 本機已安裝的模型。
    base_url: http://localhost:11434
    temperature: 0.7                       # 明確設定取樣溫度。
    max_tokens: 2048
    timeout_seconds: 120
auditors:                                 # 版本化操作檢查。
  release_limits:
    type: release_bounds
    version: "1"
agents:
  operator_1:                             # 獨立決策單元。
    reservoir: R1                         # case 中受控水庫的精確 key。
    strategy: configured                  # 通用 prompt／knowledge backend。
    mode: llm                             # 渲染 prompt 並請求 proposal。
    model: reservoir_model                # 選用上述 model profile。
    prompt: ../my_case/prompts/controller.txt # 操作指示模板。
    prompt_version: "1"                    # 改指示時更新版本。
    knowledge: {}                         # 選填：ID -> 局部文件路徑。
    context: {}                           # 選填：固定補充資料。
    response_schema: reservoir-action.v1  # 標準正規化 action。
    auditors: [release_limits]            # 此 agent 啟用的檢查。
```

### 設定如何相連

**Experiment → case → 水庫。** Case 提供水量、蓄水與河網。
`agents` 的每個項目對應一座受控水庫及一種決策方法。
Agent 的 `model` 與 `auditors` 連到同份 YAML 中的具名定義。
Prompt 取得本次選用的資訊；它不能改寫 host 的入流、蓄水或物理限制。

#### 實驗與輸出

| 欄位 | 本例中的意義 |
|---|---|
| `schema_version` | 執行器支援的設定格式；保留支援的值。 |
| `case` | Case JSON，包含水庫 ID、物理、初始狀態與入流來源。 |
| `run_id` | 保存於每份紀錄的名稱；新實驗使用新名稱。 |
| `output` | 結果與 trace 的新目錄；既有輸出會被拒絕。 |
| `max_calls` | 整次模擬的模型請求上限，不是每個 agent 的上限。本例為三日 × 一個 LLM agent。 |

#### 模型與操作檢查

| 欄位 | 本例中的意義 |
|---|---|
| `models.reservoir_model` | 自訂 profile 名稱，供 agent 引用；不會建立 agent。 |
| `provider` | Provider 介面；`ollama` 使用指定的 Ollama 服務。 |
| Profile 內的 `model` | 已安裝的模型 ID，本例為 `gemma3:4b`；不自動下載。 |
| `base_url` | 模型服務位址，本例指向本機 Ollama port。 |
| `temperature` | 取樣設定；本設計維持 **0.7**，不保證每次回覆相同。 |
| `max_tokens` | 每次回覆的生成 token 上限；不完整回覆會被拒絕。 |
| `timeout_seconds` | 單次請求允許時間；逾時停止，不自動重試。 |
| `auditors.release_limits` | 具名 audit 定義，只有列出它的 agent 才啟用。 |
| `type: release_bounds` | 比較請求放流與 host observation 中的可行上限。 |
| `version` | Audit 版本，與規格及實作 hash 一起保存。 |

#### Agent、prompt 與資訊

| 欄位 | 本例中的意義 |
|---|---|
| `agents.operator_1` | 此獨立決策單元的自訂 ID。 |
| `reservoir` | Case 中受控水庫的精確 ID，本例為 `R1`。 |
| `strategy: configured` | 通用 prompt 與正規化 action 介面；參考方法有自己的選項。 |
| `mode: llm` | 明確允許執行後，渲染 prompt 並請求模型回覆。 |
| `model: reservoir_model` | 引用上面的模型 profile；不是另一個模型 ID。 |
| `prompt` | 獨立 UTF-8 模板，包含操作指示與支援的 placeholder。 |
| `prompt_version` | 操作指示版本；修改模板時更新。 |
| `knowledge` | 選填的文件 ID 與路徑對應；通用模式加入全文，參考檢索由方法處理。 |
| `context` | 選填的固定資料，與受保護的當期 observation 分開。 |
| `response_schema` | 預期的正規化 action；本例是含 `release_cms` 的 `reservoir-action.v1`。 |
| `auditors: [release_limits]` | 對此 agent 啟用具名 audit；判定不會覆寫決策。 |

下游測站或預報需另行宣告資訊來源與 profile，見[決策資訊](INFORMATION.md)。
本例空白的 `context` 與 `knowledge` 不會自動讀取那些序列。


若使用已安裝的 wheel，且輸入分散在不同 case 資料夾，請將 `case_root` 設為它們共同的資料根目錄。

所有路徑以 YAML 所在目錄為基準。`case_root` 可指定允許的 case bundle 根目錄。
`start_date`／`end_date` 使用引號包住的 ISO 日期，須位於既有連續入流期間。
改起始日不會 warm up 或繼承另一 run：請在新 case 提供已確認的初始蓄水
及 routing 狀態，保留已驗收檔案。

## 3. 決定 LLM 看見什麼

`$observation` 是受保護的 host observation：時間、當期局部入流、
狀態、放流上限與 context。`$information` 是獨立且選用的
`decision-information.v1` 快照，由具名 profile 組成。
固定 context 與選取資訊都不能取代 host 的蓄水、入流或物理。

| Placeholder | 內容 |
|---|---|
| `$agent_id` | JSON 編碼的 agent ID |
| `$observation` | 當期 observation 與分開的 static context |
| `$knowledge` | 選用 package ID 對應完整文件文字 |
| `$previous_transition` | 前一次已提交的 observation／action／physics；第一天 null |
| `$information` | 此 agent 資訊 profile 選取的 aliases |

模板使用 Python `string.Template`；正文美元符號寫成 `$$`。
未知 placeholder 會在檢查時停止。通用 backend 的固定 system message
約束 JSON；`prompt` 中的操作指示形成 user message，沒有通用 YAML
`system_prompt` 欄位。局部 knowledge 以全文加入；通用 YAML 沒有內建
自動檢索或 agent 對話。附時間戳的觀測及預報需宣告
[資訊來源與 profiles](INFORMATION.md)。擴充來源指定已在 Python 註冊的
provider；YAML 不能匯入任意程式。

通用 `mode: offline` 直接回傳 `release_cms`，不渲染或執行 prompt。
參考範例的 offline 模式則渲染保存的 prompt，並解析提供的合成回覆；
兩者是不同測試。

## 4. 為未來實驗設定模型

`mode: llm` 需要 agent 的 `model` 指向 `models` profile；
移除 `release_cms`。模型設定本身不下載或呼叫模型。
目前實驗設計維持 temperature **0.7**。

| Model 欄位 | 意義 |
|---|---|
| `provider` | `ollama` 或 `openai_compatible` |
| `model`、`base_url` | 已可用模型 ID 與最終 HTTP(S) 端點 |
| `temperature` | 取樣溫度；使用 0.7 |
| `max_tokens` | 正整數輸出上限；預設 512 |
| `timeout_seconds` | 正值單次請求 timeout；預設 60 |
| `seed` | 選填整數；支援依 provider 而異，不保證可重現 |
| `api_key_env` | 環境變數名稱，不填 credential 本身 |

`max_calls` 須涵蓋日數 × LLM agents。真實執行另需
`--allow-network` 與 case readiness；閱讀保存結果不需要啟用這些 gate 或呼叫模型。
不支援的設定或 provider 錯誤會停止，不自動重試或 fallback。
啟用 provider 前請依[真實實驗條件](LIVE_READINESS.md)準備。

## 5. 定義 proposal、checker 與 auditor

正規化 proposal 是請求的受控放流量：

```json
{"schema_version":"reservoir-action.v1","release_cms":5.0}
```

Reader 解析回覆；checker 在套用放流前拒絕不支援欄位、錯誤 JSON、
非有限／負值及缺少必要輸出。物理程式另外決定實際放流與 spill。

| 通用 auditor | 設定與意義 |
|---|---|
| `release_bounds` | Version、選填非負 `tolerance_cms`；檢查請求放流與可行上限 |
| `field_range` | Version、點分隔 `path`、有限 `minimum` 及／或 `maximum`、`on_violation: FAIL` 或 `WARN` |

缺欄位／非數字 audit 為 UNKNOWN。所有啟用檢查皆參與：
FAIL > UNKNOWN > WARN > PASS；原 backend audit 保留。
空組合為 UNKNOWN。Audit FAIL 是診斷，不偷偷替換決策。
用[版本化 auditor 插件](auditor_plugins.md)增加 case 規則；YAML 不載入任意 Python。
專用 response schema 與參考檢索屬於各自[範例](../examples/fe_walter/README.zh-TW.md)，
不作為所有水庫的操作規則。

## 6. 檢查、執行與驗證

使用 `check → run → verify`；`check` 不呼叫 provider。執行模型另需
`run --allow-network` 及 ready case。只有給定回覆的無 provider 測試
才使用 `verify --require-offline`。
已有 output 會拒絕；請用新 run ID／output，不覆寫。此 runner 沒有自動續跑。

選用的 `outcome_checks` 在 routing 後執行，寫入 `outcome_audit.jsonl`。
它比較控制點流量與明確的常數或選取資訊門檻，只作診斷；
不會修正放流、最佳化 routing 或保證安全。見[決策資訊](INFORMATION.md#control-point-outcome-checks)。

| 輸出 | 查看什麼 |
|---|---|
| `experiment.json`、`summary.json` | 設定、來源／runtime hashes、狀態與計數 |
| `decisions.jsonl`、`audit.jsonl` | Info／proposal、原 audit 判定與 decision ID 綁定 |
| `physics.jsonl`、`backend_events.jsonl` | 實際結果、已提交 feedback 與失敗 |
| `raw/` | 完整可用 prompt／回覆／audit 及來源參照 |
| `reservoir_trajectory.csv` | 請求／實際放流、spill、蓄水與平衡 |
| `network_flows.csv`、`network_balance.csv` | Routed flow 與水庫／河段水量平衡 |
| `reach_volume_trace.json` | 各河段入流、出流及 channel storage |
| `outcome_audit.jsonl` | 選用的 routing 後控制點診斷 |

依[完整決策流程檢視](../tutorials/main.ipynb)
展示 info、實際 prompt、回覆、proposal、checker、audit、physics 與 feedback。
格式及物理驗收不代表策略品質。缺證據／費用保持未知；合成回覆不是實際模型結果。

[多庫／自己的資料](../tutorials/advanced.ipynb) ·
[原生水文設定](HYDROLOGY_SETUP.md) · [LLM 模組](LLM_MODULES.zh-TW.md)

## 保留的 FE Walter prompt profile

參考案例使用 `strategy: reference_v3_7` 及 `system_prompt_mode: original`。
獨立 TXT 放在 `prompts/fe_walter_reference`；原 builder 渲染日期、狀態及
歷史，並檢索 DKP 片段。Live mode 不允許給定 `responses` 測試回覆。
原 release／schema 使用 cfs，adapter 只轉換一次為 m³/s。這些是 FE Walter
專用選項，不是其他水庫的預設規則。

回覆須完整生成：Ollama 需 `done: true`，若有 `done_reason` 則須為 `stop`；
OpenAI-compatible 需 `finish_reason: stop`。相應的缺值、null 或 non-stop
狀態會被拒絕；JSON 有效仍不足。`raw/` 保存實際 messages、request hash、
回覆、原 audit 及可得的 request ID／usage，排除 credential 值。
見保存的 [Ollama 示範](../examples/fe_walter/README.zh-TW.md)。

## 偵錯

| 看到什麼 | 代表什麼／下一步 |
|---|---|
| 回覆未完整生成或無效 | 套用放流前停止。查看原回覆及完成欄位，修正設定後再用新案例執行。 |
| Schema、單位或放流數值無效 | 回覆檢查拒絕提案。確認 parser 與 action schema 一致。 |
| 水量平衡正常但 audit FAIL／WARN | 指定操作準則指出決策問題。查看 `audit.jsonl`；物理驗收不會覆蓋策略判定。 |
| Audit UNKNOWN | 尚無適用的策略判定。若需策略評估，設定該水庫的 auditor。 |
| Readiness 阻擋 | 依[真實實驗條件](LIVE_READINESS.md)補足證據，不移除 gate 強制執行。 |
| Output 已存在 | 使用新的 `run_id` 及 `output`，保留先前結果。 |
