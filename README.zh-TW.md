# HydroCNHS + LLM Reservoir Agent

[English](README.md) | [繁體中文](README.zh-TW.md)

**HydroCNHS + LLM Reservoir Agent** 是研究大型語言模型（LLM）水庫操作決策的 Python 框架，
讓決策在耦合水文模擬中執行。以完整固定版本的 [HydroCNHS](https://github.com/cylin928/HydroCNHS)
核心為基礎，透過原有 Dam API 接入可設定的水庫決策單元。

## 可以做什麼？

- 使用原生 HydroCNHS 的降雨產流、routing、模型建立、校正與驗證（C&V）、四種耦合 API 及 sediment 工具。
- 研究 LLM 水庫決策，並與 rule-based 或自訂控制器比較；輸入、prompt、知識來源及 auditor 皆可設定。
- 在自己的河網模擬單庫或多庫，查看請求放流、實際放流、蓄水、spill、下游流量與 trace 紀錄。

## 如何運作？

HydroCNHS 使用 GWLF（Generalized Watershed Loading Functions）或 ABCD 計算降雨產流，
以 Lohmann 模型進行 routing。每座受控水庫的指定策略讀取當日狀態，透過 Dam API 提出放流。
LLM 模式將入流、水庫狀態與過去實際放流組成 prompt，也可加入額外知識。
Checker 先檢查回覆格式及數值，再由新增的共同水庫物理程式套用限制、更新蓄水及 spill。
實際放流加 spill 只注入下游 routing 一次；audit／trace 保留決策與物理結果，隔日使用實際執行歷史。

![耦合水文與水庫操作框架](docs/figures/hydrocnhs-coupling-framework-en.png)

LLM 決策會改變蓄水與下游流量，不修改原生降雨產流方程。
水庫操作入口的 rule-based 與 LLM 策略使用同一物理求解器；原生 HydroCNHS 提供 Dam 耦合介面。

## 使用手冊與教學

先依下列六步操作。[使用手冊](docs/README.zh-TW.md)集中完整設定指南、
[可執行 notebooks](tutorials/README.zh-TW.md)與[範例](examples/README.zh-TW.md)。
原生 HydroCNHS 功能請參考[官方文件站](https://cylin928.github.io/HydroCNHS/)。

## 開始使用

### 1. 安裝

使用 Python 3.12 與完整 repo。初次安裝依賴可能需要網路。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

### 2. 準備輸入

降雨產流模擬依[原生 HydroCNHS 手冊](docs/HYDROLOGY_SETUP.md)設定集水區面積、氣象資料、
參數與 routing。GWLF／ABCD、C&V、四種耦合 API 與 sediment 工具皆保留。

每日水庫操作入口使用**給定局部入流**：CSV 欄位 `date,node,local_inflow_cms`，
搭配河網、物理限制及初始蓄水。已完成上游 routing 的水庫入流，只在入口注入一次。

### 3. 設定實驗

從[範例](examples/README.zh-TW.md)選擇可執行設定，複製 YAML 後替換自己的 case。
設定 `case`、日期、`run_id` 與 `output`。每座受控水庫指定一個決策單元；被動出口
不配置 LLM。河網連線決定哪座水庫的放流會影響下游入流。

### 4. 設定決策與檢查

選擇決策 backend，各庫提供自己的 profile、規則或 prompt、輸入情境與 versioned auditor。
使用 LLM 時另設定 provider／model 與取樣參數，先做離線驗證。
[設定手冊](docs/USER_GUIDE.zh-TW.md)逐項說明欄位；[真實實驗條件](docs/LIVE_READINESS.md)列出準備要求。

### 5. 檢查、執行與驗證

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

### 6. 查看結果

開啟 `summary.json`、`reservoir_trajectory.csv`、`network_flows.csv`，以及連到 `raw/`
的 decision／physics／audit logs。比較 requested release、implemented release、spill、
蓄水與 routed flow。隔日歷史使用實際物理結果。
策略 FAIL／WARN／UNKNOWN 原樣保留；物理驗收不代表操作策略通過。

## 引用 HydroCNHS

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 6022005。
本 repo 新增 LLM 水庫整合；原版 HydroCNHS 的貢獻請另外引用。

[專案盤點](docs/PROJECT_INVENTORY.md) · [離線證據](results/technical_note_offline/README.md) ·
[Technical Note](paper/technical_note.md) · [歷史入口](archive/README.md) ·
[原版來源／授權](third_party/hydrocnhs/SOURCE.json)
