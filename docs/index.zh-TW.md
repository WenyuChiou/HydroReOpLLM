# HydroOpsLM 使用手冊

[English](index.md) | [繁體中文](index.zh-TW.md) | [Repository](https://github.com/WenyuChiou/LLM_reservoir_agent)

HydroOpsLM 把水庫決策方法放入 HydroCNHS 模擬。HydroCNHS 仍負責集水區水文、
河川 routing、參數、calibration 與 validation；HydroOpsLM 加入決策方法、
共同水庫收支、回覆檢查、診斷 audit 與 trace 紀錄。

![HydroCNHS 與 HydroOpsLM 的耦合關係](figures/hydrocnhs-coupling-framework-en.png)

藍色箭頭表示水流，黑色箭頭表示資訊與放流提案。灰色卡片提供外部資料或可選知識。原生 Dam API 保留；HydroOpsLM 加入共同的蓄水、放流與 spill 計算。下游模擬資訊只取已完成的日步。GWLF 與 ABCD 是產流模型選項，Lohmann 是 routing 方法；Dam API 將水庫操作接入這條水流流程。

目前操作 runner 為每日步長。決策方法提出 controlled release；主程式物理核心
決定實際 controlled release、spill 與期末蓄水。LLM 不能改寫物理狀態。

## 建議閱讀順序

1. [概念與責任](README.zh-TW.md)
2. [安裝](GETTING_STARTED.md)
3. [第一個完整水庫決策](FIRST_DECISION.md)
4. [輸入與 YAML 設定](USER_GUIDE.zh-TW.md)
5. [LLM 決策流程](LLM_MODULES.zh-TW.md)
6. [Check、run、verify](USER_GUIDE.md#6-check-run-and-verify)
7. [結果、audit 與 trace](RESULTS_GUIDE.md)
8. [三種操作方法](../examples/fe_walter/README.zh-TW.md)
9. [多水庫與自己的流域](../tutorials/advanced.ipynb)

保存的教學與文件建置不會執行 notebook，也不會呼叫模型。

## 三種操作方法

| 公開名稱 | 決策來源 | 指南 |
|---|---|---|
| 規則式基準 | Hanasaki 型防洪規則 | [閱讀指南](../examples/fe_walter/benchmark/README.zh-TW.md) |
| 使用可用資訊的 LLM 操作 | 原始 prompt 與可用水庫資訊 | [閱讀指南](../examples/fe_walter/zero_shot/README.zh-TW.md) |
| 使用檢索知識的 LLM 操作 | 相同介面加上來源綁定的檢索知識 | [閱讀指南](../examples/fe_walter/dkp/README.zh-TW.md) |

`zero_shot`、`dkp` 與 `reference_v3_7` 是保留的歷史機器 ID，只在路徑與
provenance 中使用。

## 參考資料

- [決策資訊](INFORMATION.zh-TW.md)：來源、設定檔、因果選取與下游結果檢查。
- [完整參數總表](PARAMETER_REFERENCE.md)：YAML、model、agent、物理、routing
  與 audit 欄位。
- [引用與來源](REFERENCE.md)：HydroCNHS 與規則式基準來源。
- {download}`下載原始 main notebook <_notebook_downloads/main.ipynb>`
- {download}`下載原始 advanced notebook <_notebook_downloads/advanced.ipynb>`

氣象驅動模型建立、集水區參數及 calibration/validation，請使用
[原始 HydroCNHS 文件](https://cylin928.github.io/HydroCNHS/)。
