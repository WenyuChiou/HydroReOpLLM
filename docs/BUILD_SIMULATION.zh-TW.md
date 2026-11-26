# 多水庫河網串接

<div class="hero-band" markdown="1">

可模擬單一水庫、串聯水庫、平行支流、匯流點、分流與多出口流域，並在同一集水區內自由搭配 **Rule-based（Hanasaki 規則）** 與 **LLM** 操作員。完整實測範例見台灣新店溪[多水庫串聯案例](../examples/multi_reservoir/README.zh-TW.md)（翡翠水庫 → 直潭壩 → `xindian_outlet`）。

</div>

## 水系拓樸與物理規範

在 `case.json` 或 `reservoirs.yaml` 的 `network` 底下定義物理水系（`llm-reservoir-network.v1` 單一 `outlet`、`.v2` 逐日 `outlets` 清單，或 `.v3` 次日固定時距）：

| 組成元件 | 物理意義與限制條件 |
| --- | --- |
| `reservoirs.<key>` | 唯一 ID、`inflow_node`、`capacity_m3`、`dead_storage_m3`、`initial_storage_m3`（`dead <= initial <= capacity`）、`minimum_release_cms`、`maximum_release_cms`、`dt_seconds`。 |
| `operation_mode` | `controlled`（須於 `agents:` 指派一名操作員）或 `passive_outlet`（無閘門控制之溢流堰／溢洪道，依水位－流量曲線演算）。 |
| `junctions`、`outlets` | 彼此互異的匯流點與終端出口 ID（所有無下游連線的終端節點須與 `outlets` 一致）。 |
| `connections[]` | 有向河段，將 `controlled_release_cms + spill_cms` 演算至下游 `inflow_node`、`junction` 或 `outlet`。 |
| `fraction` | 介於 `(0, 1]` 的分流比例（預設 `1.0`）；同一水庫或匯流點往外分流的比例總和須為 `1.0`。 |
| `unit_hydrograph` | 非負延遲權重，總和為 `1.0`：索引 `0` 當步抵達、索引 `1` 延遲一步，依此類推（預設 `[1.0]`）。 |

## 區域增量入流與單位歷線演算

<div class="callout callout-warn" markdown="1">

**僅提供區域增量入流。** 每個 `inflow_node`、`junction` 與 `outlet` 必須**只接收區域側向逕流**——切勿填入已包含上游水庫演算的流量，否則上游水量會被重複計入。

</div>

河道演算將放流量與 `unit_hydrograph` 進行摺積（例如新店溪翡翠至直潭採用 `[0.8, 0.2]`，代表當日抵達 80%、隔日抵達 20%）。模擬結束時仍滯留於河道中的水量記錄於 `reach_volume_trace.json` 與 `network_balance.csv`，確保全流域水量閉合。

## 混合式 Hanasaki 與 LLM 多水庫配置

各水庫操作員獨立運作，因此可在同一份設定中混用 LLM 操作員與 Hanasaki 規則（自備入流實例見台灣新店溪[多水庫串聯案例](../examples/multi_reservoir/README.zh-TW.md)的 `hybrid_llm.yaml` 與 `rule_based.yaml`；以下為耦合 `v2` 流域寫法）：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `experiment.yaml`（`v2` 耦合流域）

```yaml
schema_version: hydroops-coupled-simulation.v2
run_id: hybrid-basin-demo
output: ../../runs/hybrid-basin-demo
case: reservoirs.yaml
start_date: '2020-02-28'
end_date: '2020-03-02'
max_calls: 4
hydrology: { file: hydrology.yaml }
models: { file: models.yaml }
agents: { file: agents.yaml }
auditors: { file: auditors.yaml }
information: { file: information.yaml }
extensions:
  hanasaki: extensions/hanasaki/__init__.py
```

</div>
<div class="panel-card" markdown="1">

### `agents.yaml`（LLM + Hanasaki 混合）

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    information: upstream_view
  auditors: [bounds]

operator_b:
  reservoir_id: lake_b
  type: rule_based
  rule: hanasaki
  rule_parameters:
    purpose: flood_control
    alpha: 0.85
    inflow_statistics_file: statistics_b.json
  auditors: [bounds]
```

</div>
</div>

## 執行順序與跨水庫資訊讀取

1. **由上游至下游順序**：系統依拓樸順序執行河網，確保上游放流先抵達下游後，下游水庫才開始決策。
2. **跨水庫共享狀態**：在 `information.yaml` 加入 `simulation` 來源（見[水情測站與預報](INFORMATION.zh-TW.md)），即可讓下游讀取上游已提交的蓄水或放流；尚未決策的平行水庫無法互看當步數值。
3. **離線驗證拓樸**：每次修改連線、`fraction`、`unit_hydrograph` 或 `outlets` 後請執行 `reservoir-experiment check`。
