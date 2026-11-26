# 水庫網路與混合控制

<div class="hero-band" markdown="1">

HydroReOpLLM 支援模擬單一水庫、串聯水庫、平行支流、河川匯流點、分流與多出口流域。每座受控水庫皆擁有獨立的操作員——讓您可以輕鬆在同一個集水區內，將 **Hanasaki 規則式**水庫與 **LLM 操作**水庫搭配運作。

</div>

## 水系拓樸與物理規範

在 `case.json` 或 `reservoirs.yaml` 的 `network` 區段定義流域拓樸（`llm-reservoir-network.v1` 使用單一 `outlet`、`.v2` 使用逐日 `outlets` 清單、`.v3` 則用於次日固定時距模擬）：

| 水系組成 | 物理意義與限制條件 |
| --- | --- |
| `reservoirs.<key>` | 唯一水庫 ID、配對的 `inflow_node`、`capacity_m3`、`dead_storage_m3`、`initial_storage_m3`（`dead <= initial <= capacity`）、`minimum_release_cms`、`maximum_release_cms` 與 `dt_seconds`。 |
| `operation_mode` | `controlled`（由 `agents:` 中的操作員控管）或 `passive_outlet`（無閘門控制之溢流堰／自由溢洪道，僅依水位－流量曲線演算，無須配置操作員）。 |
| `junctions` 與 `outlets` | 彼此互異的支流匯流點與流域終端出口識別碼（所有無下游連線的終端節點都必須列於 `outlets`）。 |
| `connections[]` | 有向河段，將水庫或匯流點的總出流（`controlled_release_cms + spill_cms`）導向下游的 `inflow_node`、`junction` 或 `outlet`（不得形成環路）。 |
| `fraction` | 選填的無因次分流比例，介於 `(0, 1]`（預設 `1.0`）；任一水庫或匯流點往外分流的比例總和必須等於 `1.0`。 |
| `unit_hydrograph` | 非負河道匯流延遲權重，總和為 `1.0`：索引 `0` 當步抵達、索引 `1` 延遲一步、索引 `2` 延遲兩步（預設 `[1.0]`）。 |

## 區域增量入流與單位歷線演算

<div class="callout callout-warn" markdown="1">

**僅提供區域增量入流量。** `inflows.csv`（或 `inflow_bindings`）中的每一個 `inflow_node`、`junction` 與 `outlet` 必須**只包含進入該河段的區域側向逕流**——切勿填入已經包含上游水庫演算放流量的數值。HydroReOpLLM 會自動透過 `connections[]` 加上來自上游水庫的出流。

</div>

河道演算採用 `unit_hydrograph` 權重的離散線性摺積。例如 `[0.0, 0.7, 0.3]` 代表放流當日抵達 0%、隔日抵達 70%、兩日後抵達 30%。模擬結束時仍滯留於多日演算河段中的水量，會明確記錄於 `reach_volume_trace.json` 與 `network_balance.csv`，確保全流域總水量永遠守恆閉合。

## 混合式 Hanasaki 與 LLM 多水庫配置

由於每座水庫的操作員皆獨立運作，您可以在同一份 `agents.yaml` 中將 LLM 操作員配置於其中一座水庫，並為平行或上游水庫指派決定性 Hanasaki 規則（參考 `tests/fixtures/examples/multiple_reservoirs/` 模式）：

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

1. **由上游至下游依序執行**：在每個時間步 `t`，HydroReOpLLM 會依拓樸順序推進河網。上游水庫會先完成決策並將出流演算至下游，下游水庫才觀測當日總入流量 `inflow_cms`。
2. **跨水庫共享狀態**：當下游水庫需要得知上游水庫已提交的蓄水量或放流量——或是平行水庫需依據昨日已提交狀態協同運轉時——請在 `information.yaml` 中設定 `simulation` 來源（見[決策時資訊](INFORMATION.zh-TW.md)）。同一時間步中尚未動作的平行水庫狀態將保持不可讀取，以維護因果正確性。
3. **離線驗證拓樸**：每次修改連線、`fraction` 分流比例、`unit_hydrograph` 延遲權重或 `outlets` 後，請執行 `reservoir-experiment check`。
