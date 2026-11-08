# F.E. Walter 延伸至 Bethlehem：下游水位資料準備

[English](README.md) | [繁體中文](README.zh-TW.md)

這是獨立的**資料準備範例**，尚不是能執行或已完成 C&V 的 Bethlehem 模型。
原有 [F.E. Walter 範例](https://wenyuchiou.github.io/HydroReOpLLM/docs/CASE_STUDIES.html)保留。
本案例只控制 FE Walter，Beltzville 壩下溪流觀測作所有情境共用的外部邊界。
未來比較 Rule-based MOSART-Urban、LLM without operational knowledge 及
LLM with operational knowledge，使用相同物理 profile 與 forcing。

## 從哪裡開始

| 檔案 | 用途 |
|---|---|
| [preparation.json](preparation.json) | 研究範圍、測站／節點、邊界所有權與未解項目；不是 experiment CLI 的設定檔。 |
| [ratings_inventory.csv](ratings_inventory.csv) | 三站目前 rating ID、生效時間原始欄位、來源雜湊及歷史缺口。 |
| [data_requirements.csv](data_requirements.csv) | 需補資料、取得來源及使用它的 C&V 階段。 |
| [usgs_data_request.md](usgs_data_request.md) | 尚未寄出的 USGS 資料需求稿。 |

先取得缺少的紀錄，再依下列順序建置。這裡尚無 `reservoir-experiment run` 指令；
新增產流、河網與模擬水位 provider 都還需要建立。下載資料及輸出放在自己的研究目錄，
保存來源、時間、原始 bytes、雜湊和品質碼。

## 已確認的 rating 狀態

2026-11-08 UTC 已從 USGS STAC 下載三站的 base 及目前 shifted/exsa 表，共六份。

| 測站 | 目前 rating | base 檔頭的生效時間原值 | 五年歷史是否齊全？ |
|---|---|---|---|
| Lehighton 01449000 | 12.0 | `20250506231500`；`BZONE=-05:00` | 否；缺前版及完整 shifts。 |
| Walnutport 01451000 | 26.0 | `20250507171500`；`BZONE=-05:00` | 否；缺前版及完整 shifts。 |
| Bethlehem 01453000 | 43.0 | `20260317150700`；`BZONE=-05:00` | 否；此版在研究期之後生效。 |

檔案來源為 [USGS STAC 服務](https://api.waterdata.usgs.gov/docs/stac/)，各表 URL 及雜湊
列在 inventory；成功下載不代表歷史適用性已確認。

時間欄位先保存原值，需確認 clock 語義才轉成 UTC。下載時間或 STAC item 時間不等於
rating 生效時間；檔頭的 provisional/working 也不代表歷史已核准。
[USGS 指引](https://www.usgs.gov/centers/pennsylvania-water-science-center/science/surface-water-monitoring-pennsylvania)
明確提醒目前 rating 不一定適用歷史資料。仍需各版曲線、生效起訖、完整 shift／correction
及修訂紀錄；field measurements 不能代替這些紀錄。

### 當地水位與絕對高程

操作門檻對照 00065 gage height；63160 等絕對水面高程另列。
[USGS datum 通知](https://www.usgs.gov/centers/pennsylvania-water-science-center/updating-pennsylvania-streamgage-datums)
說明此次 NGVD29→NAVD88 轉換不改變當地 stage 或 discharge，因此不能把高程差直接加減到
9／7／12 ft 門檻。公告列出 Walnutport 於 2022 年 10 月、Bethlehem 於 2023 年 8 月，
Lehighton 於 2022／2023 的兩個更新日期，仍需保留高程轉換及其他歷史 local-zero／移站資料。
三個 action stages 本身也不等於完整 A/B/C/D 規則。

### Bethlehem 的口徑

[USGS 2000 水文年站點說明](https://pubs.usgs.gov/wdr/2000/dela-00/wdr_del-2000/pdfs/01453000.pdf)
指出實體水位站在 Monocacy 匯入口上游約 1,800 ft，而公布流量與 1,279 mi² 面積包含 Monocacy。
這證實歷史說明有此差別；**2021–2025 的實際計算及幾何仍待確認**。

先分開 `bethlehem_stage_gage` 與 `bethlehem_published_discharge` 兩種比較定義。
需確認 rating 對應哪種 Q、Monocacy 的調整與時間對齊，才決定轉換方式；不能直接把
Monocacy 流量減掉就當作已解決，也不能把支流路由到實際匯入口上游。
這些是待建立的比較口徑，不是已完成的水力連線。

## Beltzville 共用邊界

採 01449800 的 00060 溪流觀測，先查數值完整性與品質。它不是獨立的閘門放水量測，
[USGS 說明](https://pubs.usgs.gov/wdr/2001/del-01-1/pdfs/01449800.pdf)也記錄了上游其他水庫與引水影響。
該站以上已含面積不再由 GWLF 重複產流，只增加站下至主流的地方來水與 routing。
必要的 01449790 池水位另列資訊資料，Beltzville 不因此成為可控水庫。

所有策略用同一外部邊界，但 hindcast 的當日均量不能提前當作決策前已知資訊。
提供給 LLM 的內容仍依完成時間及實際可取得時間處理。

## C&V 安排

1. 取得歷史 rating／shift／datum，確認 Bethlehem Q/H 口徑、互斥流域、測站與支流口位置。
2. 補齊 Q、H、Beltzville 邊界、氣象／PET、土地土壤及河段資料，依共同覆蓋固定 C/V 年份。
3. 舊上游先保留參數做回歸；新區域產流及 Lehighton→Walnutport→Bethlehem routing 重新 C&V。
   用分段觀測邊界隔離誤差，檢查總量、KGE、RMSE、洪峰、峰時與退水；尋優前固定接受標準。
4. 三站（包含 Lehighton）都要驗 Q→H：偏差／RMSE、越線時間、持續時間、誤報及漏報。
   rating 不足時再評估斷面、水力／回水與漲退水效應。USGS Q 常由 H/rating 推算，兩者不是
   兩套獨立真值。最後驗完整自由運行鏈、放水脈衝、routing 尾段和水量守恆。
5. 各策略以自己的 actual controlled release + spill 形成自己的 Q/H；前一步完成的水位與
   history 才進入下一步決策。觀測主流水位只用於 C&V；缺值不能推定未超標。
   接好資訊 provider、檢視 prompt diff 及 auditor 後，才開始新的 LLM 比較。

Daily 流量 C/V 暫以舊 1990–2010／2011–2020（暖機 1989）作待查資料的候選。
三站 subdaily H 目錄自 2007 年 10 月起，**水位 C/V 年份尚未指定**，需等 H、rating 與
邊界共同覆蓋確認；不必硬套完整流量 C/V 期間。已看過的 2021–2025 仍是 retrospective 比較。

Daily 均量不等於瞬時洪峰水位；完整洪水 A/B/C/D 時序主張需要相容的 subdaily 模擬與決策。
共用 MOSART-Urban baseline 維持原式；若安全控制器改寫實際放水，另標為 constrained variant。
詳見[英文完整說明](README.md)。
