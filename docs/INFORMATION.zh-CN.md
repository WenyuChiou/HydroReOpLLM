# 水情测站与预报

<div class="hero-band" markdown="1">

`information` 配置文件可在决策当下提供**不泄露未来水情、只读**的河道测站、入流预报、季节调度线或已提交的上游水库状态，绝不让未来的洪峰提前进入今日决策。

</div>

## 水情时序规则与决策时机

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### 操作员内置掌握的信息

- 当期期初 `storage_m3` 与当日演进入流 `inflow_cms`（已含上游依 `unit_hydrograph[0]` 同日抵达的下泄流量）。
- 先前已提交的时间步记录（`$previous_transition` / `$completed_history`）。
- 其他水库于**前一已完成时间步**提交的 `simulation` 蓄水或下泄（第 2 天起可用，第 1 天须设为 `required: false`）。

</div>
<div class="panel-card" markdown="1">

### 水情时序防护（测站与预报）

- 所有 CSV 时间戳均须包含 `Z` 或明确 UTC 偏移量。
- **测站观测**：仅当 `valid_time <= clock` 且 `available_at <= clock` 时才可用。
- **水文预报**：`valid_time` 可指向未来，但须同时满足 `issued_at <= clock` 且 `available_at <= clock`。

</div>
</div>

## 数据来源类型与单位换算

| `type` | 必填字段 | 选填字段 | 用途 |
| --- | --- | --- | --- |
| `static` | `quantity`、`unit`、`location`、`value` | `datum` | 固定目标下泄流量、警戒水位或调度线表。 |
| `csv` | `quantity`、`unit`、`location`、`kind`（`observation` \| `forecast`）、`path` | `datum` | 具水情时间戳的测站观测值或发布预报。 |
| `simulation` | `quantity`（`inflow` \| `storage` \| `release` \| `flow`）、`unit`、`location` | `datum` | 读取其他水库、汇流点或出口的只读状态（`m3`、`m3/s`）。 |
| `extension` | `quantity`、`unit`、`location`、`provider` | `kind`、`parameters`、`datum` | 返回带时间戳记录的自定义 Python 读取器。 |

**测站观测 CSV**（`valid_time,available_at,value`）：

```csv
valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-01T00:00:00Z,1240.0
2021-01-02T00:00:00Z,2021-01-02T00:00:00Z,1580.0
```

**水文预报 CSV**（`issued_at,valid_time,available_at,value`）：

```csv
issued_at,valid_time,available_at,value
2021-01-01T00:00:00Z,2021-01-02T00:00:00Z,2021-01-01T00:00:00Z,1450.0
2021-01-01T00:00:00Z,2021-01-03T00:00:00Z,2021-01-01T00:00:00Z,1920.0
```

内置单位换算（`unit:`）：`m3/s` ↔ `cfs`（`35.31466672148859`）、`m3` ↔ `acre-ft`（`1 / 1233.48183754752`）与 `m` ↔ `ft`（`3.280839895013123`）。

## 配置信息配置文件与智能体绑定

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
      upper_pool_acft: { source: upstream_storage, unit: acre-ft, required: false }  # 第 1 天尚无前期记录，须设 false
```

在 `experiment.yaml` 加入 `information: { file: information.yaml }`，在操作员配置中设置 `customization.information: operator_view`，并在提示词放入 `$information`（Python 规则则读取 `observation["context"]["decision_information"]`）。

## 缺失值处理与验证

| 字段配置 | 缺失或过期时行为 | 验证检查 |
| --- | --- | --- |
| `required: true` | 立即中止模拟（绝不替换为 `0.0`）。 | 在 `verify` 阶段依据来源 CSV 与模拟状态核对数值。 |
| `required: false` | 填入 `status: "MISSING"`、`value: null` 与明确 `reason`。 | 逐条核查 `decisions.jsonl` 每一步的水情时间戳。 |
