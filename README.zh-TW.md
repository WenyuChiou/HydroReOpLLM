# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

![HydroOpsLM 封面](docs/figures/hydroopslm-cover.png)

**HydroOpsLM** 是用於研究耦合水文模擬中語言模型水庫決策的 Python 框架。
它將可設定的決策方法接到
[HydroCNHS](https://github.com/cylin928/HydroCNHS) 原有 Dam API；原生 HydroCNHS
仍負責水文、routing、參數、校正與驗證。

![HydroCNHS 與 HydroOpsLM 耦合架構](docs/figures/hydrocnhs-coupling-framework-en.png)

## 安裝

使用 Python 3.12 與完整 repo：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

執行本機 LLM 教學前，另請安裝 [Ollama](https://ollama.com/)，並讓
`gemma3:4b` 可在本機使用。此 repo 不會替你下載或啟動模型。

## 執行範例

依 [FE Walter 完整示範](examples/fe_walter/README.zh-TW.md)，透過同一條
HydroCNHS 模擬路徑比較自訂規則、zero-shot prompt 與決策知識 prompt。
示範涵蓋設定、執行前檢查、執行、驗證及決策 trace 檢視。

## 文件與引用

[使用手冊](docs/README.zh-TW.md) · [教學](tutorials/README.zh-TW.md) ·
[原生 HydroCNHS 設定](docs/HYDROLOGY_SETUP.md) ·
[HydroCNHS 官方文件](https://cylin928.github.io/HydroCNHS/)

HydroOpsLM 在 HydroCNHS 上加入水庫決策整合。請另外引用原始專案：

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 6022005。

[專案盤點](docs/PROJECT_INVENTORY.md) ·
[Technical note](paper/technical_note.md) ·
[原版來源與授權](third_party/hydrocnhs/SOURCE.json)
