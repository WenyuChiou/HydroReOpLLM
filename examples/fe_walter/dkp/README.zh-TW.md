# HydroOpsLM FE Walter — DKP

[English](README.md) | [繁體中文](README.zh-TW.md) · [完整原版設定](../../../cases/fe_walter_reference/README.zh-TW.md)

本例由 HydroOpsLM 執行每日 Dam API、水庫物理與下游 routing。策略相容 adapter 提供 prompt、回覆解析與策略 audit；下一日使用實際物理結果。詳見[三方法共用執行鏈](../README.zh-TW.md)。

這是HydroOpsLM 水庫 agent 框架的一個具體案例。
使用原版 DKP 策略與**合成離線回覆**，尚未呼叫真實 LLM。

1. Input：共用的 [case JSON](../../../cases/fe_walter_reference/case.json)、[daily 入流 CSV](../../../cases/fe_walter_reference/inflows.csv) 與 [測試回覆](../../../tests/fixtures/dkp_responses.json)。
2. 設定：有註解的 [experiment.hydroopslm.offline.yaml](experiment.hydroopslm.offline.yaml)，1 個 FE Walter agent，daily 2016-01-01 至 2016-01-03，`mode: offline`、`max_calls: 0`。
3. Prompt：YAML 實際讀取 `prompts/` 中的 [system 指令](../../../prompts/fe_walter_reference/dkp_system.txt)。[prompt_preview.txt](prompt_preview.txt) 包含完整原版英文 system prompt、第一天狀態 prompt 與回覆 schema。它是**閱讀快照**，不是執行用 template。原版 builder 每天產生當日狀態與歷史，並檢索相關 DKP 摘錄。
4. 知識：原版 [DKP v1.2](../../../data/anik_v3_7/DKP_FEWalter_Dam_v1.2.md) 與依情境選取的規則摘錄。
5. Audit：保留原版策略 audit，另外使用通用放流界限 auditor。兩者均不改寫模型的放流要求；共用物理程式負責實施可行放流。
6. 在已安裝的 repo 根目錄執行：

```powershell
python run_experiment.py check examples/fe_walter/dkp/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/dkp/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-dkp --require-offline
```

7. 結果：查看 `summary.json`、`reservoir_trajectory.csv`、`network_flows.csv`、`audit.jsonl` 與 `raw/`。這組放流等於入流的測試回覆，預期為 3 天、0 次模型呼叫、3 次 audit PASS、水庫水量平衡殘差 0 m³。這是依據已保存離線診斷的預期檢查值，並非新生成的模型決策。

**假設與限制：**初始蓄水採原版假設 1,992.61 acre-ft，損失設為零，下游河段 `[1.0]` 為不延遲的測試 routing；真實實驗就緒狀態為 false。新一輪執行須更改 `run_id` 與 `output`。修改閱讀快照不會改變執行；若要更廣泛地自訂 prompt／狀態格式，請使用通用 `configured` 策略。另有保留相同原版策略的 [真實 LLM YAML](experiment.llm.yaml)，見 [準備教學](../../../docs/reference_live.zh-TW.md)；現有 case 仍阻擋真實執行。修改 system 指令時，複製檔案並設 `reference.system_prompt_mode: custom`，trace 會標記為變體；`original` 模式核對文字是否與原版 builder 一致。

通用合成 prompt template 放在 `tests/fixtures/prompts/`；舊根目錄檔案保留供歷史相容。本案例保留原版英文 prompt，不翻譯執行時的指令文字。測試回覆的 audit PASS 不代表真實操作策略已通過。

System prompt SHA256：`c018043ce34a6e47024024ce63622d837dffa686a15523eb97d4bdd4ae678352`。共用資料與原始 vendor 程式 bytes 維持不變。

策略來源：Anik V3.7。原版 prompt／schema／檢索與 vendor hashes 供相容性核對；本例的模擬入口為本 repo 的 `run_experiment.py`。

## 查看完整決策

離線輸出存在後，執行以下唯讀檢視，或依[教學 04／05](../../../tutorials/README.zh-TW.md)：

```powershell
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-dkp
```

依序查看 info、prompt variables、完整 system／user prompt、合成回覆、正規化 proposal、action 契約重檢、原 audit、實際放流及隔日 info。Checker 重檢不是捏造歷史事件；原 FAIL／WARN／UNKNOWN 保留，實際放流由共同物理計算。原 experiment.tutorial.yaml 及其歷史結果保留，新入口使用獨立 HydroOpsLM run。
