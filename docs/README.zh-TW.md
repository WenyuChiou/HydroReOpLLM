# HydroReOpLLM 套件總覽

<div class="cover-banner">
  <img src="assets/branding/cover.png" alt="HydroReOpLLM — 結合大型語言模型水庫決策代理與 HydroCNHS 的耦合人水系統模擬框架">
</div>

<div class="hero-band" markdown="1">

**HydroReOpLLM** 延伸自 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 的半分散式集水區水文與水庫代理人架構，讓水文學家在同一套水量守恆的模擬系統中，建置並比較**規則式（Rule-based）**與 **LLM 驅動**的水庫放流操作。

[安裝與 CLI 指令](GETTING_STARTED.zh-TW.md) · [操作規則與 LLM 設計](AGENT_DESIGN.zh-TW.md) · [互動式 Notebook 教學](../tutorials/README.zh-TW.md) · [English overview](README.md) · [简体中文](README.zh-CN.md)

</div>

## 何時適合使用 HydroReOpLLM？

- 想在完全相同的集水區入流與河道演算條件下，公平比較 **Rule-based（Hanasaki 規則）**與 **LLM 操作員**的水庫調度表現。
- 需要將真實水庫運用要點（操作知識）、水文測站觀測或流量預報，以不洩漏未來水情的方式納入每日或逐時放流決策。
- 希望在單一水庫或串聯多水庫流域中，同時驗證蓄水量、受控放流、溢流與下游河道流量的質量平衡。
- 需要可重現的離線檢查、重播與中斷續跑機制，避免重複耗費模型推論成本。

## 三大核心模組

<div class="panel-grid panel-grid-3" markdown="1">
<div class="panel-card" markdown="1">

### 模組一：水文與河道演算

支援直接匯入子集水區區域入流 CSV，或耦合已率定的 HydroCNHS 集水區模式（`GWLF` / `ABCD` + Lohmann 演算），並以單位歷線將水庫出流演算至下游測站。

</div>
<div class="panel-card" markdown="1">

### 模組二：操作規則與 LLM

每個受控水庫可指派 Hanasaki 滯洪規則、自訂 Python 操作規線，或結合提示詞、水情測站、預報與水庫運用要點的 LLM 操作員。

</div>
<div class="panel-card" markdown="1">

### 模組三：物理限制與驗證

共用的水庫水量平衡引擎統一落實放流上下限、呆庫容保護與滿庫溢流，並提供離線 `check` 與 `verify` 查核完整水量守恆與水情時序。

</div>
</div>

## 耦合模擬運作方式

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="HydroReOpLLM 與 HydroCNHS 耦合閉迴路模擬架構圖">
  <figcaption><strong>圖 1.</strong> HydroCNHS–HydroReOpLLM 耦合迴路：集水區入流與期初蓄水量送入水庫操作規則或 LLM，經水庫水量平衡引擎落實物理限制與溢流後演算至下游河道。</figcaption>
</figure>

## 使用手冊導覽

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### 安裝與執行流程

建置環境、了解 CLI 流程並判讀輸出結果。

- [安裝與 CLI 指令](GETTING_STARTED.zh-TW.md)
- [實驗設定檔](CONFIGURATION.zh-TW.md)
- [執行、驗證與續跑](RUNNING.zh-TW.md)
- [結果判讀與水量平衡](RESULTS_GUIDE.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 集水區與水文河網

準備區域入流、設定 HydroCNHS 與多水庫串接。

- [入流與 HydroCNHS 設定](HYDROLOGY_SETUP.zh-TW.md)
- [多水庫河網串接](MULTI_RESERVOIR.zh-TW.md)
- [時間尺度與單位](TIME_SCALES.zh-TW.md)
- [逐時 GWLF（實驗性）](HOURLY_GWLF.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 水庫操作決策

設計操作規則、LLM 提示詞、水情輸入與模型服務。

- [操作規則與 LLM 設計](AGENT_DESIGN.zh-TW.md)
- [水情測站與預報](INFORMATION.zh-TW.md)
- [模型服務設定](MODEL_PROVIDERS.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 範例與實作教學

從單一水庫到多水庫串聯案例，並快速排除設定問題。

- [單一水庫案例（F.E. Walter）](../examples/fe_walter/README.zh-TW.md)
- [互動式 Notebook 教學](../tutorials/README.zh-TW.md)
- [多水庫串聯案例](../examples/multi_reservoir/README.zh-TW.md)
- [常見問題與排解](TROUBLESHOOTING.zh-TW.md)

</div>
</div>

## 內建公開範例

| 範例 | 設定檔與操作方法 | 執行方式 | 示範重點 |
| --- | --- | --- | --- |
| [單一水庫：Rule-based（Hanasaki 規則）](../examples/fe_walter/README.zh-TW.md) | `examples/fe_walter/rule_based.yaml`（`hanasaki`，α = 0.85） | 離線 | F.E. Walter 離線 Hanasaki 滯洪基準。 |
| [單一水庫：Without operational knowledge（無操作知識）](../examples/fe_walter/README.zh-TW.md) | `examples/fe_walter/seasonal_target.yaml`（LLM） | 本機 Ollama | 僅提供水位、季節目標與兩日放流歷史的 LLM 運轉。 |
| [單一水庫：With operational knowledge（具操作知識）](../examples/fe_walter/README.zh-TW.md) | `examples/fe_walter/dkp.yaml`（LLM + `dkp.md`） | 本機 Ollama | 相同水庫案例加上結構化水庫運用要點檢索。 |
| [多水庫串聯：新店溪規則基準](../examples/multi_reservoir/README.zh-TW.md) | `examples/multi_reservoir/rule_based.yaml`（雙庫 Hanasaki） | 離線 | Repo 專屬案例（未收錄於論文）：10 年 HydroCNHS C&V 驅動 2025 全年雙庫（`feitsui` → `zhitan` → `xindian_outlet`）水量平衡基準。 |
| [多水庫串聯：新店溪混合規則＋LLM](../examples/multi_reservoir/README.zh-TW.md) | `examples/multi_reservoir/hybrid_llm.yaml`（聯合調度 LLM＋直潭 Hanasaki） | 本機 Ollama | Repo 專屬案例：翡翠聯合供水調度 LLM（`xindian_study` + 南勢溪入流）結合直潭 Hanasaki 混聯。 |

<div class="callout callout-info" markdown="1">

**先執行離線檢查。** `reservoir-experiment check` 會以零模型成本驗證設定檔、日期、入流與第 1 天提示詞預覽；僅在明確加上 `--allow-network` 時才會連線呼叫 LLM。

</div>
