# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

[![線上文件站 — 立即閱讀](https://wenyuchiou.github.io/LLM_reservoir_agent/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/LLM_reservoir_agent/)

![HydroOpsLM 封面](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** 是用於研究耦合水文模擬中語言模型水庫決策的 Python 框架。
它將可設定的決策方法接到
[HydroCNHS](https://github.com/cylin928/HydroCNHS) 原有 Dam API；原生 HydroCNHS
仍負責水文、routing、參數、校正與驗證。

![HydroCNHS 與 HydroOpsLM 耦合架構](docs/figures/hydrocnhs-coupling-framework-en.png)

每座水庫透過 HydroCNHS 的 Dam API 選用一種決策方法。
HydroOpsLM 加入共同蓄水、放流及 spill 計算。回覆檢查與操作規則 audit
分開進行；診斷實驗保留失敗的 audit 判定。

## 安裝

使用 Python 3.12 與完整 repo：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

執行本機 LLM 教學前，另請安裝 [Ollama](https://ollama.com/)，並讓
`gemma3:4b` 可在本機使用。此 repo 不會替你下載或啟動模型。

## 範例

從 [FE Walter 完整示範](examples/fe_walter/README.zh-TW.md)開始。
三種方法共用水庫操作及 routing 介面。

| 方法 | 決策來源 | 從這裡開始 |
|---|---|---|
| Rule-based benchmark | Hanasaki-based 防洪放流規則 | [規則及相同三日案例](examples/fe_walter/README.zh-TW.md#rule-based-benchmark) |
| Zero-shot | Prompt 與可用水庫資訊 | [Prompt 及 Ollama 設定](examples/fe_walter/zero_shot/README.zh-TW.md) |
| DKP | 相同 LLM 介面加上操作知識檢索 | [知識及 Ollama 設定](examples/fe_walter/dkp/README.zh-TW.md) |

[主教學](tutorials/main.ipynb)依序展示 input、YAML、prompt／規則、
check、run、verify 及 audit／trace。[進階篇](tutorials/advanced.ipynb)
涵蓋多水庫、被動出口、routing 與自己的資料。

## 文件與引用

[使用手冊](docs/README.zh-TW.md) · [教學](tutorials/README.zh-TW.md) ·
[原生 HydroCNHS 設定](docs/HYDROLOGY_SETUP.md) ·
[**cylin928.github.io/HydroCNHS/**](https://cylin928.github.io/HydroCNHS/)

從[線上文件站](https://wenyuchiou.github.io/LLM_reservoir_agent/)開始，
依章節查看三種方法、單／多水庫設定及 audit／trace，另可下載 tutorial notebook。
也可[在本機建置文件站](docs/BUILDING.md)。

HydroOpsLM 在 HydroCNHS 上加入水庫決策整合。請另外引用原始專案：

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 06022005。

[專案盤點](docs/PROJECT_INVENTORY.md) ·
[Technical note](paper/technical_note.md) ·
[建置 HTML 文件](docs/BUILDING.md) ·
[原版來源與授權](third_party/hydrocnhs/SOURCE.json)
