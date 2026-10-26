# HydroReOpLLM

[![使用手冊](docs/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/index.zh-TW.html)

[English](README.md) | **繁體中文**

HydroReOpLLM 是研究大型語言模型（LLM）水庫操作的 Python 框架，將可設定的水庫
操作方法連接至 HydroCNHS。HydroCNHS 計算集水區入流與河道演算；各操作方法提出
每日放流量；水庫模型依物理限制執行放流並更新蓄水量。更新後的狀態再提供給下一日決策。

![HydroReOpLLM 封面](docs/figures/hydroopslm-cover.png)

## 本專案提供的功能

若已備妥每小時或更短時間步長的平均入流，可使用
[固定時間步長操作](docs/TIME_SCALES.md)。此路徑共用水庫物理與決策介面，
不會執行小時尺度的降雨逕流模型。

- 耦合每日水文、水庫決策、水量平衡、溢流與下游河道演算。
- 規則式與 LLM 操作方法可由實驗設定切換，並共用相同的水庫物理模型。
- 以明確的本機檔案保存提示、可用資訊、檢索知識、模型設定與案例設定檔。
- 保存執行設定、每日決策紀錄、可設定稽核、輸入檔案雜湊與驗證指令，支援可重現實驗。
- 提供完整設定範本、F.E. Walter 案例、已儲存結果與 notebook；檢視結果時無須呼叫 LLM。

套件提供可重用的模擬模組與設定範本。每項研究自行管理操作規則、提示、知識、輸入資料
與案例設定。F.E. Walter 檔案記錄一項研究；其他水庫各自提供案例檔案。

## 從原始碼安裝

HydroReOpLLM 目前尚無公開套件版本。請使用 Python 3.12 與本儲存庫鎖定的相依套件版本。

```bash
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e . -c environment/requirements-bundled.txt
```

下載專案並進入其資料夾後，Windows PowerShell 使用者可執行以下指令建立並啟用環境：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

發行套件名稱為 `hydroreopllm`；Python 套件仍使用 `llm_reservoir_agent` 與
`hydrocnhs` 匯入名稱。

## F.E. Walter 案例

目前維護的案例提供三份實驗設定檔：

| 方法 | 設定檔 | 決策輸入 |
|---|---|---|
| 規則式（Rule-based） | [`experiment.yaml`](examples/fe_walter/coupled/experiment.yaml) | 已註冊的 Hanasaki 案例規則 |
| 未提供額外操作知識的 LLM | [`llm_available.yaml`](examples/fe_walter/coupled/llm_available.yaml) | 當前操作資訊與設定的提示 |
| 提供額外操作知識的 LLM | [`llm_knowledge.yaml`](examples/fe_walter/coupled/llm_knowledge.yaml) | 當前操作資訊、提示與本機知識文件 |

在儲存庫根目錄離線檢查規則式設定：

```bash
reservoir-experiment check examples/fe_walter/coupled/experiment.yaml
```

規則式設定採用 Hanasaki 操作規則；LLM 設定則提供季節水位操作資訊。
[結果指南](examples/fe_walter/results.zh-TW.md)說明這些操作目標的差異。

依序操作 [F.E. Walter notebook 教學](tutorials/README.md)，從 `experiment.yaml`
讀到保存的全年結果，或閱讀[結果指南](examples/fe_walter/results.zh-TW.md)。
已提交的[每日比較資料](examples/fe_walter/coupled/outputs/current_tutorial/daily.csv)與
[來源紀錄](examples/fe_walter/coupled/outputs/current_tutorial/provenance.json)可直接檢視，無須重新模擬或呼叫 LLM。

建立新研究時，先使用[耦合設定範本](templates/coupled/README.md)與
[輸入輸出參考](docs/INPUT_OUTPUT.md)。

## 文件

- [使用指南](docs/USER_GUIDE.zh-TW.md)
- [執行實驗](docs/RUNNING.md)
- [參數參考](docs/PARAMETER_REFERENCE.md)
- [API 參考](docs/API_REFERENCE.md)
- [參考文獻與引用指南](docs/REFERENCE.md)

## 引用

報告 HydroReOpLLM 實驗時，請一併記錄專案 Git 修訂版本、設定與輸入資料版本。
方法專屬參考文獻與來源檢查項目請見[參考文獻與引用指南](docs/REFERENCE.md)。

HydroReOpLLM 使用 HydroCNHS 進行水文模擬與河道演算。請引用原始框架：

> Lin, C.-Y., Yang, Y.-C. E., and Wi, S. (2022). “HydroCNHS: A Python Package of
> Hydrological Model for Coupled Natural Human Systems.” *Journal of Water
> Resources Planning and Management*, 148(12), 06022005.
> [https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630)

## 授權

本專案的主要授權尚待確定。隨附的 HydroCNHS 檔案保留 BSD 3-Clause 授權與歸屬；
請見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)與
[隨附授權全文](licenses/HydroCNHS-BSD-3-Clause.txt)。
