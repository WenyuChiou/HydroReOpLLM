# HydroOpsLM 使用手冊

HydroOpsLM 將水庫操作決策接到 HydroCNHS 水文與河川 routing。
為每座水庫設定資訊、prompt 與檢查，再追查提案如何成為實際放流。

![HydroOpsLM 概念圖](figures/hydrocnhs-coupling-framework-en.png)

[查看完整尺寸概念圖](https://wenyuchiou.github.io/HydroOpsLM/_images/hydrocnhs-coupling-framework-en.png)。

藍色箭頭傳遞水流，黑色箭頭傳遞資訊與提案。兩種操作方法使用原生 Dam API。
HydroOpsLM 加入共同蓄水、放流與 spill 計算。回覆檢查與操作 audit
回答不同問題，紀錄分開保留。

## 從這裡開始

先[安裝 HydroOpsLM](GETTING_STARTED.md)，再看
[第一個水庫決策](FIRST_DECISION.md)。教學開啟已保存的真實 Ollama 回覆，
依序展示檢查、audit、實際放流與下一日資訊。閱讀手冊不會呼叫模型。

## 三個完整範例

三種方法使用相同 FE Walter input 與初始條件。
[案例概覽](../examples/fe_walter/README.zh-TW.md)說明共同設定。

::: {container} method-list

### [規則式基準](../examples/fe_walter/benchmark/README.zh-TW.md)

已發表的水庫規則，調整為每日防洪操作。

### [使用可用資訊的 LLM](../examples/fe_walter/zero_shot/README.zh-TW.md)

獨立 prompt、水庫資訊與本機模型。

### [使用檢索知識的 LLM](../examples/fe_walter/dkp/README.zh-TW.md)

相同決策介面，加上有來源的操作知識。

:::

每份教學依序涵蓋 **input → YAML → prompt／規則 → check → run → verify → 結果**。
三日紀錄展示整合流程，不能證明策略優劣。

## 建立自己的實驗

接著閱讀[input 與 YAML](USER_GUIDE.zh-TW.md)、[決策資訊](INFORMATION.zh-TW.md)
及[prompt 與模組](LLM_MODULES.zh-TW.md)，再看
[多水庫](../tutorials/advanced.ipynb)、
[結果與 audit／trace](RESULTS_GUIDE.md)及[執行與維護](RUNNING.md)。

## Notebooks 與來源

{download}`主 notebook <_notebook_downloads/main.ipynb>` ·
{download}`進階 notebook <_notebook_downloads/advanced.ipynb>`

下載檔保留原始 notebook 與已保存輸出。
集水區設定、水文參數與校正／驗證請依
[HydroCNHS 手冊](https://cylin928.github.io/HydroCNHS/)。
框架與 benchmark 的來源見[引用說明](REFERENCE.md)。

[English](index.md) | [繁體中文](index.zh-TW.md) ·
[Repository](https://github.com/WenyuChiou/HydroOpsLM)
