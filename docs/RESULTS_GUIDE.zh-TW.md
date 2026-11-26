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
