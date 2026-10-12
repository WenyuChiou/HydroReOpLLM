# HydroCNHS + LLM Reservoir Agent

[English](README.md) | [繁體中文](README.zh-TW.md)

耦合水文與水庫操作模擬框架，以完整固定版本 HydroCNHS 為基礎，透過原有 Dam API
加入可設定的決策單元。HydroCNHS 計算產流與 routing；決策單元提出放流；共同水庫物理
程式執行限制、更新蓄水與計算 spill。Audit／trace 記錄決策及其實際物理結果。

![耦合水文與水庫操作框架](docs/figures/hydrocnhs-coupling-framework-en.png)

## 1. 安裝

使用 Python 3.12 與完整 repo。初次安裝依賴可能需要網路。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

## 2. 準備輸入

降雨產流模擬依[原生 HydroCNHS 手冊](docs/HYDROLOGY_SETUP.md)設定集水區面積、氣象資料、
參數與 routing。GWLF／ABCD、C&V、四種耦合 API 與 sediment 工具皆保留。

每日水庫操作入口使用**給定局部入流**：CSV 欄位 `date,node,local_inflow_cms`，
搭配河網、物理限制及初始蓄水。已完成上游 routing 的水庫入流，只在入口注入一次。

## 3. 設定實驗

從[範例](examples/README.zh-TW.md)選擇可執行設定，複製 YAML 後替換自己的 case。
設定 `case`、日期、`run_id` 與 `output`。每座受控水庫指定一個決策單元；被動出口
不配置 LLM。河網連線決定哪座水庫的放流會影響下游入流。

## 4. 設定決策與檢查

選擇決策 backend，各庫提供自己的 profile、規則或 prompt、輸入情境與 versioned auditor。
使用 LLM 時另設定 provider／model 與取樣參數，先做離線驗證。
[設定手冊](docs/USER_GUIDE.zh-TW.md)逐項說明欄位；[真實實驗條件](docs/LIVE_READINESS.md)列出準備要求。

## 5. 檢查、執行與驗證

將下列兩個路徑換成自己的 YAML 及其中指定的輸出資料夾。

```powershell
$experiment = "path/to/experiment.yaml"
$output = "runs/your-experiment"
python run_experiment.py check $experiment
python run_experiment.py run $experiment
python run_experiment.py verify $output --require-offline
```

`check` 不呼叫 provider。已有輸出不會覆寫：使用 verify，或指定新的 `run_id` 與 `output`。
完整可執行示範請依[逐步 notebooks](tutorials/README.zh-TW.md)操作。

## 6. 查看結果

開啟 `summary.json`、`reservoir_trajectory.csv`、`network_flows.csv`，以及連到 `raw/`
的 decision／physics／audit logs。比較 requested release、implemented release、spill、
蓄水與 routed flow。隔日歷史使用實際物理結果。LLM 決策改變蓄水與下游流量，不修改產流方程。
策略 FAIL／WARN／UNKNOWN 原樣保留；物理驗收不代表操作策略通過。

[專案盤點](docs/PROJECT_INVENTORY.md) · [離線證據](results/technical_note_offline/README.md) ·
[Technical Note](paper/technical_note.md) · [歷史入口](archive/README.md) ·
[原版來源／授權](third_party/hydrocnhs/SOURCE.json)
