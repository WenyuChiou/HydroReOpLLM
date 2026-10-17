# 使用指南

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

先準備已接受的 HydroCNHS 水文模型，再加入水庫與河網設定，最後為每座受控水庫選擇操作 agent。

## 檢查、執行與驗證

1. [安裝](GETTING_STARTED.md)套件。
2. [區分設定](INPUT_OUTPUT.md)：全域、水文、水庫與 agent。
3. [連接模擬](BUILD_SIMULATION.zh-TW.md)：將水文出口對應到水庫入流節點。
4. [設定 agent](CONFIGURATION.md)：選擇 Rule-based 或 LLM。
5. 依 [FE Walter 教學](../tutorials/fe_walter.md)，從實際 `experiment.yaml` 逐檔閱讀。
6. [執行並驗證](RUNNING.md)，再[查看結果](RESULTS_GUIDE.md)。

Offline 表示不發送真實模型請求。Baseline 是比較用的模擬，例如 Rule-based；它不是第三種 agent。
閱讀教學與已保存結果不需要啟動模型。

## 了解執行順序

HydroCNHS 先計算包含暖機期的連續上游入流。HydroOpsLLM 選出操作期間，
再逐日執行決策、水庫物理計算與下游 routing。更換操作方法不會改變預先計算的上游水文。

Agent 提出控制放流；水庫計算依可用水量及放流限制決定實際放流、溢流與剩餘蓄水。
下一日使用更新後的狀態。

## 選擇決策方法

| 方法 | 設定 | 決策來源 |
|---|---|---|
| Rule-based | `type: rule_based`、`rule`、`rule_parameters` | 使用者註冊的規則模組；Hanasaki 只是範例。 |
| LLM | `type: llm`、`model_profile`、`prompt_file` | 模型讀取使用者定義的 prompt。 |

LLM 擴充模組可自行建立訊息格式，不必使用 `prompt_file`。FE Walter 使用此方式保留
Anik 的訊息格式；案例邏輯保存在 examples，不是通用預設。

## 設定與選用功能

`experiment.yaml` 定義期間、輸出位置及其他設定檔的引用。Profile 是一組具名設定，
例如某個 provider 與模型參數。多個 agent 可共用 profile，但各水庫的狀態與歷史分開保存。
新實驗建議使用 `hydroops-coupled-simulation.v2`。相對路徑以寫下該路徑的檔案位置為起點。

## 稍後加入選用資訊與續跑

先完成必要設定，再依研究需要加入 system prompt、固定變數、帶時間的資訊或檢索 callback。
框架不會自動加入共用 system prompt。

## 問題排查

[問題排查](TROUBLESHOOTING.md)集中說明輸入錯誤、無效回覆、操作目標未達與中斷問題。
[執行與續跑](RUNNING.md)說明如何保留原始紀錄並從新目錄繼續；
[API 文件](API_REFERENCE.md)與[設定參考](PARAMETER_REFERENCE.md)提供完整介面。
