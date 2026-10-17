# HydroOpsLLM 使用指南

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

HydroOpsLLM 將已確認的 HydroCNHS 水文結果接到規則式或大型語言模型水庫決策。
水量計算、物理限制、routing 與紀錄都由框架處理。

## 依這個順序閱讀手冊

1. 先讀[概覽](README.md)，了解兩階段模擬。
2. 依[建立模擬](BUILD_SIMULATION.md#1-install-the-project)安裝專案。
3. 先確認 [HydroCNHS 設定與校正／驗證](HYDROLOGY_SETUP.md)。
4. 在[建立模擬](BUILD_SIMULATION.md#3-bind-hydrology-to-the-reservoir-network)設定水庫與 routing 節點對應。
5. 在[設定檔](CONFIGURATION.md)選擇 agent 與 prompt。
6. 研究需要 LLM 時，再選擇[模型 provider](MODEL_PROVIDERS.md)。
7. 明確設定[決策資訊](INFORMATION.md)或自訂 context。
8. 執行 `check → prepare → run → verify`，再查看結果或續跑。

[雙水庫教學](MULTI_RESERVOIR.md)提供完整分檔設定與可下載範例。

## 了解模擬邊界

準備階段先連續執行 GWLF 或 ABCD 降雨逕流與 Lohmann routing，包含暖機期，
再取出操作期間的入流邊界。逐日操作階段推進水庫決策、蓄水與下游 routing。
水庫決策不會改變預先計算的氣象水文模擬。

每座受控水庫由一個 agent 提出控制放流需求。物理核心依放流限制與可用水量計算
實施放流、溢流與期末蓄水，再將實施放流加溢流送往下游。

## 選擇適合的決策方法

| 目的 | Agent 設定 | Provider 請求 |
|---|---|---|
| 使用明確的操作規則或控制器 | `type: rule_based`、`rule: <registered ID>`、`rule_parameters` | 無 |
| 與範例的歷史入流規則比較 | `type: rule_based`、`rule: hanasaki` | 無 |
| 使用自己的 prompt 與模型 | `type: llm`、`model_profile`、`prompt_file` | 明確指定 `--allow-network` |
| 保留特定科學案例的方法 | `type: llm` 加上 `customization.backend` | 依 extension 設計 |

先執行規則 agent。Hanasaki 是範例實作，不是框架固定選項。
可註冊自己的模組來實作操作曲線、供水或水力發電控制器，並提供各自的演算法與測試。
Baseline 指用來比較的執行，不是演算法名稱。Offline 表示不發出真實 provider 請求；
LLM 測試與重播可使用給定或保存的回覆，不是第三種 agent 類型。
水文、河網、初始蓄水、prompt 與 audit 準則確認後，
再使用 LLM agent。F.E. Walter 教學透過案例 extension 保留
Anik 原生訊息格式；保存的 2016 年診斷結果不是新的 Anik 重現結果。

## 使用 v2 分檔設定

新實驗使用 `hydroops-coupled-simulation.v2`。`hydrology`、`models`、
`agents`、`auditors` 與 `information` 可直接寫入，或使用
`{file: path}` 引用。`extensions` 明確註冊來源檔。
每個路徑以宣告它的檔案位置解析，載入器不做深層合併。

舊版 v1 inline 設定仍受支援。[設定檔](CONFIGURATION.md)說明完整結構與路徑規則。

全域 experiment 設定共用日期、輸出、水文、物理河網與各類 catalog。
每個 agent 用 `reservoir_id` 選擇一座水庫，分別設定方法、模型、prompt、資訊 profile
與 auditor。資訊來源決定可見內容；只有物理河網的 connections 會搬移水量。

## 將 prompt 與資訊視為研究輸入

通用 LLM agent 指定 user 指令，並可另加 system 模板：

```yaml
reservoir_id: lake_a
type: llm
model_profile: local
prompt_file: prompts/operator.txt
customization:
  system_prompt_file: prompts/system.txt
```

核心不會自動加入共用 system 指令。`customization` 內固定的 `prompt_variables`、
選定的 `information` 與動態 `context_providers` 成為具名模板變數。
自訂 callback 只取得不可變的決策輸入，並回傳值與來源紀錄，不能改動物理狀態。

## 明確設定 provider 行為

支援 OpenAI Responses、Anthropic Messages、Gemini `generateContent`、
Ollama Chat 與 OpenAI-compatible Chat Completions。
明確指定模型 ID 與憑證環境變數名稱；只傳送有設定的取樣與 token 參數。

每個 profile 的重試次數有上限。選用的 `customization.fallback_models` 依序列出 profile ID，
預設為空。Trace 記錄實際使用的模型與 attempt。
驗證身分或設定錯誤會停止；audit FAIL 與物理錯誤不會要求模型重答。

## 分清楚完成與品質

`verify` 核對保存的連結、hash 與水量平衡，不代表操作策略有效。
水文校正／驗證、決策 audit 與物理驗證是三種不同證據。

Trace 保存 provider 請求／回覆、決策、物理結果與 audit。
紀錄寫入失敗即停止。續跑略過已提交決策，並可重用已保存回覆；
外部服務在所有 crash 邊界都只收到一次請求，並不是可保證的行為。

## 檢查、執行與驗證

使用同一份實驗設定執行 `check`、`prepare` 與 `run`，再驗證 operation 目錄。
完整指令與意義見[建立模擬](BUILD_SIMULATION.md#5-check-without-running-anything)。

## 排除問題

| 現象 | 下一步 |
|---|---|
| 資訊缺漏或過期 | 核對 profile、可取得時間與 required 旗標。 |
| Provider 身分驗證錯誤 | 設定指定的 `api_key_env`，不要把金鑰放進 YAML。 |
| 回覆格式錯誤或截斷 | 開始新執行前，先查看 provider ledger 與原始回覆。 |
| Audit FAIL 但水量平衡正常 | 核對操作準則；物理通過不會清除 audit 結果。 |
| 輸出目錄已存在 | 選擇新的 `run_id` 與輸出，或對中斷執行使用 `resume`。 |

使用[結果、audit 與 trace](RESULTS_GUIDE.md)了解輸出；
修改設定時查閱[參數說明](PARAMETER_REFERENCE.md)。
