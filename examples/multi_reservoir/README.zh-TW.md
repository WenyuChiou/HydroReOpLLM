# 多水庫串聯案例：新店溪翡翠水庫 → 直潭壩

<div class="hero-band" markdown="1">

本基準測試以台灣經濟部水利署（WRA）歷史日營運資料，在 **2020 年 5 月 7 日 – 6 月 5 日**梅雨鋒面期間評估新店溪雙水庫串聯系統（**翡翠水庫 `feitsui`** → **直潭壩 `zhitan`** → **`xindian_outlet`**），比較**全規則串聯（Hanasaki + Hanasaki）**與**混合式 LLM 串聯（翡翠 LLM + 直潭 Hanasaki）**兩種操作條件。

</div>

## 研究區域與基準設計

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig5-xindian-study-area.png" alt="新店溪串聯水庫研究區域與河道演算網路圖：翡翠水庫、南勢溪側向入流與直潭壩">
  <figcaption><strong>圖 5.</strong> 台灣新店溪串聯水庫研究流域：翡翠水庫（有效庫容 335,505,000 m³，放流上下限 0–500 m³/s）出流經 <code>[0.8, 0.2]</code> 單位歷線演算並匯入南勢溪側向入流（<code>zhitan_local</code>）後進入直潭壩（有效庫容 1,918,900 m³，放流上下限 0–800 m³/s），再經 <code>[1.0]</code> 演算至 <code>xindian_outlet</code>。</figcaption>
</figure>

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 情境一：全規則串聯（Rule-based）

- **設定檔**：[`rule_based.yaml`](rule_based.yaml)
- **方法**：上下游皆採 Hanasaki 滯洪規則（`strategy: benchmark`，α = 0.85），分別依 2019 年參考統計 [`feitsui_statistics.json`](feitsui_statistics.json) 與 [`zhitan_statistics.json`](zhitan_statistics.json) 離線執行。

</div>
<div class="panel-card" markdown="1">

### 情境二：混合式 LLM 串聯（Hybrid LLM）

- **設定檔**：[`hybrid_llm.yaml`](hybrid_llm.yaml)
- **方法**：上游翡翠水庫（`feitsui_operator`）由 `gemma4:12b` 操作（`history_steps: 2`，`reservoir-action.v1` JSON），搭配下游直潭壩（`zhitan_operator`）採用 Hanasaki 規則。
- **提示詞**：[System prompt](prompts/system.txt) · [User 範本](prompts/operator.txt)。

</div>
</div>

## 設定檔與快速檢查

兩組條件共用 [`case.json`](case.json) 與 32 天 WRA 實測區域入流 [`inflows.csv`](inflows.csv)（`2020-05-05`–`2020-06-05`；模擬視窗取 `2020-05-07`–`2020-06-05`，初期有效蓄水為翡翠 `253,810,100 m3`、直潭 `1,639,500 m3`）。[`reference_inflows.csv`](reference_inflows.csv) 提供 2019 年全年日入流以建立 Hanasaki 統計檔。

離線檢查兩份設定檔並執行全規則串聯基準：

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

- **期末蓄水量**：30 天 `rule_based.yaml` 結束時，翡翠為 `294,038,029 m3`、直潭為 `1,639,737 m3`（`PASS`）；`hybrid_llm.yaml` 結束時，翡翠為 `261,903,700 m3`、直潭為 `1,639,936 m3`（`PASS`）。
- **編輯入流與 YAML 規則**：修改 `inflows.csv` 後請執行 `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/multi_reservoir/inflows.csv` 更新 `inflow_source.sha256`；YAML 科學記號務必加上 `+`/`-`（如 `8.0e+6`）。
- **詳細設定指南**：水庫串聯欄位見[多水庫河網串接](../../docs/MULTI_RESERVOIR.zh-TW.md)，提示詞與規則設計見[操作規則與 LLM 設計](../../docs/AGENT_DESIGN.zh-TW.md)，單庫基準對照見[F.E. Walter 水庫案例](../fe_walter/README.zh-TW.md)。

## 梅雨鋒面模擬表現（2020 年 5–6 月）

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig6-xindian-results.png" alt="2020 年 5–6 月新店溪梅雨鋒面期間翡翠水庫蓄水量、放流量與直潭下游流量模擬與實測對照圖">
  <figcaption><strong>圖 6.</strong> 2020 年 5 月 7 日至 6 月 5 日梅雨鋒面期間，經濟部水利署實測資料與全規則串聯（Hanasaki + Hanasaki）及混合式 LLM 串聯（翡翠 LLM + 直潭 Hanasaki）之模擬對照。</figcaption>
</figure>

相較於全規則 Hanasaki 基準在梅雨強降雨期間持續蓄水而低估洪峰洩洪，混合式 LLM 串聯在上游翡翠水庫能主動因應入流暴漲調整放流，使翡翠庫容、翡翠放流與直潭下游流量歷線均更貼近水利署歷史觀測（逐項目標見 [`study/expected_scores.csv`](study/expected_scores.csv)）：

| 操作條件 | 翡翠蓄水量 KGE | 翡翠蓄水量 NSE | 翡翠蓄水量 RMSE (10⁶ m³) | 翡翠放流量 KGE / RMSE (m³/s) | 下游流量 KGE / RMSE (m³/s) |
| --- | --- | --- | --- | --- | --- |
| 全規則串聯（Hanasaki + Hanasaki） | `0.304` | `-0.186` | `10.99` | `0.459` / `23.19` | `0.824` / `21.94` |
| 混合式 LLM 串聯（翡翠 LLM + 直潭 Hanasaki） | `0.969` | `0.970` | `1.74` | `0.908` / `10.80` | `0.960` / `9.27` |

## 離線重現模擬分數

透過水庫水量平衡引擎與河道演算離線重播封存逐日放流序列（[`study/archived_releases.csv`](study/archived_releases.csv) 與全規則基準），並對照 [`study/observations.csv`](study/observations.csv) 重算所有評估分數：

```sh
python examples/multi_reservoir/study/replay.py --output runs/xindian-replay
```

各測站的 KGE、NSE 與 RMSE 指標將寫入 `runs/xindian-replay/scores.csv`。

## 使用本機 Ollama 執行即時推論

確認本機已安裝 `gemma4:12b` 並啟動 Ollama 伺服器：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Windows PowerShell

```powershell
ollama pull gemma4:12b
ollama serve
```

</div>
<div class="panel-card" markdown="1">

### macOS 或 Linux

```sh
ollama pull gemma4:12b
ollama serve
```

</div>
</div>

另開終端機執行混合式 LLM 串聯模擬（重跑時請更換 `run_id` 與未使用的 `output`）：

```sh
reservoir-experiment run examples/multi_reservoir/hybrid_llm.yaml --allow-network
reservoir-experiment verify runs/multi-reservoir-hybrid-llm
```

因不同硬體平台的浮點推論可能略有差異，若要精確重現上表分數請使用 `study/replay.py`。輸出解讀請見[結果判讀與水量平衡](../../docs/RESULTS_GUIDE.zh-TW.md)。
