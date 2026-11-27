<div align="center">

<img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png" alt="HydroReOpLLM — 建構於 HydroCNHS 之耦合人水模擬與 LLM 水庫操作框架" width="100%">

# HydroReOpLLM

[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
[![User Manual (EN)](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-en.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)
[![简体中文使用手册](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-CN.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-CN.html)
[![PyPI](https://img.shields.io/pypi/v/hydroreopllm?label=PyPI&color=0f766e)](https://pypi.org/project/hydroreopllm/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-2563eb)](https://www.python.org/downloads/)
[![BSD-3-Clause](https://img.shields.io/badge/License-BSD--3--Clause-475569)](LICENSE)
[![ODD+LLM Reproducible](https://img.shields.io/badge/ODD%2BLLM-Reproducible-0d9488)](#內建-oddllm-可重現性框架)

[English](README.md) · **繁體中文** · [简体中文](README.zh-CN.md)

</div>

**HydroReOpLLM** 是一套建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS)（`GWLF`/`ABCD` 降雨逕流與 Lohmann 河道演算）之上的水文與水庫決策耦合模擬框架，強調嚴格水量平衡閉合。本框架固定集水區水文入流、庫容物理限制與河道演算，讓水文模型建置者能在單一水庫或多水庫串聯系統上，乾淨切換 **Rule-based（Hanasaki 規則）**、自訂 Python 規則或 **LLM** 操作員。

<p align="center">
  <img src="https://wenyuchiou.github.io/HydroReOpLLM/assets/figures/fig1-framework.png" alt="HydroReOpLLM 與 HydroCNHS 閉環水庫操作耦合架構" width="92%">
  <br>
  <em>閉環耦合流程：HydroCNHS 集水區入流與水庫期初蓄水送入規則或 LLM 操作員，再由共用水量平衡引擎強制落實放流上下限、呆庫容與溢流後演算至下游。</em>
</p>

## 60 秒快速上手

需要 **Python 3.12 以上版本**。可由 PyPI 或原始碼安裝，零 API 金鑰即可跑通 F.E. Walter 離線基準（`check` → `run` → `verify` → `export-odd`）：

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
reservoir-experiment export-odd runs/fe-walter-rule-based --markdown-out ODD_LLM_REPORT.md
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
| **2. 水庫物理規格與河道演算** | `case.json`／`reservoirs.yaml`、`capacity_m3`、`dead_storage_m3`、`unit_hydrograph` | [多水庫河網串接](https://wenyuchiou.github.io/HydroReOpLLM/MULTI_RESERVOIR.zh-TW.html) · [實驗設定檔](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.zh-TW.html) |
| **3. 操作策略與領域知識** | Hanasaki 規則、自訂 Python 擴充，或 LLM `prompts/`、`dkp.md`、`rule_curve.csv` | [操作規則與 LLM 設計](https://wenyuchiou.github.io/HydroReOpLLM/AGENT_DESIGN.zh-TW.html) |
| **4. 模型服務與水情／預報** | `models.yaml`（Ollama、OpenAI、Gemini、Anthropic）與 `information.yaml`（不洩漏未來水情） | [模型服務設定](https://wenyuchiou.github.io/HydroReOpLLM/MODEL_PROVIDERS.zh-TW.html) · [水情測站與預報](https://wenyuchiou.github.io/HydroReOpLLM/INFORMATION.zh-TW.html) |

## 循序漸進實作課程（Packt 風格教學）

全系列模組皆可 **100% 離線執行（`0` API 費用）**，統一依循 **Setup → Operate → Execute → Inspect Results** 實作節奏：

| 模組 | 主題 | 實作與驗證重點 | 教學連結 |
| --- | --- | --- | --- |
| **01** | 環境建置與首次執行 | 安裝、`check` 驗證、離線跑通 F.E. Walter Hanasaki 基準並繪製蓄水與放流圖 | [`01_setup_and_first_run`](tutorials/01_setup_and_first_run/README.md) |
| **02** | LLM 提示詞與操作知識（DKP） | 對照 `seasonal_target.yaml` 與 `dkp.yaml`、檢視第 1 天提示詞與 JSON Schema 並評分 2021 重播 | [`02_prompt_and_knowledge_design`](tutorials/02_prompt_and_knowledge_design/README.md) |
| **03** | 集水區水文與 10 年率定驗證 | 載入新店溪 4 子集水區 `hydrology.yaml`（`GWLF`）、驗證 10 年 C&V（`2016–2025`）並繪製歷線 | [`03_watershed_hydrology_and_cv`](tutorials/03_watershed_hydrology_and_cv/README.md) |
| **04** | 多水庫串聯與混合調度 | 設定 `feitsui → zhitan → xindian_outlet`、Lohmann 演算、水利署運用規線與混合 LLM 重播 | [`04_multi_reservoir_hybrid_cascade`](tutorials/04_multi_reservoir_hybrid_cascade/README.md) |
| **05** | ODD+LLM 可重現性與稽核 | 檢視 `odd_llm_manifest.json`（區塊 A–E）、驗證 SHA-256 軌跡並匯出 ODD+LLM Markdown 報告 | [`05_odd_llm_reproducibility_and_audit`](tutorials/05_odd_llm_reproducibility_and_audit/README.md) |
| **Notebook** | F.E. Walter 互動式實作 | 單一整合筆記本：離線重播 2021 年 Figure 3 比較，並可選用本機 Ollama 實機執行 | [`tutorials/fe_walter.ipynb`](tutorials/fe_walter.ipynb) |

## 內建 ODD+LLM 可重現性框架

每次模擬完成皆自動產出 `odd_llm_manifest.json` 與 SHA-256 鎖定的 `decisions.jsonl`／`raw/` 追蹤紀錄，支援離線執行 `reservoir-experiment verify` 稽核與 `reservoir-experiment export-odd` 匯出報告：

| 區塊 | 可重現性收錄內容 |
| --- | --- |
| **區塊 A — 認知架構（Cognitive Architecture）** | 代理人型態與策略、工作記憶（`history_steps`）、長期操作知識（`dkp.md`、運用規線）、不洩漏未來水情之資訊設定與物理行動邊界。 |
| **區塊 B — 代理人身分與提示詞（Identity）** | 角色設定與人設框架、提示詞範本 ID／版本、`prompt_sha256` 雜湊與鎖定之原始檔清單。 |
| **區塊 C — 推論組態（Inference Configuration）** | 確切模型 ID、服務端點、Ollama 伺服器版本、模型快照 SHA-256 摘要與量化格式、雲端實測模型版本／`system_fingerprint`、解碼超參數（`temperature`、隨機種子 `seed`、`max_tokens`、`num_ctx`、`think`）、重試／備援鏈與關鍵 Python／HydroCNHS 相依套件版本。 |
| **區塊 D — 行為子模式（Signature、Binding 與 Resolution）** | 觀測欄位與 JSON 輸出 Schema／解析器（`Signature`）、提示詞變數與上下文／知識掛鉤（`Binding`），以及重試、備援、物理截幅、溢洪與稽核實測遙測（`Resolution`）。 |
| **區塊 E — 驗證與稽核（Validation）** | 水量平衡殘差、離線 `verify` 指令與結果、輸出與追蹤檔 SHA-256 雜湊及離線重播能力。 |

檢視範例完整報告：[`examples/fe_walter/ODD_LLM.md`](examples/fe_walter/ODD_LLM.md) · [`examples/multi_reservoir/ODD_LLM.md`](examples/multi_reservoir/ODD_LLM.md)。

## 專案結構、測試與授權

```text
HydroReOpLLM/
├── src/llm_reservoir_agent/   # 水量平衡引擎、CLI、模型服務、ODD+LLM 清單與驗證器
├── src/hydrocnhs/             # SHA-256 鎖定之內附 HydroCNHS 水文模式（GWLF/ABCD + Lohmann）
├── examples/
│   ├── fe_walter/             # 單一水庫基準（Rule-based、seasonal_target、dkp、ODD_LLM.md）
│   └── multi_reservoir/       # 新店溪串聯水庫（10 年 HydroCNHS C&V、混合 LLM、ODD_LLM.md）
├── tutorials/                 # 五單元離線實作課程（01..05）與互動式 fe_walter.ipynb
├── docs/                      # 三語（EN / 繁體中文 / 简体中文）使用手冊原始檔
└── tests/                     # 水量平衡、河道演算、模型服務、ODD+LLM 與打包測試
```

執行測試套件：

```sh
python -m pip install -c environment/requirements-bundled.txt ".[test]"
python -m pytest -q
```

[BSD 3-Clause 授權](LICENSE) · [第三方授權與來源](THIRD_PARTY_NOTICES.md) · [完整使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html)
