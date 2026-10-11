# LLM Reservoir Agent

[English](README.md) | [繁體中文](README.zh-TW.md)

完整 HydroCNHS，加上可設定的 LLM 水庫 agent，用於 daily 實驗。
HydroCNHS 負責水文與 routing；agent 提議放流，物理程式更新蓄水、限制放流並計算溢流。
YAML 執行器使用給定的 daily 入流，不重新執行 GWLF／ABCD，也不更改已校正參數。

原生 HydroCNHS 支援集水區面積、水文／routing 參數與校正工具，使用原生模型設定與 Python API；水庫 YAML 執行器尚未包成一鍵 calibration／validation 流程。詳見 [水文設定與 C&V](docs/HYDROLOGY_SETUP.md)。

![HydroCNHS 加上 LLM 水庫決策層](docs/figures/hydrocnhs-llm-concept-zh-TW.png)

## 1. 安裝

使用 Python 3.12，完整取得此 repo，然後在 repo 目錄執行：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e . -c environment/requirements-bundled.txt
```

## 2. 先跑離線範例

```powershell
python run_experiment.py check experiments/synthetic_cascade.yaml
python run_experiment.py run experiments/synthetic_cascade.yaml
python run_experiment.py verify runs/synthetic-cascade
```

此範例為四天、三個水庫，使用固定測試放流，不呼叫 LLM。程式不覆寫已存在的輸出目錄；新實驗請修改 `run_id` 與 `output`。

## 3. 設定自己的案例

1. 在 case JSON 準備水庫網路、物理參數與初始蓄水。
2. 準備 daily 局部入流 CSV：`date,node,local_inflow_cms`，單位 m³/s。若來源是 Excel，整理這三欄並匯出不含 BOM 的 UTF-8 CSV；程式不直接讀 `.xlsx`。更新 case 中的 CSV SHA256。
3. 複製有註解的 [實驗 YAML](experiments/fe_walter.yaml)，設定 case 路徑、輸出與 agents。一個受控水庫配置一個 agent；被動出口水庫不需要 agent。
4. 每個 agent 指定水庫 ID、prompt、DKP 檔、model profile 與 auditors。檔案路徑以 YAML 所在目錄為基準。
5. 使用自己的 YAML 路徑，依序執行上述 `check`、`run`、`verify`。

| 要修改的內容 | 設定位置 |
|---|---|
| Agents、日期、模型／選項、輸出、auditor 選擇 | `experiments/*.yaml` |
| 位置、連線、物理限制、初始狀態、入流 CSV／hash | `cases/` 下的 case JSON |
| Agent 指令 | `prompt` → `prompts/` 下的 UTF-8 template |
| DKP／操作規則 | `knowledge` → 自己的 UTF-8 檔，例如放在 `knowledge/` |
| 選用的靜態輸入 | Agent 設定中的 `context` 或 `context_file` |

Prompt 檔提供 user 指令；backend 固定 system JSON 回覆契約。模型提議放流，auditor 檢查所設定的規則，物理程式實施可行放流。

## 4. 使用 LLM

選擇 `models` profile，設定 `mode: llm`，移除離線用的 `release_cms`，並設定 `max_calls`。先執行 `check`。真實請求還需要 `--allow-network` 與已具備實驗條件的 case；執行器不下載模型。

[單水庫](experiments/fe_walter.yaml) · [FE Walter／Beltzville／被動 Prompton](experiments/fe_belt_prompton.yaml) · [LLM 設定範例](experiments/synthetic_llm.yaml)

## 5. 查看結果

`summary.json`：執行狀態、audit 統計與水量平衡誤差；`reservoir_trajectory.csv`：放流與蓄水；`network_flows.csv`：下游流量。精簡 log 指向 `raw/` 中的完整證據。Audit PASS 只表示所選規則通過，不能視為操作策略已核准。

完整操作步驟與各項設定：[User guide／完整操作手冊](docs/USER_GUIDE.md)。
研究結果：[已保存結果](results/README.md)。進階 API 與歷史重現：[進階流程](docs/ADVANCED_WORKFLOWS.md)。固定 HydroCNHS 原始碼與授權：[Source manifest](third_party/hydrocnhs/SOURCE.json)。

FE Walter 的 DKP 策略 audit：[七天離線示範與真實實驗前缺口](cases/fe_walter_dkp_offline/README.md)。此案例不呼叫 LLM；缺少策略輸入時維持 UNKNOWN。

真實三水庫案例仍有 live-readiness 缺口。Repo 保留既有科學結果與原始 audit 判定。
