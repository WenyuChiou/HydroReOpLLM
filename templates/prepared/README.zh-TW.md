# 既有入流資料範本

若已備妥各水庫的區域入流量時間序列，請使用此範本。先執行一次內附的合成範例，再替換為實際資料數值。
若需搭配原生 HydroCNHS 水文模式，請改用[耦合範本](../coupled/README.zh-TW.md)。

| 檔案 | 用途 |
|---|---|
| `experiment.yaml` | 執行識別碼、日期、輸出路徑，以及各水庫對應的一名操作員 |
| `case.json` | 物理水系結構、演算設定與入流量 CSV 路徑參照 |
| `inflows.csv` | 區域入流量（m3/s），期間為 2026-03-26 至 2026-04-06 |
| `prompts/operator.txt` | 供後續切換為 LLM 操作員時使用的提示詞檔案 |

於專案根目錄執行下列指令。

```shell
reservoir-experiment check templates/prepared/experiment.yaml
reservoir-experiment run templates/prepared/experiment.yaml
reservoir-experiment verify runs/prepared-template
```

每次執行時，請為相對於 `experiment.yaml` 的 `output` 指定全新路徑，並設定新的 `run_id`。內附範例涵蓋 10 天操作期間，自 `start_date` 起至 `end_date` 止。
模擬結束時，`upper` 的最終庫容為 5,808,000 m3，`lower` 的最終庫容為 1,000,000 m3，後者已達滿庫庫容並發生溢流。若縮短模擬視窗，`initial_storage_m3` 將套用於第一個操作日。
請開啟 `runs/prepared-template/summary.json`。此工作流程會直接將水庫操作紀錄寫入該目錄。詳細解讀方式請參閱[結果檢視指南](../../docs/RESULTS_GUIDE.zh-TW.md)。

## 案例檔案 `case.json` 的欄位

JSON 不支援註解。請依下表替換欄位值。

| 欄位 | 意義、單位與允許值 | 必填 |
|---|---|---|
| `schema_version` | `llm-reservoir-network-case.v1` | 是 |
| `data_kind` | `synthetic_fixture`、`observed_local_inflow` 或 `simulated_local_inflow`（詳見下文） | 是 |
| `live_readiness` | 對應物件。設為 `{"ready": true}` 才允許 LLM 操作員於非合成資料上運作（詳見下文） | 否 |
| `network.schema_version` | `llm-reservoir-network.v2`（日時間步長，含 `outlets` 清單） | 是 |
| `network.start_date` | `YYYY-MM-DD`。必須與入流量 CSV 的首筆日期一致 | 是 |
| `network.reservoirs.<key>` | `<key>` 對應 `agents.*.reservoir` 所指定的名稱 | 是 |
| `...inflow_node`, `physical.reservoir_id` | 承接區域入流量的節點識別碼。不可為空值的水庫識別碼。所有識別碼皆須互不重複 | 是 |
| `...physical.capacity_m3`, `dead_storage_m3`, `initial_storage_m3` | 庫容，單位為 m3：滿庫庫容須大於 0。呆庫容（受保護的最低庫容）須小於或等於初始庫容。初始庫容（第一個操作日）須小於或等於滿庫庫容 | 是 |
| `...physical.minimum_release_cms`, `maximum_release_cms` | 控制放流量上下限，單位為 m3/s，最小放流量須小於或等於最大放流量。超過滿庫庫容的溢流量不受上限限制 | 是 |
| `...physical.dt_seconds` | 時間步長，單位為秒。採用日資料 CSV 格式時為 `86400` | 否（86400） |
| `network.connections[]` | 每筆水庫出流連線對應一個項目，包含 `source`、`target`，以及選填的 `fraction`、`unit_hydrograph` | 是 |
| `...source`, `...target` | 來源可為水庫或匯流點。目標可為入流節點、匯流點或出口節點，且不可指向自身 | 是 |
| `...fraction` | 來源出流量的無因次分配比例，範圍為 (0, 1]。同一來源的分配比例總和須為 1 | 否（1） |
| `...unit_hydrograph` | 無因次延遲時間步長權重，各項皆須大於或等於 0，且總和為 1 | 否（`[1.0]`） |
| `network.outlets` | 不可為空的清單。必須與所有終端節點完全一致 | 是 |
| `inflow_source` | 包含 `path`（相對於 `case.json`）、`sha256`（CSV 檔案位元組的雜湊值）、`format` = `daily-node-local-cms.v1`。且僅限此三個鍵值 | 是 |

其餘欄位（`junctions`、`operation_mode`、被動溢流口、非日時間步長）請參閱 `src/llm_reservoir_agent/network.py:37`。僅當資料類型為 `synthetic_fixture` 時，才可使用內嵌的 `inflow_records` 取代 `inflow_source`（見 `case.py:127`）。

**入流量 CSV。** 標頭必須完全為 `date,node,local_inflow_cms`。每個日期皆須提供所有入流節點、匯流點與出口節點的數值（此範例中出口節點為 0.0），數值須大於或等於 0，單位為 m3/s。該數值為時段平均的區域入流量，不含上游水庫演算而來的水量。日期必須為連續的每日序列，不可有缺漏。
編輯 CSV 後，請將更新後的雜湊值填入 `inflow_source.sha256`。
`python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" templates/prepared/inflows.csv`
若編輯工具變更了 CSV 的換行字元，雜湊值亦會隨之改變。

**演算。** `unit_hydrograph` 會將單一時間步長的出流量分配至後續時間步長。索引 0 代表當期時間步，索引 1 代表下一個時間步。此範例中 `upper` 至 `lower` 採用 `[0.0, 0.7, 0.3]`：70% 會在下一個時間步抵達，30% 會在兩個時間步長後抵達。若省略此欄位，預設為 `[1.0]`，代表無延遲。水庫的總出流量為控制放流量加上溢流量。

**決策時機。** 操作員在每個時間步皆會取得含上游演算水量的時段平均入流量，此設定假設事前已知當日平均入流量。
若為耦合案例，請透過[決策資訊目錄](../../docs/INFORMATION.zh-TW.md)取得具時間戳記的觀測值、預報資料與模擬歷史紀錄。

## `data_kind` 與模型呼叫

- `synthetic_fixture`：合成或測試用資料。無須設定 `live_readiness` 即可供 LLM 操作員使用。
- `observed_local_inflow`、`simulated_local_inflow`：實測或模式產生的時間序列。若要啟用 LLM 操作員，須於 `case.json` 頂層與 `data_kind` 同階處加入 `"live_readiness": {"ready": true}`，且 `ready` 必須為 JSON 布林值 `true`。

執行 LLM 操作時，還須加上 `--allow-network` 並將 `max_calls` 設為不低於預計請求次數。執行 `check` 時會回報 `live_ready` 狀態。此範本預設使用 `max_calls: 0` 與 `mode: offline`，不會發出任何模型請求。若改用 LLM，請妥善記錄資料就緒決策，並遵循 [`docs/RUNNING.md`](../../docs/RUNNING.zh-TW.md) 中明確的網路與嘗試次數控管規範。

## 更換操作員

`mode: offline` 搭配 `release_cms` 代表固定放流量。若要改用已註冊規則或 LLM，請從 [`templates/coupled`](../coupled/README.zh-TW.md) 複製對應檔案（`agents.rule.yaml`、`agents.llm.yaml`、`models.yaml`、`extensions/`）。

## YAML 數值格式

YAML 載入器會將 `4.0e0`（含小數點但未標示指數正負號）解析為文字，進而導致 `check` 驗證失敗。請改寫為 `8000000.0` 或 `8.0e+6`。JSON 格式不受此限。
