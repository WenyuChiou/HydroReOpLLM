# 水情測站與預報

<div class="hero-band" markdown="1">

`information` 設定檔可在決策當下提供**不洩漏未來水情、唯讀**的河川測站、入流預報、季節運轉規線或已提交之上游水庫狀態，絕不讓未來的洪峰提早進入今日決策。

</div>

## 水情時序規則與決策時機

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 操作員內建掌握的資訊

- 當期期初 `storage_m3` 與當日演算入流 `inflow_cms`（已含上游依 `unit_hydrograph[0]` 同日抵達之放流）。
- 先前已提交的時間步紀錄（`$previous_transition` / `$completed_history`）。
- 他座水庫於**前一已完成時間步**提交的 `simulation` 蓄水或放流（第 2 天起可用，第 1 天須設為 `required: false`）。

</div>
<div class="panel-card" markdown="1">

### 水情時序防護（測站與預報）

- 所有 CSV 時間戳記皆須包含 `Z` 或明確 UTC 偏移量。
- **測站觀測**：僅當 `valid_time <= clock` 且 `available_at <= clock` 時才可用。
- **水文預報**：`valid_time` 可指向未來，但須同時滿足 `issued_at <= clock` 且 `available_at <= clock`。

</div>
</div>

## 資料來源類型與單位換算

| `type` | 必填欄位 | 選填欄位 | 用途 |
| --- | --- | --- | --- |
| `static` | `quantity`、`unit`、`location`、`value` | `datum` | 固定目標放流量、警戒水位或規線表。 |
| `csv` | `quantity`、`unit`、`location`、`kind`（`observation` \| `forecast`）、`path` | `datum` | 具水情時間戳記的測站觀測值或發布預報。 |
| `simulation` | `quantity`（`inflow` \| `storage` \| `release` \| `flow`）、`unit`、`location` | `datum` | 讀取其他水庫、匯流點或出口的唯讀狀態（`m3`、`m3/s`）。 |
| `extension` | `quantity`、`unit`、`location`、`provider` | `kind`、`parameters`、`datum` | 回傳帶時間戳記紀錄的自訂 Python 讀取器。 |

**測站觀測 CSV**（`valid_time,available_at,value`）：

```csv
valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-01T00:00:00Z,1240.0
2021-01-02T00:00:00Z,2021-01-02T00:00:00Z,1580.0
```

**水文預報 CSV**（`issued_at,valid_time,available_at,value`）：

```csv
issued_at,valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-02T00:00:00Z,2021-01-01T00:00:00Z,1450.0
2021-01-01T00:00:00Z,2021-01-03T00:00:00Z,2021-01-01T00:00:00Z,1920.0
```

內建單位換算（`unit:`）：`m3/s` ↔ `cfs`（`35.31466672148859`）、`m3` ↔ `acre-ft`（`1 / 1233.48183754752`）與 `m` ↔ `ft`（`3.280839895013123`）。

## 設定資訊設定檔與代理人綁定

```yaml
# information.yaml
sources:
  downstream_gauge:
    type: csv
    kind: observation
    quantity: flow
    unit: cfs
    location: usgs_01449000
    path: data/lehighton_obs.csv
  upstream_storage:
    type: simulation
    quantity: storage
    unit: m3
    location: upper_dam
profiles:
  operator_view:
    fields:
      lehighton_flow_cms: { source: downstream_gauge, unit: m3/s, history: 3, max_age_seconds: 86400, required: false }
      upper_pool_acft: { source: upstream_storage, unit: acre-ft, required: false }  # 第 1 天尚無前期紀錄，須設 false
```

在 `experiment.yaml` 加入 `information: { file: information.yaml }`，於操作員設定 `customization.information: operator_view`，並在提示詞放入 `$information`（Python 規則則讀取 `observation["context"]["decision_information"]`）。

## 缺值處理與驗證

| 欄位設定 | 缺漏或過期時行為 | 驗證檢查 |
| --- | --- | --- |
| `required: true` | 立即中止模擬（絕不代換為 `0.0`）。 | 於 `verify` 階段依來源 CSV 與模擬狀態核對數值。 |
| `required: false` | 填入 `status: "MISSING"`、`value: null` 與明確 `reason`。 | 逐筆查核 `decisions.jsonl` 每一步的水情時間戳記。 |
