# F.E. Walter Dam 案例研究

<div class="hero-band" markdown="1">

本基準測試於 **2021 年 1 月 1 日 – 2025 年 12 月 31 日**（`1,826` 天）在相同的 HydroCNHS 演算系統上評估 **F.E. Walter Dam**（賓夕法尼亞州 Lehigh River 流域）的三種操作條件：**Rule-based**（Hanasaki）、**Without operational knowledge**（`seasonal_target.yaml`）與 **With operational knowledge**（`dkp.yaml`）。

</div>

## 研究區域與基準設計

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig2-study-area.png" alt="F.E. Walter Dam 研究區域、水文測站與下游河道演算網路圖">
  <figcaption><strong>圖 2.</strong> F.E. Walter Dam 流域與下游河道演算網路，連接水庫出流至 USGS <code>01447800</code>（White Haven）與 USGS <code>01449000</code>（Lehighton）。</figcaption>
</figure>

<div class="panel-grid panel-grid-3" markdown="1">
<div class="panel-card" markdown="1">

### 情境一：Rule-based（Hanasaki 規則）

- **設定檔**：[`rule_based.yaml`](rule_based.yaml)
- **方法**：Hanasaki 滯洪規則（`strategy: hanasaki`，α = 0.85），使用 [1996–2015 年入流統計](rule_statistics.json)與[規則物理案例](rule_case.json)。
- **網路呼叫**：`0` 次（離線）。

</div>
<div class="panel-card" markdown="1">

### 情境二：Without operational knowledge（無操作知識）

- **設定檔**：[`seasonal_target.yaml`](seasonal_target.yaml)
- **方法**：`gemma4:12b`，僅提供水庫水位、季節目標水位與前兩日放流歷史。
- **提示詞**：[System](prompts/seasonal_target.system.txt) · [第 1 天 User](prompts/seasonal_target.user.txt)。

</div>
<div class="panel-card" markdown="1">

### 情境三：With operational knowledge（具操作知識）

- **設定檔**：[`dkp.yaml`](dkp.yaml)
- **方法**：`gemma4:12b`，從 [`dkp.md`](dkp.md) 檢索結構化操作規則，並於 JSON 中引用 `rules_applied`。
- **提示詞**：[System](prompts/dkp.system.txt) · [第 1 天 User](prompts/dkp.user.txt)。

</div>
</div>

## 設定檔與提示詞檢視

三種條件共用 2021–2025 年模擬區域入流（[`inflows.csv`](inflows.csv)），預設先跑 7 天教學視窗（`2021-01-01`–`2021-01-07`），加上 `--full` 即可執行全期 `1,826` 天。兩組 LLM 條件共用 [`case.json`](case.json)、[`study/elevation_storage.csv`](study/elevation_storage.csv)、[`study/response_schemas.json`](study/response_schemas.json) 與 [`study/formatter.py`](study/formatter.py)（將水位格式化為 `ft NGVD29`、入流為 `cfs`/`acre-ft` 並列出兩日放流歷史）。

於離線狀態（`0` 次呼叫）檢查全部三份設定檔：

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

可搭配 [F.E. Walter 教學](../../tutorials/README.zh-TW.md)與[操作員與 LLM 代理人設計](../../docs/AGENT_DESIGN.zh-TW.md)逐步學習 7 天設計流程。

## 日尺度與季節尺度表現（2021–2025）

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig3-daily-2021-2025.png" alt="2021-2025 年日尺度 F.E. Walter 水庫水位、放流量與下游流量模擬與實測對照圖">
  <figcaption><strong>圖 3.</strong> 2021–2025 年逐日水位、放流量與下游流量對照，比較 USGS 觀測值與 Rule-based、Without operational knowledge 及 With operational knowledge（各 10 組 seed）。</figcaption>
</figure>

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig4-annual-cycle.png" alt="F.E. Walter 水庫水位、放流量與下游流量之多年平均季節週期圖">
  <figcaption><strong>圖 4.</strong> 三種條件的多年平均季節週期，顯示 With operational knowledge 相較於 Without operational knowledge 與 Rule-based，能更準確重現春季回蓄（1,370 ft NGVD29）與秋季洩降（1,300 ft NGVD29）。</figcaption>
</figure>

針對全部 21 組封存模擬（`1` 組 Rule-based + `10` 組 Without operational knowledge + `10` 組 With operational knowledge）相對於 USGS `01447780`、`01447800` 與 `01449000` 之評估分數（[`study/expected_scores.csv`](study/expected_scores.csv)）：

| 研究條件 | 模擬組數 | 水庫水位 KGE（中位數） | 水庫水位 NSE（中位數） | 水庫水位 RMSE（中位數） | 水庫放流量 KGE（中位數） | 下游流量 KGE（中位數） |
| --- | --- | --- | --- | --- | --- | --- |
| Rule-based（Hanasaki，α = 0.85） | `1` | `0.077` | — | `96.21 ft` | `0.640` | `0.815` |
| Without operational knowledge | `10` | `0.806` | `0.514` | `20.85 ft` | `0.688` | `0.830` |
| With operational knowledge | `10` | `0.858` | `0.711` | `16.07 ft` | `0.618` | `0.832` |

## 離線重現論文分數

以**零次** LLM 呼叫透過主機物理與河道演算重播全部 21 組封存逐日放流序列（`study/archived_releases.csv` + Rule-based 基準）：

```sh
python examples/fe_walter/study/replay.py --output runs/walter-paper-replay
```

檢視 `runs/walter-paper-replay/scores.csv` 即可取得全數 63 筆評估分數與終端機輸出的 `water_level_medians`。

## 使用研究模型進行新的推論執行

即時 LLM 重現採用 **Ollama 0.40.6**，並透過 [`study/model.py`](study/model.py) 下載鎖定的 `gemma4:12b` 環境（約 7.6 GB）：

```sh
python examples/fe_walter/study/model.py .walter-ollama
```

於另一個終端機啟動專用 Ollama 伺服器：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Windows PowerShell

```powershell
$env:OLLAMA_MODELS = (Resolve-Path .walter-ollama).Path
$env:OLLAMA_HOST = "127.0.0.1:11446"
ollama serve
```

</div>
<div class="panel-card" markdown="1">

### macOS 或 Linux

```sh
OLLAMA_MODELS="$PWD/.walter-ollama" OLLAMA_HOST=127.0.0.1:11446 ollama serve
```

</div>
</div>

可先跑 7 天教學視窗，或加上 `--full` 執行全期 `1,826` 天（每個 `--seed 1..10` 請指定全新 `--output`）：

```sh
python examples/fe_walter/study/run.py rule_based --full --output runs/walter-rule
python examples/fe_walter/study/run.py seasonal_target --full --seed 3 --ollama-port 11446 --output runs/walter-without-s3 --allow-network
python examples/fe_walter/study/run.py dkp --full --seed 3 --ollama-port 11446 --output runs/walter-with-s3 --allow-network
```

因不同硬體平台的浮點推論可能略有差異，若要完全一致地重現已發表分數，請使用上方的 `replay.py`。輸出解讀請見[解讀執行結果](../../docs/RESULTS_GUIDE.zh-TW.md)。
