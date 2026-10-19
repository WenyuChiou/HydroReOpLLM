# FE Walter 相容性測試資料

[English](README.md) | [繁體中文](README.zh-TW.md)

新研究請依照[目前 FE Walter 教學](../../tutorials/fe_walter.md)設定。
此目錄提供介面測試使用的短期合成資料。
框架使用案例自己的訊息組合與解析程式；選用的原版程式由 repo 外經雜湊驗證的來源載入。

| 策略 | 指令／知識 | 原始回覆 |
|---|---|---|
| `configured` | 自己的 prompt template、知識檔與 auditors | 通用版本化 JSON，單位 m³/s |
| `reference_v3_7`、`method: zeroshot` | 原版公開資訊與季節目標，不含 DKP | 原版六個欄位，放流為 cfs |
| `reference_v3_7`、`method: dkp` | 相同基本資訊，加上原版 DKP 檢索 | 原版八個欄位，放流為 cfs |

## 1. 準備 input

範例提供 **2016-01-01 至 2016-01-03** 的固定 FE Walter 模擬入流，擷取自已驗收五年實驗的入流檔。`inflows.csv` 使用局部流量 m³/s，`case.json` 固定其 SHA256。
物理限制與 V3.7 相同。初始蓄水採原版 **1,992.61 acre-ft 假設值**，不是觀測值；損失設為零。下游 unit hydrograph `[1.0]` 是不延遲的測試河段，並非校正後的 routing；`live_readiness.ready` 維持 false。

`zeroshot_responses.json`、`dkp_responses.json` 清楚標示為**合成測試回覆**，每個選定日期一筆。回覆要求放流等於入流，用來測試介面；沒有模型產生這些回覆，相同結果不能證明真實 zero-shot 與 DKP 決策相同。

## 2. 選擇 YAML

使用 `experiments/fe_walter_reference_zeroshot.yaml` 或 `experiments/fe_walter_reference_dkp.yaml`。路徑以 YAML 所在目錄為基準。

這兩份使用歷史指令的測試設定，須先將 `HYDROOPS_FE_WALTER_HISTORY_DIR`
設為 repo 外恢復包的 `verified-restoration` 根目錄，再檢查或執行。
詳見[恢復索引](../../archive/fe_walter/README.md)。目前教學明確指定 prompt 檔，無須歷史恢復包。

| 設定 | 意義 |
|---|---|
| `strategy: reference_v3_7` | 選擇案例的 reference adapter |
| `mode: offline`、`max_calls: 0` | 使用測試回覆，不建立 provider、不下載、不重試 |
| `reference.profile: fe_walter` | 保留原版 FE Walter 物理／策略設定 |
| `reference.method` | `zeroshot` 或 `dkp` |
| `reference.system_prompt`／`system_prompt_mode` | 選用的 UTF-8 system 檔；`original` 核對原版文字，`custom` 標記變體。每日狀態／schema／檢索仍由 adapter 處理，見 [prompt 檔設定](../../archive/fe_walter/prompts/README.md)。 |
| `reference.responses` | 原版格式的合成回覆檔，每個選定日期恰好一筆 |
| `reference.dkp` | 僅 DKP：固定版本的 `examples/fe_walter/knowledge/operating_rules.md` |
| `prompt_storage: false` | 隱藏數值蓄水，與保存的五年 prompt 條件相同 |
| `hide_availability_line: true` | 隱藏數值可用水量上限；物理程式仍限制放流 |
| `dkp_no_missing_inputs: true` | 使用原版不含 missing-input 欄位的 DKP 變體 |
| `zeroshot_knowledge: target` | 原版公開資訊與季節目標；`wiki` 為可選的 zero-shot 變體 |
| `auditors: [release_limits]` | 保留原版 audit，另加通用放流界限檢查 |

這些旗標是明確的實驗選擇，不表示所有原版範例都如此設定；提供的原版 README 也有顯示蓄水的變體。
原版 agent 不接受通用 `prompt`、`context` 或 `response_schema` 覆寫，避免改變原始條件。自訂設計請使用 `configured`。框架使用案例自己的訊息組合與解析程式；選用的原版程式對照由 `HYDROOPS_ANIK_SOURCE_DIR` 載入並核對原始碼雜湊，見[恢復索引](../../archive/fe_walter/README.md)。

## 3. 檢查、執行、驗證

在已安裝的 repo 執行：

```powershell
python run_experiment.py check experiments/fe_walter_reference_zeroshot.yaml
python run_experiment.py run experiments/fe_walter_reference_zeroshot.yaml
python run_experiment.py verify runs/fe-walter-reference-zeroshot

python run_experiment.py check experiments/fe_walter_reference_dkp.yaml
python run_experiment.py run experiments/fe_walter_reference_dkp.yaml
python run_experiment.py verify runs/fe-walter-reference-dkp
```

`check` 驗證並固定檔案，不建立原版 policy／provider；`run` 另外確認物理限制符合原版設定。新實驗先更改 `run_id` 與 `output`，既有輸出不會被覆寫；`check` 後改變 input 也會被拒絕。

## 4. 查看結果

查看 `summary.json`、`reservoir_trajectory.csv`、`network_flows.csv`。精簡的 `audit.jsonl`、`decisions.jsonl`、`backend_events.jsonl` 指向 `raw/` 中的完整 payload，包含原版 system／state prompt、回覆 schema、測試回覆與原始 audit。
Adapter 把原版 cfs 放流轉成通用 m³/s action；物理程式實施可行放流、溢流與蓄水，下一次決策接收真正實施後的狀態。放流加溢流只注入下游 routing 一次。DKP 檢索選取規則摘錄，不會每天貼上整份 DKP。

預設原版 YAML 使用離線測試回覆，不套用 temperature；另有 [真實 LLM YAML](../../archive/README.md)，使用 `mode: llm`、`model` profile 與 temperature 0.7，不使用測試回覆檔。原版與通用真實策略都須符合既有 network／readiness／budget 限制；現有原版 case 仍未就緒。已驗收五年結果完全保留；離線 audit PASS 不代表真實策略通過，也不取代先前的 FAIL 證據。
