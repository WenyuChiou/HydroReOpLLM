# HydroOpsLM 逐步教學

[English](README.md) | [繁體中文](README.zh-TW.md)

依[框架 README](../README.zh-TW.md)安裝。先從 00 理解 LLM 決策路徑，
再準備輸入、設定 agents 並執行離線範例。
各 notebook 提供英文／繁體中文說明，共用可執行 cells。
Runtime prompt 保留原始英文 bytes。

| 順序 | Notebook | 查看什麼 |
|---|---|---|
| 00 | [LLM 架構](00_overview.ipynb) | Info → prompt → proposal → checker → execution、audit／trace 與 feedback |
| 01 | [輸入與地圖](01_input_and_map.ipynb) | 入流、單位、初始狀態與 GIS |
| 02 | [Agent 設定](02_yaml.ipynb) | YAML、model、prompt、knowledge 與 auditor |
| 03 | [規則基準](03_benchmark.ipynb) | 決定請求放流，使用共同物理／routing |
| 04 | [Zero-shot](04_zero_shot.ipynb) | 完整 prompt、合成回覆及決策鏈 |
| 05 | [DKP](05_dkp.ipynb) | 檢索知識、完整 prompt 及決策鏈 |
| 06 | [Audit 與 trace](06_audit_trace.ipynb) | 原判定、綁定的 physics 與實際隔日歷史 |
| 07 | [多庫／自己的資料](07_multi_and_custom.ipynb) | 河網、狀態隔離、被動出口及 31 日流量 |

[通用設定](../docs/USER_GUIDE.zh-TW.md)與[LLM 模組](../docs/LLM_MODULES.zh-TW.md)
皆為正式手冊。[範例](../examples/README.zh-TW.md)提供三種具體方法。

## 離線執行

```powershell
python tutorials/build_notebooks.py --execute
```

此命令按順序執行八課共 28 個純 Python code cells，保存實際 stdout；
不是 Jupyter kernel 測試。Builder 阻擋 HTTP／socket connect。
已有 run 僅在目前 YAML／input／implementation hashes 相符時驗證並重用；
缺少 run 才離線建立，hash 不符則停止，不覆寫。

| 方法 | check／run YAML | verify output |
|---|---|---|
| Benchmark | `examples/fe_walter/benchmark/experiment.hydroopslm.offline.yaml` | `runs/hydroopslm-fe-walter-benchmark` |
| Zero-shot | `examples/fe_walter/zero_shot/experiment.hydroopslm.offline.yaml` | `runs/hydroopslm-fe-walter-zero-shot` |
| DKP | `examples/fe_walter/dkp/experiment.hydroopslm.offline.yaml` | `runs/hydroopslm-fe-walter-dkp` |
| 31 日河網 | `tutorials/config/multi_reservoir.hydroopslm.offline.yaml` | `runs/hydroopslm-three-reservoir-31d-v2` |

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.hydroopslm.offline.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.hydroopslm.offline.yaml
python run_experiment.py verify runs/hydroopslm-fe-walter-zero-shot --require-offline
```

其他方法替換成表中路徑。已有 output 會拒絕；
請 verify，或使用新的 ID／output。FE 範例涵蓋 2016-01-01–03。

## 查看完整決策

離線範例存在後，不重跑模擬即可查看某日：

```powershell
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-zero-shot
python tutorials/inspect_decision_flow.py runs/hydroopslm-fe-walter-dkp --timestep 1
```

Inspector 先驗證離線證據，再顯示 **info、完整 system／user prompt、合成回覆、
正規化 proposal、action 契約重檢、原 audit、已提交物理、隔日 info 與 trace 路徑**。
重檢是當次執行，不捏造歷史 checker event。04／05 另展示拒絕負值 proposal，
不呼叫物理程式或改寫已存狀態。Checker、策略 audit 與物理平衡分別呈現。

通用固定放流 offline backend 跳過 prompt／模型。
兩個參考 offline 案例會組合 prompt 並解析給定回覆；
全部回覆是合成資料，不能衡量真實 LLM 策略品質。

## 使用自己的資料與設計實驗

Excel 匯出不含 BOM 的 UTF-8 CSV：`date,node,local_inflow_cms`、
ISO 日期、m³/s，並記錄 SHA256。此 FE 資料是已完成上游 routing 的模擬
水庫入流，只加入一次。原生 runoff 設定由手冊連結。

2016 年一月河網中，FE Walter／Beltzville 匯入 Lehigh contributions，
Prompton 在 Lackawaxen contributions 使用被動出口。這不是串聯或完整河流流量。
`UH=[1]` 驗證連接，不是校正旅行時間。07 教學說明自己的 case；
測試涵蓋串聯、匯流與延遲。

比較方法時，固定共用輸入、初始狀態、物理與 routing。
改變 prompt／knowledge／auditor 時更新版本並保存新 run。
真實 provider 實驗前請讀[真實實驗條件](../docs/LIVE_READINESS.md)。

[先前 Demo](https://github.com/WenyuChiou/HydroCNHS-Delaware-Demo) ·
[地圖來源](../data/figures/SOURCES.md) · [可編輯圖](../docs/figures/source/README.md)
