# HydroReOpLLM 使用手冊

<div class="hero-band" markdown="1">

**HydroReOpLLM** 建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 之上，以水庫操作規則或 LLM 模擬集水區逕流、水庫運轉與下游河道演算。

[安裝與首次執行](GETTING_STARTED.zh-TW.md) · [操作規則與 LLM 設計](AGENT_DESIGN.zh-TW.md) · [F.E. Walter 互動教學](../tutorials/README.zh-TW.md) · [English manual](README.md)

</div>

## 模擬建置四步驟

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### 步驟一：集水區與水文

自備區域入流資料，或耦合 HydroCNHS 集水區模式。

- [入流與 HydroCNHS 設定](HYDROLOGY_SETUP.zh-TW.md)
- [時間尺度與單位](TIME_SCALES.zh-TW.md)
- [逐時 GWLF（實驗性）](HOURLY_GWLF.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 步驟二：水庫操作決策

設定 Hanasaki 規則、自訂 Python 規線或 LLM 提示詞與水情輸入。

- [操作規則與 LLM 設計](AGENT_DESIGN.zh-TW.md)
- [水情測站與預報](INFORMATION.zh-TW.md)
- [模型服務設定](LLM_MODULES.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 步驟三：模擬建置與執行

串接多水庫河網、執行模擬並檢核水量平衡。

- [實驗設定檔](CONFIGURATION.zh-TW.md)
- [多水庫河網串接](BUILD_SIMULATION.zh-TW.md)
- [執行、驗證與續跑](RUNNING.zh-TW.md)
- [結果判讀與水量平衡](RESULTS_GUIDE.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 步驟四：案例研究與協助

重現 F.E. Walter 水庫案例並排除常見設定問題。

- [F.E. Walter 水庫案例](../examples/fe_walter/README.zh-TW.md)
- [F.E. Walter 互動教學](../tutorials/README.zh-TW.md)
- [常見問題與排解](TROUBLESHOOTING.zh-TW.md)

</div>
</div>

## 整體模擬架構

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="HydroReOpLLM 與 HydroCNHS 耦合閉迴路模擬架構圖">
  <figcaption><strong>圖 1.</strong> HydroCNHS–HydroReOpLLM 耦合迴路：集水區入流與期初蓄水量送入操作規則或 LLM，經水庫水量平衡引擎落實物理限制與溢流計算後，演算至下游河道。</figcaption>
</figure>

## 快速開始範例

| 範例 | 操作方法 | 網路呼叫（`check` / `run`） | 示範重點 |
| --- | --- | --- | --- |
| [雙水庫入門範本](../examples/template/README.zh-TW.md) | 固定離線放流（`4.0` 與 `5.0` m³/s） | `0` / `0` | 雙水庫串聯（`upper` → `lower` → `outlet`）與河道演算延遲。 |
| [Rule-based（Hanasaki 規則）](../examples/fe_walter/README.zh-TW.md) | `type: rule_based`（`hanasaki`，α = 0.85） | `0` / `0` | F.E. Walter 離線 Hanasaki 滯洪運轉基準（`rule_based.yaml`）。 |
| [Without operational knowledge（無操作知識）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`seasonal_target.yaml`） | `0` / `7`（7 天）或 `1,826`（全期） | 僅提供水位、季節目標與兩日放流歷史的 LLM 運轉。 |
| [With operational knowledge（具操作知識）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`dkp.yaml`） | `0` / `7`（7 天）或 `1,826`（全期） | 相同水庫案例加入結構化水庫運用要點（`dkp.md`）。 |

<div class="callout callout-info" markdown="1">

**先執行離線檢查。** `reservoir-experiment check` 會以零模型呼叫成本檢查設定檔、日期、入流與第 1 天提示詞預覽；僅在加上 `--allow-network` 時才會連線呼叫 LLM。

</div>
