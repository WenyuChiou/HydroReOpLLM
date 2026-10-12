# 設定手冊

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

先依[教學](../tutorials/README.zh-TW.md)完成示範，再複製三種方法的有註解 YAML。

| 要設定的內容 | 欄位／位置 |
|---|---|
| 日期、run ID、新輸出目錄、請求上限 | YAML 頂層；離線 `max_calls: 0` |
| Agent 數量與對應水庫 | 每個受控水庫一個 `agents` 項目；被動出口不填 |
| Rule benchmark | `strategy: benchmark`；`benchmark.purpose`、`alpha`、固定 `statistics` |
| 原版 zero-shot／DKP | `strategy: reference_v3_7`；`reference.method` |
| 公開資料與水位／蓄水曲線 | `reference.profile`；自訂 ID 必須有 `profile_file` |
| 真正的 system 文字 | `reference.system_prompt`；`system_prompt_mode: original` 核對原版 bytes |
| 刻意修改 prompt | `system_prompt_mode: custom`；版本與 hash 記錄變更 |
| 原版條件式 DKP 檢索 | `reference.dkp`；FE 專用 builder 與原生 auditor |
| 離線回覆 | `reference.responses`；保留合成 fixture 標籤 |
| 真實 provider／model | `models` profile；`mode: llm`、`model`、temperature **0.7**、token／timeout／call cap |
| 額外檢查 | `auditors` 定義與各 agent 的 checker IDs；原版 audit 仍保留 |
| 位置、拓樸、庫容、初始蓄水、入流／hash | Case JSON；不同區域需自己的已驗證數值 |

路徑以 YAML 所在目錄為基準。改日期不會 warm up 或沿用另一 run 的狀態；不同起始日
需新 case 提供正確初始蓄水與 routing 狀態。內建 profile 從固定 runtime 取得；
自訂 profile 缺資料或數值不合法會拒絕。

Daily 變數有日期、timestep、m³/s 與 cfs 入流、蓄水、水位與本庫歷史。Trace 顯示
變數，但不改 FE Walter 原版文字／數值格式。次日歷史保留 requested release 與實際
total outflow（controlled + spill）。

原版 V3.7 DKP builder／auditor 含 FE Walter 規則；其他水庫使用通用 `configured`
backend 與自己的 prompt／knowledge／auditor，不能改名套用 FE 規則。
[進階 configured 設定](../archive/CONFIGURED_BACKEND_GUIDE.zh-TW.md)列出完整選項與
`$observation`、`$knowledge`、`$agent_id`、`$previous_transition` 變數。
通用教學 template 位於 `tests/fixtures/prompts/`，是測試 fixture，並非第四種正式案例。

模型提議放流、物理程式執行限制。Audit FAIL 是診斷，不會偷偷替換決策；無效或
不完整回覆在套用放流前停止。`verify --require-offline` 獨立檢查保存的證據。
[Auditor 擴充](auditor_plugins.md) · [真實實驗前條件](LIVE_READINESS.md)
