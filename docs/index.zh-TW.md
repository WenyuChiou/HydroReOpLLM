# HydroOpsLM 使用手冊

在耦合水文模擬中設定水庫操作。先了解框架、建立模擬，再以一個 FE Walter 案例學習三種操作方法。

![HydroOpsLM 封面](figures/hydroopslm-cover.png)

:::: {container} reading-route

::: {container} route-step

[01 · 了解框架](README.zh-TW.md)

水文、水庫決策，以及連結它們的紀錄。


:::

::: {container} route-step

[02 · 建立模擬](BUILD_SIMULATION.zh-TW.md)

準備案例、選擇決策資訊，再設定操作方法。


:::

::: {container} route-step

[03 · FE Walter 案例](../examples/fe_walter/README.zh-TW.md)

同一地點、共用 input 與三種方法，接著查看完整五年保存結果。

:::

::::

## 框架概念

![HydroOpsLM 概念圖](figures/hydrocnhs-coupling-framework-en.png)

HydroCNHS 提供降雨逕流與河川 routing；HydroOpsLM 透過原生 Dam API 接入規則式或語言模型操作，並記錄實際放流。

[查看完整尺寸概念圖](https://wenyuchiou.github.io/HydroOpsLM/_images/hydrocnhs-coupling-framework-en.png)。

## 配套 notebooks

{download}`主教學 <_notebook_downloads/main.ipynb>` ·
{download}`多水庫 <_notebook_downloads/advanced.ipynb>`

下載檔保留原始 notebooks 與已保存輸出。集水區建模與校正／驗證請依 [HydroCNHS 手冊](https://cylin928.github.io/HydroCNHS/)。
[來源與引用](REFERENCE.md)說明原框架及新增操作方法。

[English](index.md)
