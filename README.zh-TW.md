# HydroOpsLM

[English](README.md) | [繁體中文](README.zh-TW.md)

**HydroOpsLM** 是在耦合水文模擬中研究 LLM 水庫操作的模組化 Python 框架。
以完整固定版本的 [HydroCNHS](https://github.com/cylin928/HydroCNHS) 核心為基礎，
透過原有 Dam API 接入水庫決策單元。Python 套件名稱維持 `llm_reservoir_agent`。

## 可以做什麼？

- 設定每個 LLM 看見的資訊、prompt、模型、選用知識與 auditor。
- 使用共同水庫物理，比較 LLM、規則與自訂決策。
- 連接單庫或多庫，查看放流、蓄水與下游流量。
- 從決策輸入與 proposal，追查實際執行結果及 audit／trace。

原生 HydroCNHS 的模型建立、水文、routing、校正與驗證（C&V）、
四種耦合 API 及 sediment 工具皆保留。

## 如何運作？

可用資訊與獨立 prompt，加上選用的額外內容，送入 LLM。
Response parser 將回覆轉為 **proposal：請求的受控放流量**。
Checker 檢查格式與數值，再由共同水庫物理計算實際放流、spill 與蓄水。
實際總出流只注入下游 routing 一次；執行結果回饋到下一次決策。

![HydroOpsLM：HydroCNHS 與模組化 LLM 水庫決策](docs/figures/hydrocnhs-coupling-framework-en.png)

HydroOpsLM 是框架名稱；圖中標題說明它的兩個組成部分：
HydroCNHS 與 LLM 水庫 agent。

Audit 評估指定的操作規則；trace 保存輸入、決策、來源與物理結果。
Action 有效不代表策略已通過驗收。HydroCNHS 負責水文與 routing；
LLM 改變水庫決策、蓄水及下游流量。各介面見[LLM 模組手冊](docs/LLM_MODULES.zh-TW.md)。

## 開始使用

### 1. 安裝

使用 Python 3.12 與完整 repo。初次安裝依賴可能需要網路。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

### 2. 選擇離線設定

從[範例](examples/README.zh-TW.md)開始，依其 YAML 與教學操作。
每日操作入口需要河網、水庫初始狀態，以及給定的局部入流 CSV：
`date,node,local_inflow_cms`。已完成上游 routing 的水庫入流，只在入口注入一次。

### 3. 檢查、執行與驗證

將以下路徑換成選用的離線 YAML 及其中設定的輸出目錄。

```powershell
$experiment = "path/to/experiment.yaml"
$output = "runs/your-experiment"
python run_experiment.py check $experiment
python run_experiment.py run $experiment
python run_experiment.py verify $output --require-offline
```

`check` 不呼叫 provider。已有輸出不會覆寫：
使用 verify，或指定新的 `run_id` 與 `output`。
[逐步 notebooks](tutorials/README.zh-TW.md)展示完整流程。

## 設定你的 agent

每座受控水庫配置一個獨立決策單元；被動出口不配置 LLM。
依[設定手冊](docs/USER_GUIDE.zh-TW.md)設定資訊、prompt、選用知識、模型及版本化 auditor。
[模組手冊](docs/LLM_MODULES.zh-TW.md)區分固定設定與逐日變動的資訊。
目前操作入口使用 daily timestep。

## 設計實驗與查看結果

比較決策方法時，固定入流、初始狀態、物理與 routing。
每次只改變一個明確列出的條件，保存新的 run，並保留 prompt／model／audit 版本。
河網連線決定哪座水庫的放流會影響下游入流。
真實 provider 實驗前，依[多庫與自己的資料](tutorials/07_multi_and_custom.ipynb)
及[真實實驗準備清單](docs/LIVE_READINESS.md)完成準備。

查看 `reservoir_trajectory.csv`、`network_flows.csv` 與 `summary.json`。
以 decision ID 串起 decision、physics、audit logs，再進入 `raw/` 查看完整 prompt／回覆證據。
比較 requested／implemented release、spill、蓄水及 routed flow；保留 FAIL／WARN／UNKNOWN。

[使用手冊](docs/README.zh-TW.md) · [逐步教學](tutorials/README.zh-TW.md) ·
[原生 HydroCNHS 設定](docs/HYDROLOGY_SETUP.md) ·
[HydroCNHS 官方文件](https://cylin928.github.io/HydroCNHS/)

## 來源與引用

Lin, C. Y., Yang, Y. C. E., & Wi, S. (2022).
[HydroCNHS: A Python Package of Hydrological Model for Coupled Natural Human Systems](https://doi.org/10.1061/(ASCE)WR.1943-5452.0001630).
*Journal of Water Resources Planning and Management*, 148(12), 6022005。
HydroOpsLM 新增 LLM 水庫整合；原版 HydroCNHS 的貢獻請另外引用。

[專案盤點](docs/PROJECT_INVENTORY.md) · [離線證據](results/technical_note_offline/README.md) ·
[Technical Note](paper/technical_note.md) · [歷史入口](archive/README.md) ·
[原版來源／授權](third_party/hydrocnhs/SOURCE.json)
