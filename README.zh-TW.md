# HydroReOpLLM

[English](README.md) | [繁體中文](README.zh-TW.md)

[![使用手冊](docs/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/)

![HydroReOpLLM：結合 LLM 水庫決策代理的人水耦合模擬](docs/figures/hydroopslm-cover.png)

HydroReOpLLM 是使用大型語言模型（LLM）研究水庫操作的 Python 套件，
將可設定的水庫操作員接到 [HydroCNHS](https://github.com/cylin928/HydroCNHS) 水文模擬。
使用 YAML 描述自己的流域、單一水庫或水庫網路，以及各操作員能取得的資訊。

水文模型提供入流，操作員提出放水要求；水庫物理計算套用限制、更新庫容與溢流，
再把總出流 routing 到下游。每座水庫保留獨立的狀態與決策歷史。

## 提供的功能

- **單水庫與水庫網路：**在共用水文輸入及水庫物理計算下，比較 Rule-based 與 LLM 操作員。
- **可設定的模型接口：**支援 Ollama、OpenAI-compatible、OpenAI、Anthropic 與 Gemini，
  並明確設定模型參數、retry 與 fallback。
- **研究案例自己的決策設計：**提供 system/user prompt、操作知識、觀測及決策當時可取得的其他資訊。
- **可追查的結果：**保存要求與實際放水、溢流、庫容、下游流量、reason、原始回覆、runtime 及服務回報的 token 用量。
  設定檢查、回覆驗證、水量守恆驗證與操作規則稽核分別處理實驗的不同部分。

主要流程以 Daily 為主；[時間尺度範例](examples/time_scales/README.md)也提供 Hourly 與明確步長的設定。
新的流域仍需要適當的輸入資料、水庫特性，以及水文模型的校正與驗證。

## 安裝

使用 **Python 3.12**。取得 repository 並建立虛擬環境：

```bash
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m venv .venv
```

Windows PowerShell 使用 `.venv\Scripts\Activate.ps1` 啟用；Linux/macOS 使用
`source .venv/bin/activate`。接著在 repository 根目錄安裝：

```bash
python -m pip install -e . -c environment/requirements-bundled.txt
reservoir-experiment --help
```

選配依賴請見[安裝說明](https://wenyuchiou.github.io/HydroReOpLLM/docs/GETTING_STARTED.html)。
安裝不會下載或啟動 LLM。目前是研究候選包，尚未提供 PyPI 安裝。

## 執行第一個範例

在 repository 根目錄執行小型單水庫範例。它使用已提供的入流與確定性的操作員，
不需要 API key 或模型服務：

```bash
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single
```

結果存於 `runs/daily-single`，先查看 `summary.json`、`reservoir_trajectory.csv` 與
`network_flows.csv`；其餘紀錄請見[結果與決策紀錄](https://wenyuchiou.github.io/HydroReOpLLM/docs/RESULTS_GUIDE.html)。
另一個實驗請使用新的執行名稱與輸出位置。

## 範例

| 範例 | 說明 | 輸入與操作員 |
|---|---|---|
| [單水庫與串聯](examples/daily_offline/README.md) | 從第一次執行，到三座水庫的串聯 | 小型已備妥入流；不需模型服務 |
| [多水庫](examples/multiple_reservoirs/README.md) | 氣象驅動水文與各壩獨立操作員 | 預設 Rule-based，另有可選的 LLM 設定 |
| [時間尺度](examples/time_scales/README.md) | Daily、Hourly 與明確步長的設定 | 採用非 LLM 操作員的小型設定 |
| [F.E. Walter](examples/fe_walter/README.md) | 比較 Rule-based 與 LLM 方法的研究案例 | 依[案例指南](https://wenyuchiou.github.io/HydroReOpLLM/docs/CASE_STUDIES.html)選擇 2021–2025 已備妥入流，或 2016 氣象驅動設定 |
| [F.E. Walter 延伸至 Bethlehem](examples/fe_walter_bethlehem/README.zh-TW.md) | 獨立的下游水位資料準備範例 | 歷史 rating、測站口徑與 C&V 需求；尚未提供模擬 |

也可查看[範例目錄](examples/README.zh-TW.md)與 [Notebook 教學](tutorials/README.zh-TW.md)。
`examples/` 放可執行研究及明確標示的資料準備範例，`templates/` 放起始設定。

## 設定自己的研究案例

[使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/)依下列順序介紹設定：

1. 設定模擬日期、執行名稱與輸出位置。
2. 接入已備妥入流，或自己的水文模型與氣象資料。
3. 定義水庫曲線、初始狀態、出流限制與河道連接。
4. 選擇各操作員、模型、prompt、可用資訊及稽核準則。
5. 檢查、執行並閱讀保存的結果。

從[設定指南](https://wenyuchiou.github.io/HydroReOpLLM/docs/INPUT_OUTPUT.html)與
[耦合設定範本](templates/coupled/README.md)開始。氣象驅動流程使用
`check → prepare → run → verify`；已備妥入流使用 `check → run → verify`。
案例自己的規則、測站名稱與知識放在研究檔案或 extension；多數設定不必修改核心模組。

查閱程式可從[專案結構](docs/CODE_STRUCTURE.md)與
[API 說明](https://wenyuchiou.github.io/HydroReOpLLM/docs/API_REFERENCE.html)進入。
套件檢查軟體與數值的一致性；新流域模型或操作策略的有效性仍需另外評估。

## 引用與授權

報告實驗時請記錄專案 revision，依[引用說明](docs/REFERENCE.md)引用本專案及 HydroCNHS。
主專案授權尚待確定；隨附依賴保留各自的[授權與來源](THIRD_PARTY_NOTICES.md)。
