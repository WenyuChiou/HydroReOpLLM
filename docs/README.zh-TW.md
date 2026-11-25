# HydroReOpLLM 使用手冊

使用既有入流資料建立水庫實驗、檢視物理水量平衡，並選擇指定放流量或 LLM 操作員。建議先從通用離線範本開始，再比較兩份 F.E. Walter LLM 設定。

[安裝並執行範本](GETTING_STARTED.zh-TW.md) · [F.E. Walter 教學](../tutorials/README.zh-TW.md) · [English manual](README.md)

## 公開起點

| 起點 | 示範內容 |
| --- | --- |
| [通用既有入流範本](../examples/template/README.zh-TW.md) | 以指定放流量操作的合成雙庫案例，不發出模型請求。 |
| [F.E. Walter 季節目標](../examples/fe_walter/README.zh-TW.md) | 七天的既有入流 LLM 案例，使用具名季節目標系統提示詞。 |
| [F.E. Walter DKP](../examples/fe_walter/README.zh-TW.md) | 相同的教學用物理案例，搭配具名系統提示詞與決策知識包。 |

三個入口的 `check` 皆為離線操作。F.E. Walter 案例僅在使用者明確啟動本機 Ollama 並執行 `run --allow-network` 時才會呼叫模型。儲存庫不含論文軌跡、論文結果、歷史實驗提示詞副本、模型權重或模型生成回覆。

## 設定、執行與檢視

| 指南 | 用途 |
| --- | --- |
| [設定說明](CONFIGURATION.zh-TW.md) | 解析檔案、操作員類型、單位與演算設定。 |
| [決策時資訊](INFORMATION.zh-TW.md) | 加入符合因果時序的靜態、觀測、預報或模擬資訊。 |
| [模型服務](LLM_MODULES.zh-TW.md) | 記錄模型服務識別與可重現性中繼資料。 |
| [執行生命週期](RUNNING.zh-TW.md) | 控制網路權限、嘗試次數、續跑與驗證。 |
| [結果解讀](RESULTS_GUIDE.zh-TW.md) | 讀取決策、軌跡、水量平衡與來源追蹤資訊。 |
| [疑難排解](TROUBLESHOOTING.zh-TW.md) | 診斷設定驗證、執行期與結果驗證錯誤。 |
