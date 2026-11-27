# 結果判讀與水量平衡

<div class="hero-band" markdown="1">

先確認 `summary.json` 中的 `"status": "COMPLETED"`（耦合模式在 `<output>/operation/summary.json`；自備入流在 `<output>/summary.json`），再檢視蓄水軌跡、演算流量歷線、水量平衡與 LLM 決策日誌。

</div>

<figure class="figure-card">
  <img src="assets/diagrams/results-outputs-map.svg" alt="輸出目錄結構與各類 CSV／JSONL 結果檔案關聯圖">
  <figcaption><strong>輸出檔案關聯圖。</strong> 物理軌跡 CSV、流域水量平衡表與逐時間步決策／稽核日誌。</figcaption>
</figure>

## 輸出目錄結構

| 檔案或資料夾 | 產出時機 | 內容 |
| --- | --- | --- |
| `<output>/inflows.csv`、`hydrology*.json` | 耦合 `prepare` / `run` | 集水區區域入流（`m³/s`）與選用的 GWLF 狀態／診斷。 |
| `summary.json`、`progress.json` | 所有模擬 | 執行 `status`、期末蓄水量、`network_calls`、`fallback_used` 與 `serving_profiles`。 |
| `odd_llm_manifest.json` | 所有模擬 | 結構化 ODD+LLM 可重現性清單（涵蓋區塊 A–E 與輸出檔案 SHA-256 雜湊）。 |
| `reservoir_trajectory.csv` | 所有模擬 | 逐時間步入流、請求放流 vs. 實際放流、溢流與蓄水量。 |
| `network_flows.csv` | 所有模擬 | 每個入流口、匯流點與出口的區域入流及總演算流量。 |
| `network_balance.csv`、`reach_volume_trace.json` | 所有模擬 | 全流域質量平衡（`m³`）與滯留於河道演算延遲中的水量。 |
| `decisions.jsonl`、`physics.jsonl`、`audit.jsonl` | 所有模擬 | 逐時間步提示詞、回覆、物理轉移與稽核結果（以 `decision_id` 串聯）。 |
| `provider_attempts.jsonl`、`raw/` | LLM／追蹤模擬 | 模型呼叫嘗試紀錄與保存的提示詞／回覆原始內容。 |

## 物理模擬軌跡與演算流量

| 檔案 | 主要欄位 | 水文意義（`m³`、`m³/s`） |
| --- | --- | --- |
| `reservoir_trajectory.csv` | `date`/`timestamp`、`reservoir_id`、`inflow_cms`、`target_release_cms`、`controlled_release_cms`、`spill_cms`、`storage_start_m3`、`storage_end_m3`、`adjustments` | 比較 **`target_release_cms`**（策略請求）與 **`controlled_release_cms`**（受上下限與 `dead_storage_m3` 約束後的實際放流）及 **`spill_cms`**（超過 `capacity_m3` 的無控制溢流）。 |
| `network_flows.csv` | `date`/`timestamp`、`node`、`local_inflow_cms`、`routed_flow_cms` | 將下游測站的 `routed_flow_cms` 與實測河川流量歷線對照。 |
| `network_balance.csv` | `local_input_m3`、`outlet_output_m3`、`reservoir_storage_change_m3`、`channel_storage_change_m3`、`system_residual_m3` | 確認跨水庫與河段的質量守恆（`system_residual_m3` 趨近 `0`）。 |
| `reach_volume_trace.json` | 河段鍵名與時間步陣列 | 多步長演算延遲期間暫時滯留於河道的水量。 |

<div class="callout callout-info" markdown="1">

**放流截幅與執行失敗的區別。** 若 LLM 請求超出 `[minimum_release_cms, maximum_release_cms]` 或低於 `dead_storage_m3` 的放流量，水庫水量平衡引擎會將 `controlled_release_cms` 截幅、在 `adjustments` 記下旗標並繼續執行；Hanasaki 嚴格等價模式則會在水庫物理限制與規則衝突時報錯 `parity conflict`。

</div>

## 決策、稽核與模型紀錄

- **`decisions.jsonl`**：記錄確切的觀測狀態、讀取到的 `decision_information`、LLM／規則請求的 `action` 與 `serving_profile`，可用來診斷洪水或枯水期的放流決策原因。
- **`audit.jsonl`**：記錄診斷性質的 `PASS`、`WARN`、`FAIL` 或 `UNKNOWN`，不改寫流量。
- **`provider_attempts.jsonl` 與 `summary.json`**：查看 `fallback_used` 與 `serving_profiles`，確認每一步實際由哪一個模型服務產出。

## 驗證模擬輸出

```powershell
reservoir-experiment verify path/to/output --require-offline
```

驗證即時 LLM 模擬時請省略 `--require-offline`。`verify` 會在不重跑水文、不連線模型伺服器的情況下，檢查質量平衡、河道摺積演算、水情時間戳記與完整日誌。

## ODD+LLM 可重現性報告匯出

每次模擬完成後皆會自動產出 `odd_llm_manifest.json`，與物理軌跡及決策日誌並存。可執行以下指令，由任何輸出資料夾匯出可附於論文的 ODD+LLM Markdown 報告：

```powershell
reservoir-experiment export-odd path/to/output --markdown-out ODD_LLM_REPORT.md
```

清單與報告完整收錄五項標準化可重現性區塊：

- **區塊 A — 認知架構（Cognitive Architecture）**：代理人型態與策略、工作記憶（`history_steps`）、長期操作知識（`dkp.md`、運用規線）、不洩漏未來水情的資訊設定與物理行動邊界。
- **區塊 B — 代理人身分與提示詞（Identity）**：角色設定與人設框架、提示詞範本 ID／版本、`prompt_sha256` 雜湊與鎖定之原始檔清單。
- **區塊 C — 推論組態（Inference Configuration）**：確切模型識別碼、服務端點、Ollama 伺服器版本、模型快照 SHA-256 摘要與量化格式、雲端實測模型版本／`system_fingerprint`、解碼超參數（`temperature`、隨機種子 `seed`、`max_tokens`、`num_ctx`、`think`）、重試／備援鏈與關鍵 Python／HydroCNHS 相依套件版本。
- **區塊 D — 行為子模式（Signature、Binding 與 Resolution）**：觀測欄位與 JSON 輸出 Schema／解析器（`Signature`）、提示詞變數與上下文／知識掛鉤（`Binding`），以及重試、備援、物理截幅、溢洪與稽核實測遙測（`Resolution`）。
- **區塊 E — 驗證與稽核（Validation）**：水量平衡殘差、離線 `verify` 查核狀態、輸出與追蹤檔之 SHA-256 雜湊與離線重播能力。
