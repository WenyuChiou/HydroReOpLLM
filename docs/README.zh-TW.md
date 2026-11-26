# HydroReOpLLM 使用手冊

<div class="hero-band" markdown="1">

**HydroReOpLLM** 建構於 [**HydroCNHS**](https://github.com/philip928lin/HydroCNHS) 之上，以決定性規則或 LLM 模擬集水區逕流、水庫操作與下游河道演算。

[安裝與執行](GETTING_STARTED.zh-TW.md) · [設計代理人](AGENT_DESIGN.zh-TW.md) · [F.E. Walter 教學](../tutorials/README.zh-TW.md) · [English manual](README.md)

</div>

## 四大核心學習路徑

<div class="panel-grid panel-grid-4" markdown="1">
<div class="panel-card" markdown="1">

### 支柱一：HydroCNHS 水文基礎

準備區域入流資料或耦合原生 HydroCNHS 集水區模式。

- [原生 HydroCNHS 水文設定](HYDROLOGY_SETUP.zh-TW.md)
- [時間尺度與單位](TIME_SCALES.zh-TW.md)
- [實驗性逐時 GWLF](HOURLY_GWLF.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱二：規則與 LLM 代理人設計

設定 Hanasaki 規則、自訂 Python 規線或 LLM 提示詞。

- [操作員與 LLM 代理人設計](AGENT_DESIGN.zh-TW.md)
- [決策時資訊](INFORMATION.zh-TW.md)
- [模型服務與可重現性](LLM_MODULES.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱三：耦合架構與執行

串接多水庫系統、執行模擬並檢視水量平衡。

- [設定檔說明](CONFIGURATION.zh-TW.md)
- [水庫網路與混合控制](BUILD_SIMULATION.zh-TW.md)
- [檢查、準備、執行與驗證](RUNNING.zh-TW.md)
- [解讀執行結果](RESULTS_GUIDE.zh-TW.md)

</div>
<div class="panel-card" markdown="1">

### 支柱四：案例研究與參考

重現 F.E. Walter 案例研究並排除常見設定錯誤。

- [F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)
- [F.E. Walter 教學](../tutorials/README.zh-TW.md)
- [疑難排解](TROUBLESHOOTING.zh-TW.md)

</div>
</div>

## 端對端系統架構

<figure class="figure-card">
  <img src="assets/figures/fig1-framework.png" alt="HydroReOpLLM 與 HydroCNHS 閉迴路水庫操作模擬架構圖">
  <figcaption><strong>圖 1.</strong> HydroCNHS–HydroReOpLLM 耦合迴路：集水區入流與水庫狀態送入規則或 LLM 操作員後，主機物理核心落實放流上下限與溢流計算，再演算至下游。</figcaption>
</figure>

## 公開起點

| 起點 | 操作員與方法 | 網路呼叫（`check` / `run`） | 示範重點 |
| --- | --- | --- | --- |
| [通用範本](../examples/template/README.zh-TW.md) | 固定離線放流（`4.0` 與 `5.0` m³/s） | `0` / `0` | 雙水庫串聯（`upper` → `lower` → `outlet`）與河道演算延遲。 |
| [Rule-based（Hanasaki 規則）](../examples/fe_walter/README.zh-TW.md) | `type: rule_based`（`hanasaki`，α = 0.85） | `0` / `0` | F.E. Walter 離線 Hanasaki 滯洪基準（`rule_based.yaml`）。 |
| [Without operational knowledge（無操作知識）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`seasonal_target.yaml`） | `0` / `7`（7 天）或 `1,826`（全期） | 僅依水位、季節目標與兩日放流歷史進行 LLM 決策。 |
| [With operational knowledge（具操作知識）](../examples/fe_walter/README.zh-TW.md) | `type: llm`（`dkp.yaml`） | `0` / `7`（7 天）或 `1,826`（全期） | 相同案例加上結構化操作手冊條文檢索（`dkp.md`）。 |

<div class="callout callout-info" markdown="1">

**先執行離線檢查。** `reservoir-experiment check` 會以零模型成本驗證檔案、日期、入流與第 1 天提示詞預覽；僅在加上 `--allow-network` 時才會發出即時 LLM 呼叫。

</div>
