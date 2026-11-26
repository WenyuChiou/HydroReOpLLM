# 檢查、準備、執行與驗證

<div class="hero-band" markdown="1">

每一項 HydroReOpLLM 實驗都採用同一套一致的命令列工作流程：`check` →（耦合 HydroCNHS 專用的 `prepare`）→ `run` → `verify`（加上供長時間即時執行中斷時使用的 `resume`）。

</div>

<figure class="figure-card">
  <img src="assets/simulation-stages.png" alt="從設定檔檢查、前處理準備、水庫操作到驗證的每日工作流程圖">
  <figcaption><strong>模擬生命週期。</strong> 先於離線狀態驗證設定，視需要檢視預先產出的 HydroCNHS 入流量，接著執行水庫操作，最後核對水量平衡與決策紀錄。</figcaption>
</figure>

## CLI 生命週期與輸出目錄結構

於專案根目錄或工作目錄執行標準的三段式指令序列：

```powershell
reservoir-experiment check path/to/experiment.yaml
reservoir-experiment run path/to/experiment.yaml
reservoir-experiment verify path/to/output
```

| 子指令 | 用途 | 寫入的輸出 | 網路呼叫次數 |
| --- | --- | --- | --- |
| `check <config>` | 驗證水文綁定、水庫拓樸、日期、提示詞，並產出第 1 天提示詞預覽。 | 無 | `0` |
| `prepare <config>` | 僅限耦合 HydroCNHS：執行集水區降雨－逕流＋暖機期模擬並寫出 `inflows.csv`。 | 準備目錄 | `0` |
| `run <config> [--allow-network]` | 視需要先行準備入流（耦合模式），再執行操作員與河道演算並保存模擬軌跡。 | 全新 `<output>` | `0`（除非傳入 `--allow-network`） |
| `verify <output> [--require-offline]` | 查核已保存的水量平衡、河道演算守恆、因果時序與追蹤完整性。 | 無 | `0` |
| `resume <config> --from-run ... --output ... --run-id ...` | 重播中斷執行的已完成步驟，並將剩餘步驟接續寫入全新目錄。 | 全新 `--output` | 僅針對剩餘步驟 |

水庫操作檔案寫入的位置取決於您的水文輸入模式：

| 輸入模式 | 設定檔的 `output` | 操作檔案位置（`summary.json`、CSV） | 驗證指令 |
| --- | --- | --- | --- |
| 耦合 HydroCNHS（`v1`/`v2`） | 準備目錄（`inflows.csv`、`hydrology*.json`） | `<output>/operation/` | `reservoir-experiment verify <output>`（或 `<output>/operation`） |
| 既有入流資料（`v1`/`v2`） | 操作目錄 | `<output>/` | `reservoir-experiment verify <output>` |

<div class="callout callout-info" markdown="1">

**操作前先檢視集水區入流。** 若想在呼叫 LLM 之前先繪圖或對照測站檢查 `inflows.csv`，請先執行 `prepare`。之後執行 `run` 時會自動驗證並沿用這份已準備好的 `inflows.csv`，無須重跑 HydroCNHS。

</div>

## 即時模型呼叫與安全閘門

啟用即時 LLM 推論必須同時滿足三項明確防護條件，避免誤觸非預期的 API 呼叫或帳單費用：

1. **CLI 授權旗標**：於執行 `reservoir-experiment run`（或 `resume`）時傳入 `--allow-network`。
2. **案例就緒宣告**：實測或模擬入流案例（`observed_local_inflow` 或 `simulated_local_inflow`）必須在 `case.json` / `reservoirs.yaml` 中加入 `"live_readiness": {"ready": true}`。合成教學範本無須此欄位即視為就緒。
3. **呼叫預算上限（`max_calls`）**：設為至少 `llm_agents * steps`（外加重試／備援餘裕），或明確設為 `null` 代表不設上限。

## 續跑中斷的水庫操作

若多年期 LLM 模擬因網路中斷或電腦重開機而中途停止，請保持原本的部分輸出資料夾完整不動，並以新的 `--run-id` 將續跑結果寫入全新的 `--output` 目錄：

```powershell
reservoir-experiment resume path/to/experiment.yaml `
  --from-run path/to/partial-operation `
  --output path/to/new-operation `
  --run-id NEW_RUN_ID
```

已完成的時間步與已保存的模型回覆會完全一致地重播，不會重複詢問 LLM；僅當剩餘未完成步驟需要即時呼叫模型時才加上 `--allow-network`。

## 重播已保存的逐日回覆

若要透過水庫物理與河道演算引擎離線重播封存的逐日放流紀錄：

```powershell
llm-reservoir-daily --case-root path/to/case-directory `
  --case case.json `
  --responses responses.json `
  --output runs/replay
reservoir-experiment verify runs/replay --require-offline
```

若要重現 F.E. Walter 的 21 組基準模擬，請執行 `python examples/fe_walter/study/replay.py --output runs/walter-paper-replay`（詳見 [F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)）。接著請繼續閱讀[解讀執行結果](RESULTS_GUIDE.zh-TW.md)。
