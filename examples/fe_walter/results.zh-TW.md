# FE Walter：水位與控制放流

[English](results.md) | [繁體中文](results.zh-TW.md)

比較同一 FE Walter 案例的三種方法：**Rule-based**、**LLM with available information**、
**LLM with retrieved knowledge**。期間為 2016-01-01 至 2016-12-31，共 366 天。
下圖使用已保存的框架模擬結果，沒有新增模型請求。

## 水庫操作

![2016 年水位與控制放流](coupled/outputs/current_tutorial/reservoir_operations.png)

*圖 1。**Rule-based**、**LLM with available information** 與
**LLM with retrieved knowledge** 的 2016 年保存操作結果。(A) 日末水位，
單位為 ft NGVD29；1300 與 1370 ft 虛線協助閱讀本研究定義的季節水位範圍。
(B) 每日控制放流，單位為 m³/s；分組柱狀圖不包含 spill。兩個面板共用日期軸。*

[完整精度每日資料](coupled/outputs/current_tutorial/daily.csv) ·
[來源紀錄](coupled/outputs/current_tutorial/provenance.json) ·
[合併圖 SVG](coupled/outputs/current_tutorial/reservoir_operations.svg) ·
[合併圖 PDF](coupled/outputs/current_tutorial/reservoir_operations.pdf)

次要的單圖下載：[水位 PDF](coupled/outputs/current_tutorial/daily_water_elevation.pdf) ·
[放流 PDF](coupled/outputs/current_tutorial/controlled_release_daily.pdf)

資料由已保存的 Rule-based 年度結果及兩個最新框架 LLM 結果整理而成。
每種方法都有 366 個依序排列且不重複的日期；整理前已核對共同入流
（CSV 序列化容差 1e-10 m³/s）、初始蓄水 2,457,848.279729185 m³ 與單位，沒有插值或新增模擬。
模型參數保存在 [models.yaml](coupled/current/models.yaml)。水位目標未達屬於操作結果，
不等於模型請求或水量計算失敗。這些軌跡用於比較本次保存的方法結果，不能推論一般性的優劣排名；
完成執行與水量守恆也不代表操作已達標。

下一步：[逐檔教學](../../tutorials/fe_walter.md) · [結果 notebook](../../tutorials/main.ipynb)。
較早五年研究與原始紀錄保存在[歷史參考](results_history.zh-TW.md)。
