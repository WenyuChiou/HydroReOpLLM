# 概覽

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM 將水庫決策接入 HydroCNHS 水文模擬。
準備階段先計算完整期間的氣象驅動水文，再選取水庫入流邊界。
逐日操作時，LLM 根據可用資訊提出放流建議。

共同水庫計算決定實際放流、溢流與蓄水，再將出流送往下游。
更新後的條件提供給下一次決策，形成持續循環。
目前案例採每日時間步；規則式 agent 也可使用相同水庫計算進行比較。
每座水庫選擇 `type: rule_based` 與已註冊規則，或 `type: llm` 與模型 profile、
明確的 prompt。水庫決策不會改變預先計算的氣象逕流。

## 手冊閱讀順序

| 步驟 | 章節 | 要完成的事 |
|---|---|---|
| 1 | [安裝](GETTING_STARTED.md) | 安裝 package，確認命令列入口可用。 |
| 2 | [輸入與輸出](INPUT_OUTPUT.md) | 區分全域、水文、水庫／耦合及 agent 設定，確認資料單位。 |
| 3 | [建立模擬](BUILD_SIMULATION.zh-TW.md)、[設定 agent](CONFIGURATION.md)及[模型服務](MODEL_PROVIDERS.md) | 先學通用設定與 Rule-based 到 LLM 的切換，再設定模型、prompt 與選用知識。 |
| 4 | [F.E. Walter 案例](../examples/fe_walter/README.zh-TW.md)與[實作教學](../tutorials/fe_walter.md) | 將地圖、操作目的及資料接到實際 YAML、prompt 設計與每日決策。 |
| 5 | [結果](RESULTS_GUIDE.md)與[恢復執行](RUNNING.md) | 查看最新全年結果、檢查紀錄及接續中斷的模擬。 |
| 6 | [Python API](API_REFERENCE.md)與[程式架構](CODE_STRUCTURE.md) | 查詢函數介面、擴充方式及對應的實作模組。 |

以上詳細章節以英文維護。集水區建置與校正請依
[HydroCNHS 前置設定](HYDROLOGY_SETUP.md)中的官方教學連結。

## 核心流程

![HydroOpsLLM 核心流程](figures/hydrocnhs-coupling-framework-en.png)

上游連續水文先預算完成。逐日循環再組成決策、驗證回覆、套用物理計算、
將出流送往下游 routing，並提交狀態給下一次決策。
回覆驗證檢查 action 介面；診斷 audit 評估決策；recorder 保存證據，三者職責不同。
