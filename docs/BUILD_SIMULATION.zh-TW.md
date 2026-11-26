# 水庫網路與混合式多庫控制

<div class="hero-band" markdown="1">

HydroReOpLLM 於 `network.py` 與 `interval_network.py` 中將單一水庫、串聯水庫、平行支線、匯流點與多出口流域建模為有向無環圖（DAG）。每座受控水庫皆擁有獨立的操作員——讓您能輕鬆在同一個流域中結合 **Hanasaki 規則式** 與 **LLM 驅動** 的代理人。

</div>

## 水系拓樸與物理規範

`validate_network`（`src/llm_reservoir_agent/network.py`）針對 `llm-reservoir-network.v1`（單一 `outlet`）、`.v2`（`outlets` 清單、逐日）與 `.v3`（`outlets` 清單、明確 `start_time` / `dt_seconds`）強制檢查結構與物理一致性：

| 水系組成 | 核心規則與不變量 |
| --- | --- |
| `reservoirs.<key>` | 唯一的非空水庫鍵名、唯一 `inflow_node`、唯一 `physical.reservoir_id`、與水系時鐘一致的 `dt_seconds`、`dead_storage_m3 <= initial_storage_m3 <= capacity_m3`，以及 `minimum_release_cms <= maximum_release_cms`。 |
| `operation_mode` | `controlled`（須在 `agents:` 內對應且僅對應一名操作員）或 `passive_outlet`（使用 `passive_outlet` 率定曲線，無操作員）。 |
| `junctions` 與 `outlets` | 所有水庫、入流節點、匯流點與出口 ID 皆須彼此互異。所有無下游出流的終端節點必須與 `outlets` 清單完全吻合。 |
| `connections[]` | 將水庫或匯流點的總出流（`controlled_release_cms + spill_cms`）導向 `inflow_node`、`junction` 或 `outlet`（禁止自我迴圈與有向環路）。 |
| `fraction` | 介於 `(0, 1]` 的無因次分流比例；同一水庫或匯流點的所有下游分流比例總和須在 `1e-12` 誤差內等於 `1.0`。 |
| `unit_hydrograph` | 各項大於等於 0 且總和在 `1e-12` 誤差內等於 `1.0` 的時間步延遲權重；索引 `0` 代表當期時間步、索引 `1` 代表 `+1` 時間步，依此類推。 |

## 區域增量入流與單位歷線演算

<div class="callout callout-warn" markdown="1">

**區域增量入流原則。** 每一個 `routing_node`（`inflow_node`、`junction`、`outlet`）自 `inflows.csv` 或 `hydrology.yaml` `inflow_bindings` 取得的數值，**僅能代表該節點的區域側向逕流**。切勿在下游節點填入已包含上游演算水量的流量，否則 HydroReOpLLM 會重複計入上游放流量。

</div>

在每一個節點上，總流量等於區域增量入流量加上所有上游來流經 `connections[]` 單位歷線摺積後抵達的水量。尚未抵達下游、仍滯留於多步長 `unit_hydrograph` 河道中的水體體積，會明確記錄於 `reach_volume_trace.json` 與 `network_balance.csv`（`channel_storage_end_m3`），使整個河網的質量平衡閉合至機器精度（`< 1e-6` m3）。

## 混合式 Hanasaki 與 LLM 多水庫配置

由於 `validate_isolated_backends` 確保每座水庫都持有各自獨立的有狀態後端實例，您可以在同一份 `agents.yaml` 中同時為一座水庫指派 LLM 操作員、為另一座水庫指派決定性 Hanasaki 規則（參考 `tests/fixtures/examples/multiple_reservoirs/agents.llm.yaml` 與 `experiment.yaml` 模式）：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### `experiment.yaml`（`v2` 耦合入口）

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

### `agents.yaml`（混合 LLM + Hanasaki）

```yaml
operator_a:
  reservoir_id: lake_a
  type: llm
  model_profile: local
  prompt_file: prompts/operator.txt
  customization:
    system_prompt_file: prompts/system.txt
    information: downstream_view
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

1. **決定性拓樸順序**：在每個時間步 `t`，`network.py` / `interval_network.py` 會依拓樸序列（`SimSeq`）依序執行節點。上游水庫會先完成該步的 `Transition` 並將 `total_outflow_cms` 演算至下游，下游水庫才觀測其 `inflow_cms`。
2. **因果跨水庫讀取**：若下游或平行水庫需要讀取另一座水庫的狀態，請於 `information.yaml` 中宣告 `simulation` 來源（見[決策時資訊](INFORMATION.zh-TW.md)）。同一個時間步 `t` 中僅可讀取稍早已提交的上游水庫狀態；尚未提交或平行節點之當期狀態須待步驟 `t` 結束後方可使用。
3. **驗證設定**：每次修改水系拓樸、分流比例、單位歷線或操作員指派後，請務必執行 `reservoir-experiment check`。
