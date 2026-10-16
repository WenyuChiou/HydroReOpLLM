# HydroOpsLLM

[![使用手冊](docs/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroOpsLM/)
![Python 3.12 setup](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)

[English](README.md) | [繁體中文](README.zh-TW.md) · [使用手冊](https://wenyuchiou.github.io/HydroOpsLM/) · [快速入門](#安裝)

HydroOpsLLM 是以 HydroCNHS 為基礎的 Python 套件，將 LLM 驅動的決策與水文模擬耦合，應用於水庫操作與水資源管理。

![HydroOpsLLM 封面](docs/figures/hydroopslm-cover.png)

## 安裝

使用 Python 3.12。專案維持私有期間需要 repo 存取權。

```sh
git clone https://github.com/WenyuChiou/HydroOpsLM.git
cd HydroOpsLM
```

Linux/macOS 已安裝 Python 3.12 時：

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell 可透過 Python launcher 使用 Python 3.12 時：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

啟用後先確認 interpreter 顯示 Python 3.12，再安裝：

```sh
python --version
python -m pip install -e . -c environment/requirements-bundled.txt
```

## 快速入門：逐日水庫操作

HydroOpsLLM 以**一天為時間步長**推進耦合系統：讀取入流與狀態 → 提出放流需求 → 更新蓄水並演算出流 → 將實施結果回饋至下一日決策。模擬起訖期間與逐日時間步長分開設定。

先執行不需語言模型或 API key 的 F.E. Walter 規則式範例：

```sh
python run_experiment.py check examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-benchmark --require-offline
```

此範例依操作規則計算 2016 年 1 月 1–3 日的逐日放流，並非固定動作。請使用尚不存在的輸出位置；設定、延長期間與再次執行方式見[執行指南](docs/USER_GUIDE.md)。

### 探索 Rule-based、Zero-shot 與 DKP

[F.E. Walter 教學](examples/fe_walter/README.md)以同一套逐日耦合流程說明三種方法：

| 方法 | 逐日決策 | 範例 |
|---|---|---|
| Rule-based | 依入流、蓄水與歷史統計執行防洪規則 | [執行與檢視](examples/fe_walter/benchmark/README.md) |
| Zero-shot | LLM 使用操作指示與可用水庫資訊 | [提示詞、回覆與操作](examples/fe_walter/zero_shot/README.md) |
| DKP | LLM 另使用檢索的文件知識 | [檢索、回覆與操作](examples/fe_walter/dkp/README.md) |

LLM 範例保留 Anik V3.7 reference 方法的整合。[主教學 notebook](tutorials/main.ipynb)可直接查看已保存的逐日提示詞、回覆、放流與蓄水，不需發送模型請求。執行前先檢查兩份 LLM 設定：

```sh
python run_experiment.py check examples/fe_walter/zero_shot/experiment.ollama.yaml
python run_experiment.py check examples/fe_walter/dkp/experiment.ollama.yaml
```

`check` 不發送 provider 請求。新 LLM 模擬需要本機 Ollama 已備妥 `gemma3:4b`，並明確指定 `--allow-network`；這兩個範例不需 API key。其他 provider 可能需要憑證並產生費用。執行命令見各方法連結。保存的教學紀錄用來說明決策，並非受控效能排名。

## 功能

- 為各受控水庫設定決策資訊、提示詞與模型 provider。
- 以共用水庫動作介面替換規則式與 LLM 策略。
- 將水庫操作接入 HydroCNHS 河川演算，並把實施結果回饋至後續決策。
- 保存資訊、提案、稽核與物理結果，支援可重現的分析。
- 建立多水庫實驗，見[進階教學](tutorials/advanced.ipynb)。

## 架構與資訊流

三種流程分別處理：

1. **水量與物理狀態：** 入流 → HydroCNHS 演算 → 水庫狀態轉移 → 下游演算及蓄水更新。
2. **決策資訊：** 選取的狀態與符合可用條件的外部資訊 → 提示詞／backend → 動作需求。
3. **回饋與證據：** 已實施的狀態轉移 → 後續決策歷史；決策及物理紀錄 → 稽核與保存結果驗證。

LLM 接收訊息中提供的資訊；蓄水與河川演算仍由主程式掌管。

| 元件 | 現行模組 | 責任 |
|---|---|---|
| 設定與編排 | `workflow`、`case`、`experiment` | 驗證輸入、組合方法、執行條件管制與協調實驗 |
| 原生模擬耦合 | `network`、`agent` | 將策略接至 HydroCNHS Dam agents、演算與已提交結果回饋 |
| 物理收支 | `physics`、`passive`、`balance` | 實施放流、溢流、蓄水與水庫／河網水量收支 |
| 決策資訊 | `information`、`information_runtime` | 選取時間條件合格的資料並接入模擬資訊 |
| 策略與 provider | `configured_backend`、`benchmark`、`reference_backend`、`policy_adapter` | 產生及標準化提案，保留各方法的特定行為 |
| 稽核與證據 | `auditor`、`configured_audit`、`outcome`、`trace`、`verification` | 評估設定的準則、診斷演算結果並驗證保存紀錄 |

上述模組屬於 `llm_reservoir_agent`。隨附的 `hydrocnhs` 命名空間保留上游 API；`delaware_operations` 保留歷史與相容程式，其中部分 adapters 仍被 reference 方法使用。介面與擴充界線見 [LLM 模組](docs/LLM_MODULES.md)。

## 文件與研究使用

[使用手冊](https://wenyuchiou.github.io/HydroOpsLM/) · [設計模擬](docs/BUILD_SIMULATION.md) · [模型設定](docs/USER_GUIDE.md) · [閱讀結果](docs/RESULTS_GUIDE.md)

目前 CLI 使用給定的逐日入流，搭配原生 HydroCNHS 河川演算與 Dam 耦合。F.E. Walter 範例讀取固定保存的水文輸出；氣象驅動整合需要明確設定原生模型與策略接線，見[水文設定](docs/HYDROLOGY_SETUP.md)與[逐日耦合](examples/fe_walter/coupling.md)。

請記錄程式 commit、環境、輸入、提示詞、模型設定及完整執行證據。物理假設、稽核解讀與擴充需求見[案例指南](examples/fe_walter/README.md)、[模組指南](docs/LLM_MODULES.md)與[執行指南](docs/RUNNING.md)。本套件為研究軟體；操作稽核不構成水壩安全認證。

## 授權

專案授權待定，目前沒有 MIT 授權。HydroCNHS 保留其 [BSD 3-Clause 授權](licenses/HydroCNHS-BSD-3-Clause.txt)。公開散布前，請確認[第三方聲明](THIRD_PARTY_NOTICES.md)，包括尚未釐清的 Anik 再散布權限。

## 參考文獻與引用

HydroOpsLLM 建築於 [HydroCNHS](https://github.com/cylin928/HydroCNHS)，隨附核心版本為 commit `fdd5097a3fcabb312c6c3739efc71da2d67c47da`（[來源紀錄](third_party/hydrocnhs/SOURCE.json)）。請引用原始框架：

Lin, C.-Y., Yang, Y.-C. E., and Wi, S. (2022). “HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems.” *Journal of Water Resources Planning and Management*, 148(12), 06022005. [doi:10.1061/(ASCE)WR.1943-5452.0001630](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).

操作方法來源見[參考文獻指南](docs/REFERENCE.md)。請另外記錄 HydroOpsLLM commit；專用軟體引文／DOI 尚未指定。
