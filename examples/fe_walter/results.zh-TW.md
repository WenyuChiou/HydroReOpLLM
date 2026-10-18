# FE Walter：水位與控制放流

[English](results.md) | [繁體中文](results.zh-TW.md)

比較同一 FE Walter 案例的三種方法：**Rule-based**、**LLM with available information**、
**LLM with retrieved knowledge**。期間為 2016-01-01 至 2016-12-31，共 366 天。
下圖使用舊 prompt 產生的框架結果，尚未加入新的當日季節資訊，沒有新增模型請求。
[10 月原文對照](prompt_review.md)把歷史請求與擬修改提示分開展示。

## 水庫操作

Rule-based 使用 Hanasaki 規則，決策公式沒有讀取冬夏目標水位。
2016 年累積放流為 3.28717 億 m³，兩個 LLM 情境分別為 3.80617 與 3.80684 億 m³；
少放的水留在水庫中，因此水位較高。詳見[水量診斷](engine_comparison.md#reading-the-rule-based-trajectory)。

檢索知識情境在 10 月 12–14 日的回覆中，提前套用 10 月 15–31 日的退水窗口。
持續放流使水位在 **10 月 15 日降至 1287.8 ft**。這是已保存的決策行為；
季節 audit 會記錄問題，不會改寫放流。詳見[決策證據](engine_comparison.md#reading-the-retrieved-knowledge-trajectory)。

水位是當日日末的狀態，放水量則是當日的操作值。蓄水量也受入流與溢流影響，
見[水量平衡](README.zh-TW.md#水庫實驗)。冬季檢查範圍為 11 月 1 日至
3 月 14 日的 1297–1303 ft；夏季上限適用於 5 月 10 日至 10 月 14 日。
這些研究準則不會改寫放流決策。

季節虛線在 3 月底前維持 1300 ft，從 4 月 1 日開始上升。
春、秋過渡期斜率只是示意，不會重訂研究的季節 audit 窗口，也不指定每日放流。

[完整精度每日資料](coupled/outputs/current_tutorial/daily.csv) ·
[來源紀錄](coupled/outputs/current_tutorial/provenance.json) ·
[合併圖 SVG](coupled/outputs/current_tutorial/reservoir_operations.svg) ·
[合併圖 PDF](coupled/outputs/current_tutorial/reservoir_operations.pdf)

次要的單圖下載：[水位 PDF](coupled/outputs/current_tutorial/daily_water_elevation.pdf) ·
[放流 PDF](coupled/outputs/current_tutorial/controlled_release_daily.pdf)

資料由已保存的 Rule-based 年度結果及兩個最新框架 LLM 結果整理而成。
每種方法都有 366 個依序排列且不重複的日期；整理前已核對共同入流
（CSV 序列化容差 1e-10 m³/s）、初始蓄水 2,457,848.279729185 m³ 與單位，沒有插值或新增模擬。
模型參數保存在 [models.yaml](coupled/models.yaml)。水位目標未達屬於操作結果，
不等於模型請求或水量計算失敗。這些軌跡用於比較本次保存的方法結果，不能推論一般性的優劣排名；
完成執行與水量守恆也不代表操作已達標。

較早五年研究與原始紀錄保存在[歷史參考](results_history.zh-TW.md)。

![2016 年水位與控制放流](coupled/outputs/current_tutorial/reservoir_operations.png)

*圖 1。2016 年保存的操作結果。(a) 日末水位（ft NGVD29），搭配從 4 月開始上升的
季節示意線：冬季目標 1300 ft、夏季上限 1370 ft。(b–d) 實際放水量（m³/s），
不含溢流。各圖共用操作日期；三張放流圖使用相同刻度。*
