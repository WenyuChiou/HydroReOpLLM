# 關鍵設定檔總表（1 對 1 對照）

<div class="hero-band" markdown="1">

每項 HydroReOpLLM 實驗都是從一份主設定檔（YAML）出發，串聯起 **4 組關鍵設定檔**。建議先參考[單一水庫案例（F.E. Walter）](../examples/fe_walter/README.zh-TW.md)或[多水庫串聯案例（新店溪）](../examples/multi_reservoir/README.zh-TW.md)，再對照下表替換成自己的流域。

</div>

## 套用到專屬流域的最小起步檔案

- **純規則基準（只要 3 個檔）：** `<實驗名>.yaml`（如 `rule_based.yaml`）＋ `case.json` ＋ `inflows.csv` *（使用 Hanasaki 規則時再加 `*_statistics.json`）*。
- **標準 SI 單位 LLM 模擬（只要 5 個檔）：** 上述 3 個檔 ＋ `prompts/system.txt` ＋ `prompts/user.txt` *（直接回傳 `release_cms`，**完全免寫 Python、也不必建 `study/` 資料夾**）*。

<figure class="figure-card">
  <img src="assets/diagrams/package-structure.svg" alt="HydroReOpLLM 4 組關鍵設定檔關聯圖">
  <figcaption><strong>四大關鍵設定檔架構。</strong> 所有相對路徑一律相對於「宣告該路徑的 YAML 檔」解析。</figcaption>
</figure>

## 範例真實檔名 1 對 1 對照表

| 設定層級 | 範例中的真實檔名（及模組化 `v2` 拆檔名） | 性質 | 這個檔案負責什麼 | 詳細設定章節 |
| --- | --- | --- | --- | --- |
| **1. 主實驗入口** | `rule_based.yaml`、`seasonal_target.yaml`、`dkp.yaml`、`hybrid_llm.yaml` *（或 `experiment.yaml`）* | **必備** | 設定 `run_id`、模擬起訖日、串接第 2–4 層檔案、`models`、`agents`、`max_calls` 與 `output`。 | 下方「頂層設定鍵」 |
| **2. 水文與入流** | `inflows.csv` | 自備入流 | 各非水庫節點每日區域增量逕流（`date,node,local_inflow_cms`）。 | [入流與 HydroCNHS 設定](HYDROLOGY_SETUP.zh-TW.md) |
| | `hydrology/hydrology.yaml` ＋ `xindian_catchments.yaml` ＋ `forcing.csv(.gz)` | 耦合專用 | 連接 HydroCNHS 集水區模式（`GWLF`/`ABCD` + `Lohmann`）、氣象資料與 `inflow_bindings`。 | [入流與 HydroCNHS 設定](HYDROLOGY_SETUP.zh-TW.md) |
| **3. 水庫與河網** | `case.json` *（及規則用 `rule_case.json`、拆檔用 `reservoirs.yaml`）* | **必備** | 水庫滿庫庫容、呆庫容、放流上下限 `[min, max]` 與河段 `unit_hydrograph` 延遲權重。 | [水庫物理與河網串接](MULTI_RESERVOIR.zh-TW.md) |
| **4. 決策 Agent 與服務** | `rule_statistics.json`、`feitsui_statistics.json`、`zhitan_statistics.json` | Hanasaki 必備 | Hanasaki 規則所需的長年平均入流量統計。 | [操作規則與 LLM 提示詞](AGENT_DESIGN.zh-TW.md) |
| | `prompts/*.system.txt`、`prompts/*.user.txt`、選用 `dkp.md` | LLM 必備 | 系統角色目標、每日填空提示詞範本，以及選用的水庫運用要點（`dkp.md`）。 | [操作規則與 LLM 提示詞](AGENT_DESIGN.zh-TW.md) |
| | `information.yaml` *（選用）* 與 `models:`／`models.yaml` | 選用 / LLM | 不洩漏未來水情之測站預報設定，以及 Ollama／雲端模型參數（`seed`、`temperature`）。 | [水情測站與預報](INFORMATION.zh-TW.md) · [模型服務連線](MODEL_PROVIDERS.zh-TW.md) |

<div class="callout callout-info" markdown="1">

**關於範例資料夾中的 `study/` 目錄：** `examples/*/study/`（例如 `formatter.py`、`response_schemas.json`、`archived_releases.csv`、`replay.py`）僅供範例重播論文數據或進行英制單位（`ft`/`cfs`）轉換；自建標準 SI 單位（`m3`、`m3/s`）流域**完全不需要 `study/`**。

</div>

## 設定版本與 `{file: ...}` 拆檔寫法

| `schema_version` | 入流方式 | 可用 `{file: ...}` 拆檔的區段 | 適用情境 |
| --- | --- | --- | --- |
| `llm-reservoir-experiment.v1` | 自備 `inflows.csv` | 內嵌 | 單庫 F.E. Walter 與多庫新店溪標準範例。 |
| `llm-reservoir-experiment.v2` | 自備 `inflows.csv` | `models`、`agents`、`auditors`、`extensions`、`information` | 較大型之分檔自備入流實驗。 |
| `hydroops-coupled-simulation.v1` | 耦合 HydroCNHS | 內嵌 | 單檔式集水區＋水庫耦合模擬。 |
| `hydroops-coupled-simulation.v2` | 耦合 HydroCNHS | `hydrology`、`models`、`agents`、`auditors`、`extensions`、`information` | 建議用於多水庫＋水文模式之模組化專案。 |

## 頂層 YAML 關鍵欄位與防呆提醒

| 欄位 | 必填 | 用途 |
| --- | --- | --- |
| `schema_version`、`run_id`、`output`、`case` | **是** | 設定版本、唯一識別碼、尚未存在的輸出資料夾與物理案例檔。 |
| `start_date`、`end_date` *（或 `start_time`/`end_time`/`time`）* | **是** | 加引號 `YYYY-MM-DD` 含括日期（或固定次日時距之 UTC 時間）。 |
| `hydrology` | 耦合 | 連結 `hydrology.yaml`，先執行 HydroCNHS 產出區域入流。 |
| `agents` | **是** | 為每座受控水庫指派 `rule_based`、`llm` 或 `offline` 操作員。 |
| `models` | LLM | 具名 Ollama 或雲端服務組態（`seed`、`temperature`、`max_tokens`、逾時）。 |
| `information`、`auditors`、`outcome_checks`、`extensions` | 否 | 測站預報、放流檢查與自訂 Python 規則擴充。 |
| `max_calls` | 建議 | LLM 呼叫次數上限（規則／離線設 `0`；即時推論須 `>= llm_agents * steps`）。 |

<div class="callout callout-warn" markdown="1">

**兩條必記 YAML 規則：** 同區段不可有重複鍵名；科學記號**一定要寫 `+` 或 `-`**（寫 `8.0e+6` 或 `8000000.0`，不可寫 `8.0e6`）。修改後隨時執行 `reservoir-experiment check <設定檔.yaml>` 離線檢查。

</div>
