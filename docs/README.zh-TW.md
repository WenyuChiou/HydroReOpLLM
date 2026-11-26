# HydroReOpLLM 使用手冊

<div class="hero-band" markdown="1">

**HydroReOpLLM** 建構於 [HydroCNHS](https://github.com/philip928lin/HydroCNHS) 之上，整合集水區水文模擬、多水庫河道演算與可重現的 **規則式（rule-based）** 或 **LLM 驅動（LLM-driven）** 水庫放流決策，並由單一可稽核的水量平衡核心統一把關。

[安裝並執行範本](GETTING_STARTED.zh-TW.md) · [設計操作員與 LLM 代理人](AGENT_DESIGN.zh-TW.md) · [F.E. Walter 教學](../tutorials/README.zh-TW.md) · [English manual](README.md)

</div>

## 四大核心學習路徑

依序沿著四個主題支柱，從頭到尾完成完整的水庫操作實驗設計：

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### 支柱一：HydroCNHS 水文基礎

透過 `inflows.csv` 或原生 HydroCNHS（`GWLF`／`ABCD` 搭配 Lohmann 演算）準備日尺度或次日尺度區域入流量，避免集水區重複計入，並確認時間軸對齊。

- [原生 HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md)
- [時間尺度與單位](TIME_SCALES.zh-TW.md)
- [實驗性逐時 GWLF](HOURLY_GWLF.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱二：規則與 LLM 代理人設計

設定決定性規則（例如 Hanasaki 滯洪運轉）或 LLM 操作員，搭配結構化提示詞、符合因果時序的資訊目錄、JSON schema 與放流邊界稽核器。

- [操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md)
- [決策時資訊](INFORMATION.zh-TW.md)
- [模型服務與可重現性](LLM_MODULES.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱三：耦合架構與執行

組裝單檔或拆檔式 YAML 設定、連接單庫或混合型多水庫串聯水系、落實網路授權閘門，並驗證每一步的完整來源追蹤證據。

- [設定檔說明](CONFIGURATION.zh-TW.md)
- [水庫網路與多庫系統](BUILD_SIMULATION.zh-TW.md)
- [執行、驗證與續跑](RUNNING.zh-TW.md)
- [解讀執行結果](RESULTS_GUIDE.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱四：案例研究與參考

離線重現 F.E. Walter Dam 21 組論文基準模擬（Hanasaki、Seasonal Target 與 DKP）、檢視已保存的模擬軌跡，或診斷設定與驗證錯誤。

- [F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)
- [F.E. Walter 教學](../tutorials/README.zh-TW.md)
- [疑難排解](TROUBLESHOOTING.zh-TW.md)

</div>
</div>

## 端對端系統架構

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="HydroReOpLLM 與 HydroCNHS 閉迴路水庫操作模擬架構圖">
  <figcaption><strong>圖 1.</strong> HydroCNHS–HydroReOpLLM 耦合閉迴路架構：集水區入流與期初水庫蓄水量進入觀測格式器與因果資訊／決策知識包（DKP）檢索流程，交由決定性規則或 LLM 模型服務產生結構化放流請求並換算為 SI 單位，最後由主機物理核心完成水量平衡與下游河道演算。</figcaption>
</figure>

## 公開起點

| 起點 | 操作員與方法 | 網路呼叫（`check` / `run`） | 示範重點 |
| --- | --- | --- | --- |
| [通用既有入流範本](../examples/template/README.zh-TW.md) | `mode: offline`（`4.0` 與 `5.0` m3/s） | `0` / `0` | 雙水庫串聯系統（`upper` → `lower` → `outlet`），示範演算延遲與水量平衡檢查。 |
| [F.E. Walter — Hanasaki 規則](../examples/fe_walter/README.zh-TW.md) | `type: rule_based`（`strategy: hanasaki`，α = 0.85） | `0` / `0` | 離線 Hanasaki 滯洪運轉規則，固定綁定 1996–2015 年參考入流統計值。 |
| [F.E. Walter — 季節目標（Seasonal Target）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`study_method: seasonal_target`） | `0` / `7`（7 天）或 `1,826`（完整期程） | 依據水位－庫容狀態、季節蓄水目標與前兩步已提交回饋進行 LLM 控制。 |
| [F.E. Walter — 決策知識包（DKP）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`study_method: dkp`） | `0` / `7`（7 天）或 `1,826`（完整期程） | 在相同物理案例上加入決策知識包（`dkp.md`）與規則引用 JSON schema。 |

<div class="callout callout-info" markdown="1">

**先執行零成本離線驗證。** 所有起點皆可使用 `reservoir-experiment check` 離線檢查設定 schema、SHA-256 輸入雜湊值、河網拓樸與渲染後的提示詞預覽。若要執行即時 LLM 推論，必須明確加上 `--allow-network` 旗標，且案例檔案須標記 `"live_readiness": {"ready": true}`（或使用 `synthetic_fixture`）。

</div>

## 完整章節總覽

| 學習支柱 | 章節 | 核心內容 |
| --- | --- | --- |
| 開始使用 | [安裝與首次執行](GETTING_STARTED.zh-TW.md) | Python 3.12 環境建置、`init-examples` 與執行離線通用範本。 |
| 開始使用 | [通用既有入流範本](../examples/template/README.zh-TW.md) | 逐欄解說 `experiment.yaml`、`case.json` 與 `inflows.csv`。 |
| 水文模擬 | [原生 HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md) | `hydrology.yaml`、GWLF／ABCD + Lohmann 設定、`ModelBuilder`、`Dam` 節點綁定與平衡診斷。 |
| 水文模擬 | [時間尺度與單位](TIME_SCALES.zh-TW.md) | 物理核心 SI 單位（`m3`、`m3/s`、`dt_seconds`）、水深轉流量規範與輸出彙整。 |
| 水文模擬 | [實驗性逐時 GWLF](HOURLY_GWLF.zh-TW.md) | 次日尺度 `run_GWLF_hourly` API（`3600`、`1800`、`900` 秒）、狀態連續性與診斷紀錄。 |
| 代理人與 LLM | [操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md) | `LLMReservoirAgent` 回呼介接、Hanasaki 規則、LLM YAML 客製化、提示詞、JSON 契約與安全閘門。 |
| 代理人與 LLM | [決策時資訊](INFORMATION.zh-TW.md) | `InformationCatalog`、因果時序閘門（`valid_time`/`available_at`/`issued_at`）與單位換算。 |
| 代理人與 LLM | [模型服務與可重現性](LLM_MODULES.zh-TW.md) | `ollama`、`openai`、`openai_compatible`、`anthropic` 與 `gemini` 設定、重試、備援與身分鎖定。 |
| 耦合與執行 | [設定檔說明](CONFIGURATION.zh-TW.md) | `v1`/`v2` YAML 格式、`{file: ...}` 拆檔組裝、`UniqueLoader` 規則與 `outcome_checks`。 |
| 耦合與執行 | [水庫網路與多庫系統](BUILD_SIMULATION.zh-TW.md) | 水系拓樸、分流比例、單位歷線演算，以及 Hanasaki + LLM 混合式多水庫串聯設計。 |
| 耦合與執行 | [執行、驗證與續跑](RUNNING.zh-TW.md) | CLI 子指令（`check`、`prepare`、`run`、`verify`、`resume`）、`max_calls` 與重播。 |
| 耦合與執行 | [解讀執行結果](RESULTS_GUIDE.zh-TW.md) | `summary.json`、水庫軌跡／流量／水量平衡 CSV 與 `decisions.jsonl`/`audit.jsonl` 來源追蹤。 |
| 案例研究 | [F.E. Walter Dam](../examples/fe_walter/README.zh-TW.md) | 2021–2025 年日尺度與季節基準效能（圖 2–4）、離線重播與 Ollama 0.40.6 研究重現。 |
| 參考資料 | [疑難排解](TROUBLESHOOTING.zh-TW.md) | 路徑、水文綁定、模型服務與結果驗證錯誤的排查對照表。 |
