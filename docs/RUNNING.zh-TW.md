# 檢查、準備、執行與驗證

<div class="hero-band" markdown="1">

每項 HydroReOpLLM 實驗皆依循同一套 CLI 流程：`check` →（耦合 HydroCNHS 專用 `prepare`）→ `run` → `verify`（以及供中斷續跑用的 `resume`）。

</div>

<figure class="figure-card">
  <img src="assets/simulation-stages.png" alt="從設定檔檢查、前處理準備、水庫操作到驗證的每日工作流程圖">
  <figcaption><strong>模擬生命週期。</strong> 離線驗證輸入、視需要檢視 HydroCNHS 入流、執行操作並驗證水量平衡。</figcaption>
</figure>

## CLI 生命週期與輸出目錄結構

```powershell
reservoir-experiment check path/to/experiment.yaml
reservoir-experiment run path/to/experiment.yaml
reservoir-experiment verify path/to/output
```

| 子指令 | 用途 | 網路呼叫 |
| --- | --- | --- |
| `check <config>` | 驗證水文綁定、拓樸、日期、提示詞與第 1 天提示詞預覽。 | `0` |
| `prepare <config>` | 僅限耦合 HydroCNHS：執行集水區模式與暖機期並輸出 `inflows.csv`。 | `0` |
| `run <config> [--allow-network]` | 準備入流（若為耦合）、執行水庫操作與演算並寫入結果。 | `0`（除非加上 `--allow-network`） |
| `verify <output> [--require-offline]` | 查核質量守恆、河道演算、因果時序與完整決策日誌。 | `0` |
| `resume <config> --from-run ... --output ... --run-id ...` | 重播中斷執行的已完成步驟並接續跑完剩餘步驟。 | 僅針對剩餘步驟 |

| 輸入方式 | 設定檔 `output` | 操作結果位置（`summary.json`、CSV） | 驗證指令 |
| --- | --- | --- | --- |
| 耦合 HydroCNHS（`v1`/`v2`） | 準備資料夾（`inflows.csv`、`hydrology*.json`） | `<output>/operation/` | `reservoir-experiment verify <output>` |
| 既有入流資料（`v1`/`v2`） | 操作資料夾 | `<output>/` | `reservoir-experiment verify <output>` |

<div class="callout callout-info" markdown="1">

**呼叫 LLM 前先檢查入流。** 先執行 `prepare` 可先繪圖或比對測站檢查 `inflows.csv`；之後執行 `run` 會自動沿用該入流檔，不需重跑 HydroCNHS。

</div>

## 即時模型呼叫與安全閘門

即時 LLM 推論必須滿足三項明確防護：

1. **CLI 旗標**：於 `reservoir-experiment run`（或 `resume`）傳入 `--allow-network`。
2. **案例就緒宣告**：實測或模擬入流案例須於 `case.json` / `reservoirs.yaml` 宣告 `"live_readiness": {"ready": true}`（合成測試案例自動就緒）。
3. **呼叫預算**：將 `max_calls` 設為至少 `llm_agents * steps`（含重試／備援餘裕）或 `null`。

## 續跑中斷的水庫操作

保持部分輸出資料夾完整不動，並以新的 `--run-id` 指向全新的 `--output` 資料夾：

```powershell
reservoir-experiment resume path/to/experiment.yaml `
  --from-run path/to/partial-operation `
  --output path/to/new-operation `
  --run-id NEW_RUN_ID
```

已完成的步驟會直接重播，不重複詢問 LLM；僅當剩餘步驟需要新模型呼叫時才加上 `--allow-network`。

## 重播已保存的逐日回覆

```powershell
llm-reservoir-daily --case-root path/to/case-directory `
  --case case.json `
  --responses responses.json `
  --output runs/replay
reservoir-experiment verify runs/replay --require-offline
```

若要重現 F.E. Walter 的 21 組基準模擬，請執行 `python examples/fe_walter/study/replay.py --output runs/walter-paper-replay`（[F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)）。接著請參閱[解讀執行結果](RESULTS_GUIDE.zh-TW.md)。
