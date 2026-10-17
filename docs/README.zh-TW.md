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

![HydroOpsLLM 核心流程](figures/hydrocnhs-coupling-framework-en.png)

上游連續水文先預算完成。逐日循環再組成決策、驗證回覆、套用物理計算、
將出流送往下游 routing，並提交狀態給下一次決策。
回覆驗證檢查 action 介面；診斷 audit 評估決策；recorder 保存證據，三者職責不同。

先從[安裝](GETTING_STARTED.md)開始，閱讀英文[輸入與輸出](INPUT_OUTPUT.md)，
再[設定 agent（英文）](CONFIGURATION.md)，接著進入英文
[FE Walter 設定教學](../tutorials/fe_walter.md)。
