# 多水庫串聯案例：新店溪翡翠水庫 → 直潭壩

本範例以台灣經濟部水利署（WRA）**2020 年 5 月梅雨鋒面**（`2020-05-20` 至 `2020-05-29`）實測日入流資料，建構新店溪雙水庫串聯系統（**翡翠水庫 `feitsui`** → **直潭壩 `zhitan`** → **`xindian_outlet`**），示範 `[0.8, 0.2]` 河道演算延遲（當日 `80%`、隔日 `20%`），並對照雙庫規則基準與「上游規則＋下游 LLM」混合運轉。

## 檔案與快速執行

| 檔案 | 用途 |
| --- | --- |
| [`rule_based.yaml`](rule_based.yaml) | 10 天離線基準（`2020-05-20`–`2020-05-29`）：翡翠與直潭皆採 Hanasaki 滯洪規則（α = 0.85）。 |
| [`hybrid_llm.yaml`](hybrid_llm.yaml) | 10 天混合設定：上游翡翠水庫採 Hanasaki（`feitsui_operator`）＋下游直潭壩採 LLM（`zhitan_operator`）。 |
| [`case.json`](case.json) | 水庫有效庫容（翡翠 `335,505,000 m3`、直潭 `1,918,900 m3`）、放流上下限（`[0, 500]` 與 `[0, 800] m3/s`）與 `[0.8, 0.2]` 演算權重。 |
| [`inflows.csv`](inflows.csv) | 2020-05-18 至 2020-06-02（16 天）WRA 實測區域入流（`m3/s`；`zhitan_local` 為南勢溪與區間側向逕流）。 |
| [`reference_inflows.csv`](reference_inflows.csv) | 2019 年全年 WRA 日入流，用以建立 `feitsui_statistics.json` 與 `zhitan_statistics.json` 參考統計。 |
| [`prompts/operator.txt`](prompts/operator.txt) | `hybrid_llm.yaml` 中 `zhitan_operator` 的提示詞範本，要求回傳 `reservoir-action.v1` JSON。 |

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

重複執行前請更換新的 `run_id` 與未使用的 `output`。10 天 `rule_based.yaml` 離線模擬結束時，翡翠水庫（`feitsui`）蓄水量為 `275,297,173 m3`、直潭壩（`zhitan`）為 `1,761,528 m3`（`PASS`）。若要即時執行 `hybrid_llm.yaml`，請啟動本機 Ollama（`gemma4:12b`）並加上 `--allow-network`。輸出判讀請見[結果判讀與水量平衡](../../docs/RESULTS_GUIDE.zh-TW.md)。

## 物理水系欄位（`case.json`）

`network.reservoirs.<key>` 底下的每座水庫皆定義各自的 `inflow_node` 與 `physical.*` 物理邊界：

| 欄位 | 意義、原生單位與限制 | 必填 |
| --- | --- | --- |
| `schema_version` | `llm-reservoir-network-case.v1` | 是 |
| `data_kind` | `observed_local_inflow`（本案例）、`simulated_local_inflow` 或 `synthetic_fixture` | 是 |
| `live_readiness` | 對實測或模擬入流啟用 LLM 時須設為 `{"ready": true}`（本案例已就緒） | 否 |
| `network.schema_version` | `llm-reservoir-network.v2`（`outlets` 清單、逐日） | 是 |
| `network.start_date` | 加引號之 `YYYY-MM-DD`；須與 `inflows.csv` 首筆日期（`2020-05-18`）一致 | 是 |
| `reservoirs.<key>.inflow_node` | 區域入流節點 ID（`feitsui_local`、`zhitan_local`） | 是 |
| `physical.capacity_m3`、`dead_storage_m3`、`initial_storage_m3` | 有效庫容邊界（`m3`）：`0 <= dead <= initial <= capacity`（初始值套用於 `start_date`） | 是 |
| `physical.minimum_release_cms`、`maximum_release_cms` | 控制放流上下限（`m3/s`）；超過滿庫之溢流不受上限限制 | 是 |
| `physical.dt_seconds` | 時間步長（秒）；逐日 CSV 為 `86400.0` | 否 |
| `network.connections[]` | `source`、`target`、選填 `fraction`（總和為 `1`）、選填 `unit_hydrograph` | 是 |
| `network.outlets` | 非空終端出口清單（本案例為 `["xindian_outlet"]`） | 是 |
| `inflow_source` | `{path, sha256, format}`（`daily-node-local-cms.v1`） | 是 |

匯流點、無閘門溢流堰（`passive_outlet`）與次日（`v3`）串聯請參閱[多水庫河網串接](../../docs/MULTI_RESERVOIR.zh-TW.md)。

## 入流、河道演算與 YAML 注意事項

- **區域增量入流**：`inflows.csv` 欄位為 `date,node,local_inflow_cms`（連續日期、`>= 0` m3/s），不含上游放流。編輯 `inflows.csv` 後請執行 `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" examples/multi_reservoir/inflows.csv` 更新 `case.json` 中的 `inflow_source.sha256`。
- **單位歷線演算**：`feitsui` 將 `controlled_release_cms + spill_cms` 透過 `[0.8, 0.2]` 演算至 `zhitan_local`；`zhitan` 透過 `[1.0]` 演算至 `xindian_outlet`。
- **YAML 科學記號**：指數務必加上 `+` 或 `-`（例如 `8.0e+6` 或 `8000000.0`），否則 YAML 會將 `8.0e6` 當作純文字而遭 `check` 拒絕。
- **延伸學習**：對照單一水庫 [F.E. Walter 水庫案例](../fe_walter/README.zh-TW.md)，或前往[操作規則與 LLM 設計](../../docs/AGENT_DESIGN.zh-TW.md)自訂提示詞。
