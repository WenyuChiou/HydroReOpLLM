# 多水庫串聯案例

本範例以雙水庫串聯系統（`upper` → `lower` → `outlet`）示範由上游至下游的河道演算延遲（`[0.0, 0.7, 0.3]`，代表 `70%` 隔日抵達、`30%` 兩日後抵達），並對照全規則基準與「上游規則＋下游 LLM」的混合操作。

## 檔案與快速執行

| 檔案 | 用途 |
| --- | --- |
| [`rule_based.yaml`](rule_based.yaml) | 10 天離線基準（`2026-03-27`–`2026-04-05`）：上下游皆採 Hanasaki 滯洪規則（α = 0.85，`max_calls: 0`）。 |
| [`hybrid_llm.yaml`](hybrid_llm.yaml) | 10 天混合設定：上游 Hanasaki（`upper`）＋下游 LLM（`lower`，`prompts/operator.txt`，`max_calls: 10`）。 |
| [`case.json`](case.json) | 水庫庫容、放流上下限、`[0.0, 0.7, 0.3]` 演算權重與 `inflows.csv` 連結。 |
| [`inflows.csv`](inflows.csv) | 逐日區域增量入流（`m3/s`），期間 `2026-03-26` 至 `2026-04-06`（不含上游放流量）。 |
| [`prompts/operator.txt`](prompts/operator.txt) | `hybrid_llm.yaml` 中 `lower_operator` 的入門提示詞，要求回傳 `reservoir-action.v1` JSON。 |

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

重複執行前請更換新的 `run_id` 與未使用的 `output`。10 天 `rule_based.yaml` 模擬結束時，`upper` 蓄水量為 `3,023,037 m3`、`lower` 為 `800,044 m3`（`PASS`，`0` 次網路呼叫）。若要即時執行 `hybrid_llm.yaml`，請啟動本機 Ollama（`gemma4:12b`）並加上 `--allow-network`。輸出解讀請見[結果判讀與水量平衡](../../docs/RESULTS_GUIDE.zh-TW.md)。

## 物理水系欄位（`case.json`）

`network.reservoirs.<key>` 底下的每座水庫皆定義各自的 `inflow_node` 與 `physical.*` 物理邊界：

| 欄位 | 意義、原生單位與限制 | 必填 |
| --- | --- | --- |
| `schema_version` | `llm-reservoir-network-case.v1` | 是 |
| `data_kind` | `synthetic_fixture`、`observed_local_inflow` 或 `simulated_local_inflow` | 是 |
| `live_readiness` | 對非合成入流啟用 LLM 時須設為 `{"ready": true}` | 否 |
| `network.schema_version` | `llm-reservoir-network.v2`（`outlets` 清單、逐日） | 是 |
| `network.start_date` | 加引號之 `YYYY-MM-DD`；須與 `inflows.csv` 首筆日期一致 | 是 |
| `reservoirs.<key>.inflow_node` | 唯一的區域入流節點 ID（須與 `physical.reservoir_id` 相異） | 是 |
| `physical.capacity_m3`、`dead_storage_m3`、`initial_storage_m3` | 庫容邊界（`m3`）：`0 <= dead <= initial <= capacity`（套用於 `start_date`） | 是 |
| `physical.minimum_release_cms`、`maximum_release_cms` | 控制放流上下限（`m3/s`）；超過滿庫之溢流不受上限限制 | 是 |
| `physical.dt_seconds` | 時間步長（秒）；逐日 CSV 為 `86400.0` | 否 |
| `network.connections[]` | `source`、`target`、選填 `fraction`（總和為 `1`）、選填 `unit_hydrograph` | 是 |
| `network.outlets` | 非空終端出口清單，須與所有無下游連線的節點一致 | 是 |
| `inflow_source` | `{path, sha256, format}`（`daily-node-local-cms.v1`） | 是 |

匯流點、無閘門溢流堰（`passive_outlet`）與次日（`v3`）串聯請參閱[多水庫河網串接](../../docs/BUILD_SIMULATION.zh-TW.md)。

## 入流、河道演算與 YAML 注意事項

- **區域增量入流**：`inflows.csv` 欄位為 `date,node,local_inflow_cms`（連續日期、`>= 0` m3/s），不含上游放流。編輯 `inflows.csv` 後請執行 `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/multi_reservoir/inflows.csv` 更新 `inflow_source.sha256`。
- **單位歷線演算**：`upper` 將 `controlled_release_cms + spill_cms` 透過 `[0.0, 0.7, 0.3]` 演算至 `lower_local`；`lower` 透過 `[1.0]` 演算至 `outlet`。
- **YAML 科學記號**：指數務必加上 `+` 或 `-`（`8.0e+6` 或 `8000000.0`），否則 YAML 會將 `8.0e6` 當作純文字而遭 `check` 拒絕。
- **延伸學習**：對照單一水庫 [F.E. Walter 水庫案例](../fe_walter/README.zh-TW.md)，或前往[操作規則與 LLM 設計](../../docs/AGENT_DESIGN.zh-TW.md)自訂提示詞。
