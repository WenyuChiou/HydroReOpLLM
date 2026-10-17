# 概覽

[English](README.md) | [繁體中文](README.zh-TW.md)

![HydroOpsLLM：建立在 HydroCNHS 上的水庫操作](figures/hydroopslm-cover.png)

HydroOpsLLM 在 HydroCNHS 上加入 LLM 水庫操作功能。使用者保留原有水文模型，
再為每座水庫選擇 **Rule-based** 或 **LLM** 操作。

HydroCNHS 先利用降雨、溫度與潛在蒸發散（PET）計算每日水庫入流。
HydroOpsLLM 保存操作期間的入流；每天由 agent 根據入流及當前水庫狀態提出放流。
水庫計算決定實際放流、溢流及剩餘蓄水，再將出流送往下游 routing。
下一日從更新後的狀態繼續。

目前入口分兩階段：先計算上游入流，再逐日模擬水庫操作及下游 routing。
水庫決策不會改變上游降雨逕流計算。

## 手冊閱讀順序

| 步驟 | 章節 | 要完成的事 |
|---|---|---|
| 1 | [安裝](GETTING_STARTED.md) | 安裝套件並確認命令可用。 |
| 2 | [輸入與設定](INPUT_OUTPUT.md) | 區分全域、水文、水庫與 agent 設定。 |
| 3 | [設定 agent](CONFIGURATION.md) | 選擇規則或 LLM，再設定模型、prompt 及選用知識。 |
| 4 | [FE Walter 教學](../tutorials/fe_walter.md) | 從 `experiment.yaml` 逐步接到每日操作。 |
| 5 | [結果](RESULTS_GUIDE.md) | 查看水位及控制放流。 |
| 6 | [問題排查](TROUBLESHOOTING.md) | 找出輸入、模型回覆或中斷問題。 |
| 7 | [API 文件](API_REFERENCE.md) | 查詢設定對應的函數。 |

詳細章節以英文維護。集水區建置、參數估計與校正請依
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。

## 核心流程

![HydroOpsLLM 核心流程](figures/hydrocnhs-coupling-framework-en.png)

*圖 1。HydroCNHS 提供上游水文與 routing。Agent 提出控制放流，水庫物理計算實作放流並更新蓄水。
回覆驗證檢查模型回覆；audit 評估已設定的操作條件；recorder 保存決策與物理結果。*
