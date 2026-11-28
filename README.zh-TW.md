<div align="center">

<img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png" alt="HydroReOpLLM — 建構於 HydroCNHS 之耦合人水模擬與 LLM 水庫操作框架" width="100%">

# HydroReOpLLM

[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
[![User Manual (EN)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)
[![简体中文使用手册](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-CN.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
[![PyPI](https://img.shields.io/pypi/v/hydroreopllm?label=PyPI&color=0f766e)](https://pypi.org/project/hydroreopllm/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-2563eb)](https://www.python.org/downloads/)
[![BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-475569)](LICENSE)

[English](README.md) · **繁體中文** · [简体中文](README.zh-CN.md)

</div>

**HydroReOpLLM** 是一套建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS)（`GWLF`/`ABCD` 降雨逕流與 Lohmann 河道演算）之上的水文與水庫決策耦合模擬框架，強調嚴格水量平衡閉合。本框架固定集水區水文入流、庫容物理限制與河道演算，讓水文模型建置者能在單一水庫或多水庫串聯系統上，乾淨切換 **Rule-based（Hanasaki 規則）**、自訂 Python 規則或 **LLM** 操作員。

<p align="center">
  <img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/figures/fig1-framework.png" alt="HydroReOpLLM 與 HydroCNHS 閉環水庫操作耦合架構" width="92%">
  <br>
  <em>閉環耦合流程：HydroCNHS 集水區入流與水庫期初蓄水送入規則或 LLM 操作員，再由共用水量平衡引擎強制落實放流上下限、呆庫容與溢流後演算至下游。</em>
</p>

## 60 秒快速上手

需要 **Python 3.12 以上版本**。可由 PyPI 或原始碼安裝，零 API 金鑰即可跑通 F.E. Walter 離線基準（`check` → `run` → `verify`）：

```sh
# 方式 A：由 PyPI 安裝並匯出內建範例
pip install hydroreopllm
reservoir-experiment init-examples

# 方式 B：從原始碼安裝（鎖定內附相依套件環境）
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
```

```sh
# 零 API 金鑰離線實跑 F.E. Walter 水庫基準
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
```

重複執行前請設定新的 `run_id` 與未使用的 `output` 資料夾。完整指令與輸出詳見[安裝與 CLI 指令](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-TW.html)及[結果判讀與水量平衡](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.zh-TW.html)。

## 已驗證基準表現摘要

| 流域案例與模擬期間 | 操作條件 | 水庫水位表現 | 下游流量表現 | 設定入口 |
| --- | --- | --- | --- | --- |
| **F.E. Walter 水庫** *(2021–2025，隨附論文基準)* | **Rule-based**（Hanasaki，α = 0.85） | `KGE 0.077` | `KGE 0.815` | [`fe_walter/rule_based.yaml`](examples/fe_walter/README.zh-TW.md) |
| **F.E. Walter 水庫** *(2021–2025)* | **Without operational knowledge**（`gemma4:12b`） | `KGE 0.806` · `NSE 0.514` · `RMSE 20.85 ft` | `KGE 0.830` | [`fe_walter/seasonal_target.yaml`](examples/fe_walter/README.zh-TW.md) |
| **F.E. Walter 水庫** *(2021–2025)* | **With operational knowledge**（`gemma4:12b` + `dkp.md`） | `KGE 0.858` · `NSE 0.711` · `RMSE 16.07 ft` | `KGE 0.832` | [`fe_walter/dkp.yaml`](examples/fe_walter/README.zh-TW.md) |
| **台灣新店溪串聯水庫** *(2025，Repo 專屬範例，未收錄於論文)* | **Rule-based 串聯**（翡翠 + 直潭 Hanasaki） | `KGE 0.915` · `RMSE 3.63 m` | `KGE 0.760` | [`multi_reservoir/rule_based.yaml`](examples/multi_reservoir/README.zh-TW.md) |
| **台灣新店溪串聯水庫** *(2025，Repo 專屬範例，未收錄於論文)* | **混合式 LLM 聯合調度**（翡翠 LLM + 直潭 Hanasaki） | `NSE 0.498` · `RMSE 3.21 m` | `RMSE 57.92 m³/s` | [`multi_reservoir/hybrid_llm.yaml`](examples/multi_reservoir/README.zh-TW.md) |

> **新店溪 10 年 HydroCNHS `GA_DEAP` 率定與驗證（2016–2025）：** 翡翠入流率定／驗證 `KGE 0.926 / 0.912`；直潭合成流量率定／驗證 `KGE 0.922 / 0.916`。

## 抽換為您的專屬流域（模型建置藍圖）

保持耦合水量平衡迴圈不變，獨立替換任一層模組：

| 您想抽換的模組 | 對應檔案與設定鍵 | 手冊章節 |
| --- | --- | --- |
| **1. 集水區水文與入流** | 自備 `inflows.csv` 或耦合 HydroCNHS `hydrology.yaml`（`GWLF`/`ABCD`） | [入流與 HydroCNHS 設定](https://wenyuchiou.github.io/HydroReOpLLM/HYDROLOGY_SETUP.zh-TW.html) |
| **2. 水庫物理規格與河道演算** | `case.json`／`reservoirs.yaml`、`capacity_m3`、`dead_storage_m3`、`unit_hydrograph` | [多水庫河網串接](https://wenyuchiou.github.io/HydroReOpLLM/MULTI_RESERVOIR.zh-TW.html) · [關鍵設定檔總表](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.zh-TW.html) |
| **3. 操作策略與領域知識** | Hanasaki 規則、自訂 Python 擴充，或 LLM `prompts/`、`dkp.md`、`rule_curve.csv` | [操作規則與 LLM 設計](https://wenyuchiou.github.io/HydroReOpLLM/AGENT_DESIGN.zh-TW.html) |
| **4. 模型服務與水情／預報** | `models.yaml`（Ollama、OpenAI、Gemini、Anthropic）與 `information.yaml`（不洩漏未來水情） | [模型服務設定](https://wenyuchiou.github.io/HydroReOpLLM/MODEL_PROVIDERS.zh-TW.html) · [水情測站與預報](https://wenyuchiou.github.io/HydroReOpLLM/INFORMATION.zh-TW.html) |

## 循序漸進實作課程（4 步驟端到端流程）

全系列模組皆可 **100% 離線執行（`0` API 費用）**，由 HydroCNHS 集水區入流一路實作到水庫與代理人設定及完整模擬驗收：

| 步驟 | 主題 | 實作與驗證重點 | 教學連結 |
| --- | --- | --- | --- |
| **01** | HydroCNHS 集水區與入流 | 載入新店溪 4 子集水區 `hydrology.yaml`（`GWLF`）、驗證 10 年 C&V（`2016–2025`）並檢查 `inflows.csv` | [`01_hydrocnhs_watershed_inflows`](tutorials/01_hydrocnhs_watershed_inflows/README.zh-TW.md) |
| **02** | 水庫物理與代理人設定 | 對照關鍵設定檔（`experiment.yaml`、`reservoirs.yaml`、`models.yaml`、`prompts/`）、檢視第 1 天提示詞與 `dkp.md` | [`02_reservoir_and_agent_setup`](tutorials/02_reservoir_and_agent_setup/README.zh-TW.md) |
| **03** | 單一水庫模擬執行與驗收 | 驗證（`check`）、離線執行 F.E. Walter Hanasaki＋LLM 重播、檢查 `summary.json` 並執行 `verify` | [`03_run_single_reservoir_simulation`](tutorials/03_run_single_reservoir_simulation/README.zh-TW.md) |
| **04** | 多水庫串聯混合模擬 | 設定 `feitsui → zhitan → xindian_outlet`、Lohmann 演算、水利署運用規線與混合式 LLM 串聯重播 | [`04_run_multi_reservoir_cascade`](tutorials/04_run_multi_reservoir_cascade/README.zh-TW.md) |
| **Notebook** | F.E. Walter 互動式實作 | 單一整合筆記本：離線重播 2021 年 Figure 3 比較，並可選用本機 Ollama 實機執行 | [`tutorials/fe_walter.ipynb`](tutorials/fe_walter.ipynb) |

## 內建執行環境與模型追蹤

每次模擬完成後，系統會自動於 `summary.json` 與逐時／逐日紀錄中保存完整可重現與稽核資訊，無須額外匯出指令：

- **執行環境紀錄（`summary.json["runtime_environment"]`）**：Python 版本、HydroReOpLLM 與 HydroCNHS 核心提交／相依套件版本、`source_file_sha256`，以及各水庫代理人設定（`mode`、`provider`、`model`、`temperature`、`seed`、`max_tokens`、`num_ctx`）。
- **即時模型快照**：自動記錄 Ollama `server_runtime_snapshot`（`server_version`、`model_digest_sha256`、`quantization_level`）與雲端實測的 `observed_model_versions` / `observed_system_fingerprints`。
- **完整性與離線稽核**：輸出檔 `output_files` 之 SHA-256 雜湊搭配 `decisions.jsonl`、`physics.jsonl`、`audit.jsonl` 與 `raw/` 紀錄，支援離線執行 `reservoir-experiment verify`。

## 專案結構、測試與授權

```text
HydroReOpLLM/
├── src/llm_reservoir_agent/   # 5 大領域子套件：config/、hydrology/、operators/、information/、simulation/（含 cli.py）
│   └── README.md              # 單頁式原始碼模組與資料流地圖
├── src/hydrocnhs/             # SHA-256 鎖定之內附 HydroCNHS 水文模式（GWLF/ABCD + Lohmann）
├── examples/
│   ├── fe_walter/             # 單一水庫基準（Rule-based、seasonal_target、dkp）
│   └── multi_reservoir/       # 新店溪串聯水庫（10 年 HydroCNHS C&V、混合 LLM）
├── tutorials/                 # 4 步驟離線實作課程（01..04）與互動式 fe_walter.ipynb
├── docs/                      # 三語（EN / 繁體中文 / 简体中文）使用手冊原始檔
└── tests/                     # 水量平衡、河道演算、模型服務、執行環境紀錄與打包測試
```

執行測試套件：

```sh
python -m pip install -c environment/requirements-bundled.txt ".[test]"
python -m pytest -q
```

[BSD 3-Clause 授權](LICENSE) · [第三方授權與來源](THIRD_PARTY_NOTICES.md) · [完整使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
