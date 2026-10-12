# Daily 水庫逐步教學

[English](README.md) | [繁體中文](README.zh-TW.md)

先完成首頁安裝，再從 00 依序開啟 notebook。每份都有目標、環境、步驟、檢查與下一步。
Notebook 內文採英文；本頁與中文設定手冊提供中文入口。

| 順序 | Notebook |
|---|---|
| 00 | [Architecture / 原版與升級架構](00_overview.ipynb) |
| 01 | [Input and GIS / 入流與地圖](01_input_and_map.ipynb) |
| 02 | [YAML and agents / 設定與 agent](02_yaml.ipynb) |
| 03 | [Rule benchmark / 規則基準](03_benchmark.ipynb) |
| 04 | [Zero-shot](04_zero_shot.ipynb) |
| 05 | [DKP](05_dkp.ipynb) |
| 06 | [Audit and trace](06_audit_trace.ipynb) |
| 07 | [Multiple reservoirs and own data / 多庫與自己的資料](07_multi_and_custom.ipynb) |

## 不開 notebook server 也能離線執行

```powershell
python tutorials/build_notebooks.py --execute
```

這會依序執行純 Python cell，保存實際 stdout；不是 Jupyter kernel 驗證。
八份 nbformat 4 notebook 共 23 個 code cell，也能用 notebook server 開啟。
已有 run 會驗證並重用，不存在的 run 才會離線建立。

這些是本 repo 的 HydroCNHS 使用範例。[FE Walter 入口](../examples/fe_walter/README.zh-TW.md)
說明共同模擬執行鏈，以及策略來源與框架執行各自的責任。

## 逐一執行各方法

| 方法 | check／run YAML | verify 輸出 |
|---|---|---|
| Benchmark | `examples/fe_walter/benchmark/experiment.yaml` | `runs/fe-walter-benchmark-tutorial` |
| Zero-shot | `examples/fe_walter/zero_shot/experiment.tutorial.yaml` | `runs/fe-walter-tutorial-zeroshot` |
| DKP | `examples/fe_walter/dkp/experiment.tutorial.yaml` | `runs/fe-walter-tutorial-dkp` |
| 31 日多庫 | `tutorials/config/multi_reservoir.offline.yaml` | `runs/three-reservoir-tutorial-31d` |

```powershell
python run_experiment.py check examples/fe_walter/zero_shot/experiment.tutorial.yaml
python run_experiment.py run examples/fe_walter/zero_shot/experiment.tutorial.yaml
python run_experiment.py verify runs/fe-walter-tutorial-zeroshot --require-offline
```

其他方法代入表中路徑。命令不覆寫已有輸出；已有 run 使用 `verify`，新實驗改 IDs／output。
Notebook 重用另核對目前 YAML、input 與實作 hashes。不一致時停止，要求新 IDs／output；
歷史 `verify` 檢查的是已保存的證據。
FE 三方法期間是 2016-01-01–03；多庫是 2016 年 1 月。

Input CSV 為 `date,node,local_inflow_cms`。Excel 先匯出無 BOM 的 UTF-8 CSV，使用
ISO 日期與 m³/s，在 case 記錄 SHA256。FE 入流是已完成上游 routing 的模擬入流，
不能再次 routing 或重複注入。完整自然產流使用[原生水文設定](../docs/HYDROLOGY_SETUP.md)，再接水庫操作。

多庫中 FE Walter 與 Beltzville 在 Lehigh 支流貢獻合流；Prompton 被動出口屬 Lackawaxen
支流貢獻。這不是三壩串聯，也不是 Delaware 全河流量。`UH=[1]` 驗證連通性，不代表
校正過的傳遞時間；07 與測試另涵蓋真正串聯、合流、延遲與河道蓄水。

原[Demo 教學](https://github.com/WenyuChiou/HydroCNHS-Delaware-Demo)保留為來源參考；本教學
沿用 input → setup → run → results 順序與固定 GIS。
[地圖來源](../data/figures/SOURCES.md) · [圖源與重製](../docs/figures/source/README.md)
