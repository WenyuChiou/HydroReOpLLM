# HydroOpsLLM 使用指南

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

HydroOpsLLM 將已確認的 HydroCNHS 模型接到規則式或 LLM 水庫操作。
水量計算、物理限制、routing、audit 與證據紀錄都由 HydroOpsLLM 管理。

## 依同一條首次執行路徑操作

1. **安裝。** 依[建立模擬：安裝](BUILD_SIMULATION.md#1-install-the-project)完成安裝。
2. **確認輸入與輸出。** 閱讀[輸入與輸出](INPUT_OUTPUT.md)。流域建置、參數推導與
   校正／驗證沿用 [HydroCNHS 官方手冊](https://cylin928.github.io/HydroCNHS/)。
3. **建置並連接。** 依[建立模擬](BUILD_SIMULATION.md)使用四天的獨立河川 fixture，
   檢查氣象、水文、水庫 ID、連線與輸出；此 fixture 不代表通過科學驗證。
4. **設定 agent。** 先使用規則設定，再依[設定](CONFIGURATION.md)將一座水庫改成
   最小 LLM agent：`reservoir_id`、`type`、`model_profile`、`prompt_file`。
5. **設定模型與 prompt。** 在[模型 provider](MODEL_PROVIDERS.md)選擇 `local` 或其他
   明確 profile。HydroOpsLLM 不會自動加入共用 system prompt。
6. **執行與驗證。** 依[執行與復原](RUNNING.md#run-the-generic-coupled-fixture)
   完整執行 `check → prepare → run → verify`。
7. **閱讀結果。** 先讀 `summary.json`，再依[結果、audit 與 trace](RESULTS_GUIDE.md)檢查。

完成通用路徑後，再讀 [F.E. Walter 案例背景](../examples/fe_walter/README.zh-TW.md)
與英文[實際設定教學](../tutorials/fe_walter.md)，或
[雙水庫教學](MULTI_RESERVOIR.md)。

## 了解執行邊界

準備階段在完整連續期間（包含暖機期）執行 GWLF 或 ABCD 降雨逕流與 Lohmann
routing，再選出操作日期的入流邊界。逐日操作推進水庫決策、蓄水與下游 routing。
水庫決策不會改變預先計算的氣象到逕流結果。

每座受控水庫有一個 agent。Agent 提出控制放流需求；物理核心依可用水量與放流限制
計算實施放流、溢流與期末蓄水，再將實施控制放流加溢流送往下游。

## 選擇決策方法

| 目的 | Agent 設定 | Provider 請求 |
|---|---|---|
| 使用操作規則或控制器 | `type: rule_based`、`rule`、`rule_parameters` | 無 |
| 執行 fixture 的歷史入流範例 | `type: rule_based`、`rule: hanasaki` | 無 |
| 使用自己的 prompt 與模型 | `type: llm`、`model_profile`、`prompt_file` | 只有 `--allow-network` 才允許 |
| 保留特定科學案例方法 | `type: llm` 加 `customization.backend` | 依 extension 而定 |

先用規則 agent 確認物理連線。Hanasaki 是一個已註冊的範例，不是框架預設。
Baseline 是比較用執行，不是演算法。Offline 表示沒有即時 provider 請求；fixture 與
replay 可使用保存回覆，不會形成第三種 agent 類型。

F.E. Walter extension 保留該案例原有的 Anik 訊息格式；它不會替其他水庫定義共用
prompt 或 Anik 預設值。

## 使用 v2 與明確研究輸入

新實驗使用 `hydroops-coupled-simulation.v2`。Experiment 保存共用日期、輸出、水文、
物理拓撲與 catalogs；各 agent 選擇水庫、方法、模型 profile、prompt、資訊 profile 與
auditors。資訊控制 operator 能看見什麼；物理 connections 才會搬移水量。

`hydrology`、`models`、`agents`、`auditors`、`information` 可直接寫入，或使用
完全獨立的 `{file: path}`。路徑以宣告它的檔案為基準，section 檔不做深層合併。
舊版 inline v1 設定仍受支援。

Catalog 是共用的具名項目集合，例如所有模型 profiles；profile 是 agent 選取的單一
具名項目。Source pin 用輸入原始 bytes 或 hash 固定研究來源。Committed history 是已
保存完成日期的決策、物理 transition 與證據序列。

## 需要時再加入進階 context 與復原

最小 LLM agent 為：

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
```

研究需要時，才在 `customization` 加入 `system_prompt_file`、`prompt_variables`、
knowledge、選定的[決策資訊](INFORMATION.md)、`context_providers`、重試與
`fallback_models`。Fallback 是依序排列的模型 profile ID；audit、物理 transition 或
證據寫入失敗時不會啟用 fallback。

`verify` 核對保存的連結、hash 與水量平衡，不代表操作政策有效。水文校正／驗證、
回覆驗證、操作 audit 與物理驗證應保留為不同證據。

Resume 會在新目錄重建中斷執行，略過 committed decisions，並可重用保存回覆。
Crash 時仍在傳送中的外部請求可能再次送出，因此不能保證 provider exactly-once。
詳見[執行與復原](RUNNING.md#resume-an-interrupted-run)。

## 排除問題

| 現象 | 下一步 |
|---|---|
| 資訊缺漏或過期 | 核對選定 profile、可取得時間與 required 旗標。 |
| Provider 驗證錯誤 | 設定指定的 `api_key_env`；不要把憑證寫入 YAML。 |
| 回覆格式錯誤或截斷 | 再次執行前先查看 provider ledger 與原始回覆。 |
| Audit FAIL 但水量平衡正常 | 檢查操作準則；物理成功不會清除 audit 結果。 |
| 輸出目錄已存在 | 設定新的 `run_id` 與 output，或在新目錄 resume 中斷執行。 |

修改欄位時使用[參數說明](PARAMETER_REFERENCE.md)，即時研究前閱讀
[Live readiness](LIVE_READINESS.md)。
