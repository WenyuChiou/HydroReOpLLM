# 多水庫串聯案例：新店溪翡翠水庫 → 直潭壩（Repository 專屬範例）

<div class="hero-band" markdown="1">

本案例為 **GitHub 程式碼庫（Repository）專用的多水庫示範範例**（不收錄於論文文章中，論文主體實驗為單一水庫 F.E. Walter），以台灣新店溪 **2 座水庫串聯系統**（**翡翠水庫 `feitsui`** → **直潭壩 `zhitan`** → **`xindian_outlet`**）模擬 **2020 年 5 月 7 日 – 6 月 5 日**（30 天）梅雨鋒面期間操作。本範例已完全對齊 F.E. Walter 架構：採用 **4 子集水區 HydroCNHS（`GWLF` + `Lohmann`）水文率定與驗證（C&V）**，並將 LLM 操作員統一為**結構化決策鏈 JSON 提示詞**。

</div>

## 研究區域、HydroCNHS 水文模型與 C&V 驗證

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig5-xindian-study-area.png" alt="新店溪雙水庫串聯研究區域：子集水區 U1–U2 與 D1–D2、水利署測站 10205 與 10212、翡翠水庫與直潭壩位置圖">
  <figcaption><strong>圖 5.</strong> 台灣新店溪<strong>雙水庫串聯系統（2 座水庫串聯）</strong>、子集水區（<code>U1–U2</code> 匯入 <code>feitsui_local</code>，30,300 公頃；<code>D1–D2</code> 匯入 <code>zhitan_local</code>，37,680 公頃）、水利署測站（<code>10205</code>、<code>10212</code>）與年均降雨分布（WorldClim 2.1）：<strong>1. 翡翠水庫</strong>（<code>335,505,000 m³</code>，<code>0–500 m³/s</code>）經率定之 Lohmann 單位歷線（<code>[0.857904, 0.142054, 4.2e-05]</code>）銜接 <strong>2. 直潭壩</strong>（<code>1,918,900 m³</code>，<code>0–800 m³/s</code>），再經 <code>[1.0]</code> 流至 <code>xindian_outlet</code>。</figcaption>
</figure>

本範例的區域增量入流（[`inflows.csv`](inflows.csv)，`data_kind: simulated_local_inflow`）由 4 子集水區 HydroCNHS 模式（[`hydrology/xindian_catchments.yaml`](hydrology/xindian_catchments.yaml)、[`hydrology/hydrology.yaml`](hydrology/hydrology.yaml)）驅動逐日 ERA5 氣象資料（[`hydrology/forcing.csv`](hydrology/forcing.csv)，含 2018 年暖機期）產生，並對照台灣經濟部水利署（WRA）歷史觀測資料完成率定與驗證（[`hydrology/cv_summary.json`](hydrology/cv_summary.json)）：

| 水文階段 | 期間 | 天數 | KGE | NSE | RMSE (m³/s) |
| --- | --- | --- | --- | --- | --- |
| 率定期 Calibration（`U1–U2`，對照 WRA `10205`） | `2019-01-01`–`2019-08-31` | 243 | `0.699` | `0.476` | `20.39` |
| 驗證期 V1（`U1–U2`，對照 WRA `10205`） | `2019-09-01`–`2019-12-31` | 122 | `0.572` | `0.656` | `37.90` |
| 驗證期 V2（`U1–U2`，2020 梅雨事件 WRA `10205`） | `2020-05-05`–`2020-06-05` | 32 | `0.769` | `0.638` | `27.87` |
| 驗證期 V2（`D1–D2` 區間入流 / 直潭組合下游流量） | `2020-05-05`–`2020-06-05` | 32 / 30 | `0.396` / `0.662` | `-0.441` / `0.330` | `41.10` / `42.58` |

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 情境一：全規則串聯（Rule-based）

- **設定檔**：[`rule_based.yaml`](rule_based.yaml)
- **方法**：上下游皆採 Hanasaki 滯洪規則（`strategy: benchmark`，α = 0.85），分別依 2019 年參考統計 [`feitsui_statistics.json`](feitsui_statistics.json) 與 [`zhitan_statistics.json`](zhitan_statistics.json) 離線執行。
- **期末蓄水量**：翡翠水庫結束於 `282,228,494 m3`、直潭壩結束於 `1,639,724 m3`（`PASS`）。

</div>
<div class="panel-card" markdown="1">

### 情境二：混合式 LLM 串聯（Hybrid LLM）

- **設定檔**：[`hybrid_llm.yaml`](hybrid_llm.yaml)
- **方法**：上游翡翠水庫（`feitsui_operator`）由 `gemma4:12b` 操作（`strategy: xindian_study`，與 F.E. Walter 一致的結構化決策鏈 JSON [`study/response_schemas.json`](study/response_schemas.json) 與 [`study/formatter.py`](study/formatter.py)），搭配下游直潭壩（`zhitan_operator`）採用 Hanasaki 規則。
- **提示詞**：[System prompt](prompts/feitsui.system.txt) · [第 1 天 User 範例](prompts/feitsui.user.txt)。
- **期末蓄水量**：翡翠水庫結束於 `248,759,154 m3`、直潭壩結束於 `1,269,582 m3`（`PASS`）。

</div>
</div>

## 設定檔與快速檢查

兩組條件共用 [`case.json`](case.json) 與 [`inflows.csv`](inflows.csv)（含 2018–2020 ERA5 驅動之 HydroCNHS 模擬區域入流，初始有效蓄水為翡翠 `253,810,100 m3`、直潭 `1,639,500 m3`）。離線檢查兩份設定檔並執行全規則串聯基準：

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

- **編輯入流與 YAML 規則**：修改 `inflows.csv` 後請執行 `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/multi_reservoir/inflows.csv` 更新 `inflow_source.sha256`；YAML 科學記號務必加上 `+`/`-`（如 `8.0e+6`）。
- **詳細設定指南**：水庫串聯欄位見[多水庫河網串接](../../docs/MULTI_RESERVOIR.zh-TW.md)，提示詞與規則設計見[操作規則與 LLM 設計](../../docs/AGENT_DESIGN.zh-TW.md)，論文單庫基準見[F.E. Walter 水庫案例](../fe_walter/README.zh-TW.md)。

## 梅雨鋒面模擬表現（2020 年 5–6 月）

<figure class="figure-card">
  <img src="../../docs/assets/figures/fig6-xindian-results.png" alt="統一為 F.E. Walter 同款結構化提示詞與 HydroCNHS 模擬入流後之 2020 年 5–6 月翡翠蓄水量、放流量與直潭下游流量對照圖">
  <figcaption><strong>圖 6.</strong> 2020 年 5 月 7 日至 6 月 5 日梅雨鋒面期間，台灣經濟部水利署實測資料與全規則串聯（Hanasaki + Hanasaki）及混合式 LLM 串聯（翡翠統一結構化目標提示詞、無硬編碼門檻）之模擬對照。</figcaption>
</figure>

改用無硬編碼洪峰門檻、僅給定汛前目標庫容（`250 × 10⁶ m³`）的統一提示詞後，`gemma4:12b` 嚴格追蹤目標水位（結束於 `248.8 × 10⁶ m³`）而在 5/22–5/24 暴雨洪峰選擇將大流量直接下洩，全規則 Hanasaki 則能蓄洪削峰至 `282.2 × 10⁶ m³`，清楚呈現缺乏專屬防洪操作知識下 LLM 的極端洪峰行為（逐項指標見 [`study/expected_scores.csv`](study/expected_scores.csv)）：

| 操作條件 | 翡翠蓄水量 KGE | 翡翠蓄水量 NSE | 翡翠蓄水量 RMSE (10⁶ m³) | 翡翠放流量 KGE / RMSE (m³/s) | 下游流量 KGE / RMSE (m³/s) |
| --- | --- | --- | --- | --- | --- |
| 全規則串聯（Hanasaki + Hanasaki） | `0.521` | `0.452` | `7.47` | `0.377` / `26.01` | `0.504` / `54.77` |
| 混合式 LLM 串聯（翡翠 LLM + 直潭 Hanasaki） | `-0.710` | `-0.739` | `13.30` | `-0.163` / `44.55` | `0.028` / `79.73` |

## 離線重現或使用本機 Ollama 即時重跑

透過水庫水量平衡引擎與河道演算離線重播封存放流序列（[`study/archived_releases.csv`](study/archived_releases.csv)），或於本機啟動 `ollama serve`（需已下載 `gemma4:12b`）重新執行即時模擬：

```sh
python examples/multi_reservoir/study/replay.py --output runs/xindian-replay
reservoir-experiment run examples/multi_reservoir/hybrid_llm.yaml --allow-network
```

輸出判讀請見[結果判讀與水量平衡](../../docs/RESULTS_GUIDE.zh-TW.md)。
