# HydroOpsLLM 使用手冊

**Hydrological Simulation with Large Language Model Reservoir Operations**

在耦合水文模擬中設定水庫操作。先了解輸入、設定 agent，再以一個 FE Walter 案例學習三種操作方法。

![HydroOpsLLM 封面](figures/hydroopslm-cover.png)

:::: {container} reading-route

::: {container} route-step

[01 · 了解框架](README.zh-TW.md)

水文、水庫決策，以及連結它們的紀錄。


:::

::: {container} route-step

[02 · 設定水庫 agent（英文）](CONFIGURATION.md)

選擇 Rule-based 或 LLM、模型參數、prompt 與可用資訊。


:::

::: {container} route-step

[03 · FE Walter 設定教學（英文）](../tutorials/fe_walter.md)

逐檔理解共用 input、三種操作方法、prompt 與逐日決策，再查看保存紀錄。

:::

::::

## 目錄

| 依序閱讀 | 內容 |
|---|---|
| [Overview](README.zh-TW.md) 與[安裝](GETTING_STARTED.md) | 本套件新增的功能與安裝方式。 |
| [輸入與輸出（英文）](INPUT_OUTPUT.md) | 相對於原生 HydroCNHS 新增的 experiment YAML、資料格式、單位與輸出。 |
| [設定 agent（英文）](CONFIGURATION.md) 與[建立模擬](BUILD_SIMULATION.zh-TW.md) | 選擇規則或 LLM、對應水庫、設定 prompt 與模型。 |
| [F.E. Walter 教學（英文）](../tutorials/fe_walter.md) | 逐檔閱讀實際 experiment、prompt、案例資源與每日決策。 |
| [結果（英文）](RESULTS_GUIDE.md) 與[續跑（英文）](RUNNING.md) | 查看決策、audit、實際流量及中斷紀錄。 |
| [Python API 文件（英文）](API_REFERENCE.md) | 函數參數、回傳值及擴充介面。 |
| [設定參考（英文）](PARAMETER_REFERENCE.md) 與[程式架構（英文）](CODE_STRUCTURE.md) | 查詢欄位及對應的實作。 |

未更動的水文建模與校正方法請依照 [HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)。
本手冊說明新增的輸入、agent 設定、LLM 行為、耦合與紀錄。

## 框架概念

![HydroOpsLLM 概念圖](figures/hydrocnhs-coupling-framework-en.png)

HydroCNHS 先預算連續上游降雨逕流與 routing；逐日循環再透過原生 Dam API
接入規則或 LLM 決策、回覆驗證、水庫物理計算、下游 routing 與已提交狀態回饋。
回覆驗證檢查 action 介面，診斷 audit 評估行為，recorder 保存證據。

## 配套 notebooks

{download}`主教學 <_notebook_downloads/main.ipynb>` ·
{download}`多水庫 <_notebook_downloads/advanced.ipynb>`

下載檔保留原始 notebooks 與已保存輸出。集水區建模與校正／驗證請依 [HydroCNHS 手冊](https://cylin928.github.io/HydroCNHS/)。
[來源與引用](REFERENCE.md)說明原框架及新增操作方法。

[English](index.md)
