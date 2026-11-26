# 雙水庫入門範本

複製這組雙水庫串聯系統（`upper` → `lower` → `outlet`），並替換成您的區域入流、水庫物理尺寸、日期或操作員。

## 檔案與快速執行

| 檔案 | 用途 |
| --- | --- |
| [`experiment.yaml`](experiment.yaml) | 執行識別碼、`start_date`/`end_date`、`output`、`max_calls: 0` 與 `offline` 操作員。 |
| [`case.json`](case.json) | 物理水系（`llm-reservoir-network.v2`）、演算延遲與 `inflows.csv` 連結。 |
| [`inflows.csv`](inflows.csv) | 逐日區域增量入流（`m3/s`），期間為 `2026-03-26` 至 `2026-04-06`。 |
| [`prompts/operator.txt`](prompts/operator.txt) | 預備供後續切換為 `mode: llm` / `type: llm` 使用的提示詞範本。 |

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

每次執行請設定新的 `run_id` 與未使用的 `output`。10 天模擬結束時，`upper` 為 `5,808,000 m3`、`lower` 為 `1,000,000 m3`（達滿庫並溢流）。依[結果判讀與水量平衡](../../docs/RESULTS_GUIDE.zh-TW.md)檢視 `runs/prepared-template/summary.json`。

## 案例檔案欄位

下表中 `physical.*` 欄位皆位於 `network.reservoirs.<key>` 底下：

| 欄位（`case.json`） | 意義、原生單位與限制 | 必填 |
| --- | --- | --- |
| `schema_version` | `llm-reservoir-network-case.v1` | 是 |
| `data_kind` | `synthetic_fixture`、`observed_local_inflow` 或 `simulated_local_inflow` | 是 |
| `live_readiness` | 對非合成入流啟用 LLM 時須設為 `{"ready": true}` | 否 |
| `network.schema_version` | `llm-reservoir-network.v2`（`outlets` 清單、逐日） | 是 |
| `network.start_date` | 加引號之 `YYYY-MM-DD`；須與 CSV 首筆日期一致 | 是 |
| `network.reservoirs.<key>` | `agents.*.reservoir` / `reservoir_id` 參照的水庫鍵名 | 是 |
| `reservoirs.<key>.inflow_node`、`physical.reservoir_id` | 彼此互異的入流節點與物理水庫 ID | 是 |
| `physical.capacity_m3`、`dead_storage_m3`、`initial_storage_m3` | 庫容邊界（`m3`）：`0 <= dead <= initial <= capacity`（套用於 `start_date`） | 是 |
| `physical.minimum_release_cms`、`maximum_release_cms` | 控制放流上下限（`m3/s`）；溢流不受此上限限制 | 是 |
| `physical.dt_seconds` | 時間步長（秒）；逐日 CSV 為 `86400.0` | 否（`86400`） |
| `network.connections[]` | `source`、`target`、選填 `fraction`（總和為 `1`）、選填 `unit_hydrograph` | 是 |
| `network.outlets` | 非空終端節點清單，須與出度為零的節點一致 | 是 |
| `inflow_source` | 固定鍵值 `{path, sha256, format}`（`daily-node-local-cms.v1`） | 是 |

關於 `junctions`、`operation_mode: passive_outlet` 與 `v3` 次日時距水系，請見[多水庫河網串接](../../docs/BUILD_SIMULATION.zh-TW.md)。

## 入流、河道演算與即時就緒閘門

- **區域增量入流**：`inflows.csv` 欄位為 `date,node,local_inflow_cms`（連續日期、`>= 0` m3/s），不含上游放流。編輯 `inflows.csv` 後請以 `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/template/inflows.csv` 更新 `inflow_source.sha256`。
- **河道演算（`unit_hydrograph`）**：索引 `0` 為當步、索引 `1` 為 `+1` 步（`[0.0, 0.7, 0.3]` 表示 70% 隔日、30% 兩日後抵達），演算對象為 `controlled_release_cms + spill_cms`。
- **決策時機與即時閘門**：每步觀測時段平均入流（含上游來流）。`synthetic_fixture` 自動就緒；實測／模擬入流須具 `"live_readiness": {"ready": true}`、`--allow-network` 與 `max_calls`。詳見[水情測站與預報](../../docs/INFORMATION.zh-TW.md)與[執行、驗證與續跑](../../docs/RUNNING.zh-TW.md)。

## 更換操作員與 YAML 數值格式

- **操作員**：可依[操作規則與 LLM 設計](../../docs/AGENT_DESIGN.zh-TW.md)、[F.E. Walter 水庫案例](../fe_walter/README.zh-TW.md)或 [F.E. Walter 互動教學](../../tutorials/README.zh-TW.md)將 `mode: offline`（`release_cms`）改為 `type: rule_based` 或 `type: llm`。
- **YAML 科學記號**：指數務必加上 `+`/`-`（`8.0e+6` 或 `8000000.0`），否則 PyYAML 會將 `8.0e6` 當成字串。
