# HydroReOpLLM 使用手冊

<div class="hero-band" markdown="1">

**HydroReOpLLM** 建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 之上，在單一水量守恆的模擬迴圈中，結合集水區水文模擬、多水庫河道演算，以及可重現的 **規則式（rule-based）** 或 **LLM 驅動（LLM-driven）** 水庫放流決策。

[安裝並執行範本](GETTING_STARTED.zh-TW.md) · [設計操作員與 LLM 代理人](AGENT_DESIGN.zh-TW.md) · [F.E. Walter 教學](../tutorials/README.zh-TW.md) · [English manual](README.md)

</div>

## 四大核心學習路徑

依序沿著以下四個主題支柱，從頭建立、執行並評估完整的水庫模擬實驗：

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### 支柱一：HydroCNHS 水文基礎

匯入已備妥的區域入流時間序列（`inflows.csv`），或直接耦合已率定的 HydroCNHS 集水區模式（`GWLF`／`ABCD` 搭配 Lohmann 演算），在不重複計入上游放流的前提下綁定子集水區，並對齊逐日或逐時時間步長。

- [原生 HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md)
- [時間尺度與單位](TIME_SCALES.zh-TW.md)
- [實驗性逐時 GWLF](HOURLY_GWLF.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱二：規則與 LLM 代理人設計

設定決定性操作規則（如 Hanasaki 滯洪運轉或自訂季節運轉規線），或設計結合水庫運用要點、水文測站／預報輸入、工程單位提示詞與安全邊界的 LLM 操作員。

- [操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md)
- [決策時資訊](INFORMATION.zh-TW.md)
- [模型服務與可重現性](LLM_MODULES.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱三：耦合架構與執行

串接單一水庫、串聯水庫、分流支線與河道演算延遲；在同一流域混用規則式與 LLM 操作員；於離線狀態預覽提示詞；並驗證保存的水量平衡結果。

- [設定檔說明](CONFIGURATION.zh-TW.md)
- [水庫網路與混合控制](BUILD_SIMULATION.zh-TW.md)
- [檢查、準備、執行與驗證](RUNNING.zh-TW.md)
- [解讀執行結果](RESULTS_GUIDE.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱四：案例研究與參考

探索五年期 F.E. Walter Dam 案例研究（Hanasaki 基準、Seasonal Target 與決策知識包 DKP），離線重播已發表模擬軌跡，或排查設定檔問題。

- [F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)
- [F.E. Walter 教學](../tutorials/README.zh-TW.md)
- [疑難排解](TROUBLESHOOTING.zh-TW.md)

</div>
</div>

## 端對端系統架構

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="HydroReOpLLM 與 HydroCNHS 閉迴路水庫操作模擬架構圖">
  <figcaption><strong>圖 1.</strong> HydroCNHS–HydroReOpLLM 耦合閉迴路架構：集水區入流進入水庫節點後，操作員結合當期蓄水量、入流量與季節目標、測站／預報資料或操作手冊規則（DKP）提出放流請求，再由主機落實蓄水容量與放流上下限，並將出流演算至下游河道。</figcaption>
</figure>

## 公開起點

| 起點 | 操作員與方法 | 網路呼叫（`check` / `run`） | 示範重點 |
| --- | --- | --- | --- |
| [通用既有入流範本](../examples/template/README.zh-TW.md) | 固定離線放流（`4.0` 與 `5.0` m³/s） | `0` / `0` | 雙水庫串聯系統（`upper` → `lower` → `outlet`），示範河道演算延遲與水量平衡檢查。 |
| [F.E. Walter — Hanasaki 規則](../examples/fe_walter/README.zh-TW.md) | `type: rule_based`（`strategy: hanasaki`，α = 0.85） | `0` / `0` | 依 1996–2015 年參考入流氣候統計值驅動的離線 Hanasaki 滯洪運轉規則。 |
| [F.E. Walter — 季節目標（Seasonal Target）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`study_method: seasonal_target`） | `0` / `7`（7 天）或 `1,826`（完整期程） | 使用水庫水位、季節目標水位與前兩日實際放流量進行 LLM 決策。 |
| [F.E. Walter — 決策知識包（DKP）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`study_method: dkp`） | `0` / `7`（7 天）或 `1,826`（完整期程） | 於相同物理流域中加入結構化決策知識包（`dkp.md`）操作規則的 LLM 決策。 |

<div class="callout callout-info" markdown="1">

**執行前先離線檢查。** `reservoir-experiment check` 會以零模型呼叫成本，完整檢查檔案路徑、日期範圍、入流表格、河道演算權重以及第一天的提示詞預覽。僅當您明確傳入 `--allow-network` 且將物理案例標記為就緒時，才會實際發出 LLM 請求。

</div>

## 完整章節總覽

| 學習支柱 | 章節 | 核心內容 |
| --- | --- | --- |
| 開始使用 | [安裝與首次執行](GETTING_STARTED.zh-TW.md) | Python 3.12 環境建置、匯出隨附範例與執行離線範本。 |
| 開始使用 | [通用既有入流範本](../examples/template/README.zh-TW.md) | 逐欄解說 `experiment.yaml`、`case.json` 與 `inflows.csv`。 |
| 水文模擬 | [原生 HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md) | 既有入流與耦合 HydroCNHS（`hydrology.yaml`）比較、暖機期與集水區綁定。 |
| 水文模擬 | [時間尺度與單位](TIME_SCALES.zh-TW.md) | 原生單位（`m3`、`m3/s`、`dt_seconds`）、降雨／PET 水深規範與輸出彙整。 |
| 水文模擬 | [實驗性逐時 GWLF](HOURLY_GWLF.zh-TW.md) | 次日尺度 `run_GWLF_hourly` 工作流程（`3600`、`1800`、`900` 秒）、狀態連續性與診斷。 |
| 代理人與 LLM | [操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md) | Hanasaki 與自訂 Python 規則、LLM 提示詞設計、單位換算與物理安全閘門。 |
| 代理人與 LLM | [決策時資訊](INFORMATION.zh-TW.md) | 在不洩漏未來資訊的前提下接入測站觀測、流量預報、運轉規線與上游水庫狀態。 |
| 代理人與 LLM | [模型服務與可重現性](LLM_MODULES.zh-TW.md) | 可直接套用的 Ollama、OpenAI、Gemini、Anthropic 與 OpenAI-compatible YAML 設定檔。 |
| 耦合與執行 | [設定檔說明](CONFIGURATION.zh-TW.md) | 單檔與拆檔式 YAML 架構、頂層設定欄位與 `outcome_checks`。 |
| 耦合與執行 | [水庫網路與混合控制](BUILD_SIMULATION.zh-TW.md) | 串聯水庫、分流比例、單位歷線延遲、被動溢流堰與規則＋LLM 混合流域。 |
| 耦合與執行 | [檢查、準備、執行與驗證](RUNNING.zh-TW.md) | CLI 工作流程（`check`、`prepare`、`run`、`verify`、`resume`）、呼叫預算與離線重播。 |
| 耦合與執行 | [解讀執行結果](RESULTS_GUIDE.zh-TW.md) | 解讀 `summary.json`、水庫蓄水軌跡、演算流量歷線與水量平衡表。 |
| 案例研究 | [F.E. Walter Dam](../examples/fe_walter/README.zh-TW.md) | 2021–2025 年日尺度與季節基準效能（圖 2–4）、離線重播與本機 Ollama 執行指南。 |
| 參考資料 | [疑難排解](TROUBLESHOOTING.zh-TW.md) | 常見水文設定、YAML 語法、模型服務與驗證錯誤排除方法。 |
