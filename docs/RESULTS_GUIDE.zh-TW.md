# 解讀執行結果

<div class="hero-band" markdown="1">

請先開啟 `summary.json`（耦合模式位於 `<output>/operation/summary.json`；既有入流模式直接位於 `<output>/summary.json`），確認 `"status": "COMPLETED"`。在判讀水庫操作績效前，請依序檢視實體 CSV 數據表與逐時間步 JSONL 來源追蹤紀錄。

</div>

<figure class="figure-card">
  <img src="assets/diagrams/results-outputs-map.svg" alt="輸出目錄結構與各類 CSV／JSONL 結果檔案關聯圖">
  <figcaption><strong>輸出產物關聯圖。</strong> 物理軌跡與水量平衡表格皆可透過 <code>decision_id</code> 與決策、稽核及原始追蹤日誌精確串聯。</figcaption>
</figure>

## 輸出目錄結構

| 路徑 | 產出時機 | 內容說明 |
| --- | --- | --- |
| `<output>/inflows.csv`、`preparation.json`、`hydrology*.json` | 耦合模式 `prepare` / `run` | 鎖定版本的 HydroCNHS 入流量、前處理簽章，以及選用的 GWLF 診斷／狀態紀錄。 |
| `summary.json` 與 `progress.json` | 所有模擬 | 執行 `status`、期末蓄水量、`network_calls`、`fallback_used`、`serving_profiles` 與步數計數器。 |
| `experiment.json` | 所有模擬 | 已凍結的水系結構、入流資料、套件與 HydroCNHS SHA-256 雜湊值、資訊目錄及來源追蹤。 |
| `reservoir_trajectory.csv`、`network_flows.csv`、`network_balance.csv` | 所有模擬 | 時間序列水庫狀態、河道流量與整體河網水量平衡（`m3` / `m3/s`）。 |
| `decisions.jsonl`、`physics.jsonl`、`audit.jsonl`、`backend_events.jsonl` | 所有模擬 | 透過 `decision_id` 串聯的逐時間步因果追蹤日誌。 |
| `provider_attempts.jsonl` 與 `raw/` | LLM / 追蹤模擬 | Append-fsync 模型服務呼叫帳本，以及去敏後的提示詞／回覆原始快照。 |

## 物理模擬軌跡與演算流量

| 檔案 | 主要欄位 | 物理意義（`m3`、`m3/s`） |
| --- | --- | --- |
| `reservoir_trajectory.csv` | `date`/`timestamp`、`reservoir_id`、`inflow_cms`、`target_release_cms`、`controlled_release_cms`、`spill_cms`、`storage_start_m3`、`storage_end_m3`、`adjustments` | 每座水庫於每個時間步一筆紀錄。`target_release_cms` 為操作員請求放流量；`controlled_release_cms` 為物理限幅後的實際受控放流量；`spill_cms` 為超過 `capacity_m3` 的溢流量。 |
| `network_flows.csv` | `date`/`timestamp`、`node`、`local_inflow_cms`、`routed_flow_cms` | 河網各節點的區域增量入流量與總摺積演算流量。 |
| `network_balance.csv` | `local_input_m3`、`outlet_output_m3`、`reservoir_storage_change_m3`、`channel_storage_change_m3`、`system_residual_m3` | 逐時間步閉合的系統整體水量平衡（`system_residual_m3 < 1e-6`）。 |
| `reach_volume_trace.json` | 河段鍵名與時間步陣列 | 在上游放流與下游抵達之間的演算延遲期間，暫時滯留於河道中的水體體積。 |

<div class="callout callout-info" markdown="1">

**放流截幅與執行失敗的區別。** 當操作員請求的放流量超出 `[minimum_release_cms, maximum_release_cms]`，或超過高於 `dead_storage_m3` 的可用水量時，`apply_transition` 會在 `adjustments` 欄位記下調整原因（`target_clipped_to_operating_bounds`、`controlled_release_limited_by_dead_storage`、`spill_above_capacity`），並不會因此中斷模擬。惟 Hanasaki 嚴格等價模式若偵測到主機物理限制與規則推算結果分歧，會在提交前主動拋出 `parity conflict`。

</div>

## 決策、稽核與來源追蹤日誌

- **`decisions.jsonl`**：完整的 `ReservoirObservation`（含 `decision_information` 快照）、請求的 `action`、`request_id`、`serving_profile` 與 `provenance`。
- **`physics.jsonl`**：確切的 `observation` + `action` 與其對應產生的 `Transition` 物理結果。
- **`audit.jsonl`**：每個已設定稽核器針對每筆決策產出的 `AuditedBackend` 結果（`PASS`、`WARN`、`FAIL`、`UNKNOWN`）。稽核 `FAIL` 屬於診斷性質——不會改寫物理流量，也不會阻礙 `status: "COMPLETED"`。
- **`backend_events.jsonl` 與 `provider_attempts.jsonl`**：記錄 `decision_started` → `decision_returned` / `decision_failed` 與 `STARTED` → `RETURNED` / `FAILED` HTTP 呼叫嘗試。若 `summary.json` 顯示 `fallback_used: true`，在將決策歸因於主要模型前，請先確認 `serving_profiles`。

## 驗證已保存的證據

```powershell
reservoir-experiment verify path/to/output --require-offline
```

若為即時連線的 LLM 模擬，請省略 `--require-offline`。`verify`（`src/llm_reservoir_agent/verification.py`）會在不重跑水文模擬、不聯繫模型服務的前提下，獨立核對所有檔案 SHA-256 雜湊值、因果追蹤序列完整性、`apply_transition` 物理不變量、獨立河道摺積演算、`network_balance` 以及重建後的 `InformationCatalog` 快照。
