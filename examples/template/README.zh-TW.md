# 既有入流資料範本

複製這組雙水庫串聯案例（`upper` → `lower` → `outlet`），並將其中的合成入流、水庫物理尺寸、模擬日期或操作員替換為您自己的資料。

## 檔案與快速執行

| 檔案 | 用途 |
| --- | --- |
| [`experiment.yaml`](experiment.yaml) | 執行識別碼、`start_date`/`end_date`、`output`、`max_calls: 0` 與 `offline` 操作員。 |
| [`case.json`](case.json) | 物理水系結構（`llm-reservoir-network.v2`）、演算延遲與 `inflows.csv` SHA-256 鎖定值。 |
| [`inflows.csv`](inflows.csv) | 逐日區域增量入流量（`m3/s`），期間為 `2026-03-26` 至 `2026-04-06`。 |
| [`prompts/operator.txt`](prompts/operator.txt) | 預備供後續切換為 `mode: llm` / `type: llm` 使用的起始提示詞範本。 |

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

每次執行都請設定全新的 `run_id` 與尚未使用的 `output` 路徑。此 10 天視窗結束時，`upper` 期末蓄水量為 `5,808,000 m3`，`lower` 為 `1,000,000 m3`（已達滿庫並發生溢流）。請依照[解讀執行結果](../../docs/RESULTS_GUIDE.zh-TW.md)檢視 `runs/prepared-template/summary.json`。

## 案例檔案欄位

| 欄位（`case.json`） | 意義、原生單位與限制條件 | 必填 |
| --- | --- | --- |
| `schema_version` | `llm-reservoir-network-case.v1` | 是 |
| `data_kind` | `synthetic_fixture`、`observed_local_inflow` 或 `simulated_local_inflow` | 是 |
| `live_readiness` | 針對非合成入流啟用 LLM 呼叫時須設為 `{"ready": true}` | 否 |
| `network.schema_version` | `llm-reservoir-network.v2`（含 `outlets` 清單、逐日尺度） | 是 |
| `network.start_date` | 加引號之 `YYYY-MM-DD`；必須與 CSV 首筆日期一致 | 是 |
| `network.reservoirs.<key>` | 對應 `agents.*.reservoir` / `reservoir_id` 參照的水庫鍵名 | 是 |
| `...inflow_node`、`physical.reservoir_id` | 彼此互異的入流節點與物理水庫識別碼 | 是 |
| `...physical.capacity_m3`、`dead_storage_m3`、`initial_storage_m3` | 蓄水邊界（`m3`）：`0 <= dead <= initial <= capacity`（`initial` 套用於 `start_date`） | 是 |
| `...physical.minimum_release_cms`、`maximum_release_cms` | 控制放流量上下限（`m3/s`）；超過滿庫庫容的溢流不受此上限限制 | 是 |
| `...physical.dt_seconds` | 時間步長（秒）；逐日 CSV 格式預設為 `86400.0` | 否（`86400`） |
| `network.connections[]` | `source`、`target`、選填 `fraction`（總和為 `1`）、選填 `unit_hydrograph` | 是 |
| `network.outlets` | 非空終端節點清單，必須與所有出度為零的節點完全相符 | 是 |
| `inflow_source` | 嚴格限定 `{path, sha256, format}` 三個鍵值（`daily-node-local-cms.v1`） | 是 |

關於 `junctions`、`operation_mode: passive_outlet` 與 `v3` 固定時距水系，請參閱 [`network.py`](../../src/llm_reservoir_agent/network.py)。

## 入流、河道演算與即時就緒閘門

- **區域增量入流**：`inflows.csv` 欄位為 `date,node,local_inflow_cms`（連續日期、`>= 0` m3/s），不得包含上游已演算抵達的放流量。編輯後請更新 `inflow_source.sha256`：`python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/template/inflows.csv`。
- **河道演算（`unit_hydrograph`）**：索引 `0` 為當期步長、索引 `1` 為 `+1` 步長（`[0.0, 0.7, 0.3]` 表示 70% 於隔日抵達、30% 於兩日後抵達），演算水量為 `controlled_release_cms + spill_cms`。
- **決策時機與即時授權**：每個時間步皆會觀測到時段平均入流量（含上游演算來流）。`synthetic_fixture` 預設即具備即時就緒資格；`observed_local_inflow` 與 `simulated_local_inflow` 則須同時滿足 `"live_readiness": {"ready": true}`、`--allow-network` 與 `max_calls`。詳見[決策時資訊](../../docs/INFORMATION.zh-TW.md)與[執行生命週期](../../docs/RUNNING.zh-TW.md)。

## 更換操作員與 YAML 數值格式

- **操作員**：可依[操作員與 LLM 代理人設計](../../docs/AGENT_DESIGN.zh-TW.md)與 [F.E. Walter 範例](../fe_walter/README.zh-TW.md)或[互動教學](../../tutorials/README.zh-TW.md)，將 `mode: offline`（`release_cms`）替換為 `type: rule_based`（例如 Hanasaki）或 `type: llm`。
- **YAML 科學記號**：指數務必明確標示 `+`/`-` 正負號（例如 `8.0e+6` 或 `8000000.0`），因為 PyYAML 會將 `8.0e6` 解析成文字而遭 `check` 拒絕。
