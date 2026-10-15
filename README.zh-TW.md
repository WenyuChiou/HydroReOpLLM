<img src="docs/figures/assets/branding/hydroopslm-logo.png" align="right" width="64" height="64" alt="HydroOpsLM logo">

# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

[![閱讀使用手冊](docs/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroOpsLM/)

![HydroOpsLM 封面](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** 將可設定的語言模型水庫操作接到
[HydroCNHS](https://github.com/cylin928/HydroCNHS)。研究者可為每座水庫選擇
資訊、prompt 與操作檢查。HydroCNHS 提供水文與河川 routing；HydroOpsLM
加入水庫收支計算，記錄每次提案、audit 與實際放流。

![HydroOpsLM 概念圖](docs/figures/hydrocnhs-coupling-framework-en.png)

藍色箭頭傳遞水流，黑色箭頭傳遞資訊與提案。每座水庫透過原生 Dam API
選用一種操作方法。共同蓄水、放流及 spill 計算由 HydroOpsLM 加入。

## 安裝

使用 Python 3.12，在 repo 根目錄執行：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

依[安裝指南](docs/GETTING_STARTED.md)檢查設定，不需推論。三日 LLM 設定範例使用
本機 Ollama `gemma3:4b`，temperature **0.7**。讀取已保存結果不需要模型；
框架不會下載或啟動模型。

## FE Walter：一個案例、三種方法

先看[建立模擬](docs/BUILD_SIMULATION.zh-TW.md)，再依
[FE Walter 案例](examples/fe_walter/README.zh-TW.md)操作。

| 方法 | 決策來源 | 逐步教學 |
|---|---|---|
| Rule-based benchmark | 已發表的水庫規則，調整為每日防洪操作 | [規則式](examples/fe_walter/benchmark/README.zh-TW.md) |
| 使用可用資訊的 LLM | Prompt 與可用水庫資訊 | [可用資訊](examples/fe_walter/zero_shot/README.zh-TW.md) |
| 使用檢索知識的 LLM | 相同介面加上有來源的操作知識 | [檢索知識](examples/fe_walter/dkp/README.zh-TW.md) |

案例共用物理設定，再依序教授設定、操作方法、執行及保存決策。
先看已保存的 **2020 全年每日範例（366 日）**，再查看完整 2016–2020 紀錄。

## 研究與引用

水文設定、集水區參數及校正／驗證請依
[原始 HydroCNHS 手冊](https://cylin928.github.io/HydroCNHS/)。
請引用原作者的工作：

Lin, C. Y., Yang, Y. C. E., and Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 06022005。

[方法來源](docs/REFERENCE.md) · [來源與授權](third_party/hydrocnhs/SOURCE.json)
