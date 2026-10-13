# HydroOpsLM 使用手冊

[English](index.md) | [繁體中文](index.zh-TW.md)

HydroOpsLM 將可設定的水庫決策接到原生 HydroCNHS Dam API。
HydroCNHS 提供水文模型與河道 routing；HydroOpsLM 加入 LLM prompt、
回覆檢查、水庫計算及 audit／trace 紀錄。

![HydroOpsLM 概念圖](figures/hydrocnhs-coupling-framework-en.png)

每座水庫選用一種操作方法。藍線表示水流；黑線表示資訊與決策。
回覆檢查確認輸出有效，操作 audit 判斷是否符合設定的規則，判定原樣保存在 trace。

## 從這裡開始

| 步驟 | 閱讀 | 準備內容 |
|---|---|---|
| 1 | [安裝](../README.zh-TW.md#安裝) | Python 環境與模型需求 |
| 2 | [FE Walter 示範](../examples/fe_walter/README.zh-TW.md) | Input、初始蓄水與三種方法 |
| 3 | [模組設定](USER_GUIDE.zh-TW.md) | YAML、水庫 agent、prompt 及可選知識 |
| 4 | [LLM 決策流程](LLM_MODULES.zh-TW.md) | Info → prompt → proposal → 檢查 → 實際放流 → 下一步資訊 |
| 5 | [查看 audit／trace](USER_GUIDE.zh-TW.md#偵錯) | 結果、失敗檢查與重現紀錄 |

## 三個範例

| 方法 | 決策來源 | 範例 |
|---|---|---|
| Rule-based benchmark | Hanasaki-based 防洪放流規則 | [Rule-based](../examples/fe_walter/benchmark/README.zh-TW.md) |
| Zero-shot | Prompt 與可用水庫資訊 | [Zero-shot](../examples/fe_walter/zero_shot/README.zh-TW.md) |
| DKP | 相同 LLM 介面加上操作知識 | [DKP](../examples/fe_walter/dkp/README.zh-TW.md) |

## 教學與 notebook

文件站可直接閱讀[單水庫教學](../tutorials/main.ipynb)及
[多水庫教學](../tutorials/advanced.ipynb)，表格、圖與模型回覆使用保存的實驗紀錄。
建置文件站不會呼叫模型。

- {download}`下載主教學 notebook <_notebook_downloads/main.ipynb>`
- {download}`下載進階 notebook <_notebook_downloads/advanced.ipynb>`

## 原生水文與引用

集水區參數、水文建模及校正／驗證請使用
[HydroCNHS 文件站](https://cylin928.github.io/HydroCNHS/)與
[原生設定說明](HYDROLOGY_SETUP.md)。請另外引用
[原版 HydroCNHS 論文](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630)，
區分其貢獻與 HydroOpsLM 新增功能。
