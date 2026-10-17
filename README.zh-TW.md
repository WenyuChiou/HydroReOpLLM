# HydroOpsLLM

[![使用手冊](docs/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroOpsLLM/)

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM 在 HydroCNHS 上加入可設定的 LLM 水庫操作功能。

![HydroOpsLLM 封面](docs/figures/hydroopslm-cover.png)

HydroCNHS 計算流量；每個水庫 agent 提出放流需求；物理模型執行該決策、更新蓄水量，並將出流向下游遞送。執行後的狀態再提供給下一日決策。

## 從這裡開始

1. **安裝。** 使用 Python 3.12 與 repository 鎖定的相依套件版本。專案為私人 repository 期間，需要存取權限。

   ```sh
   git clone https://github.com/WenyuChiou/HydroOpsLLM.git
   cd HydroOpsLLM
   python3.12 -m venv .venv
   source .venv/bin/activate
   python -m pip install -e . -c environment/requirements-bundled.txt
   ```

   在 Windows PowerShell 中，先以 `py -3.12 -m venv .venv` 與 `.venv\Scripts\Activate.ps1` 建立並啟用環境，再執行相同的安裝指令。

2. **檢查目前的實驗設定。**

   ```sh
   reservoir-experiment check examples/fe_walter/coupled/current/experiment.yaml
   ```

   `check` 會驗證設定並預覽 prompts，不會執行水文模擬或呼叫模型。請由[輸入與設定](docs/INPUT_OUTPUT.md)了解實驗、水文、水庫、agent 與模型檔案。

3. **依序閱讀 [F.E. Walter 教學](tutorials/fe_walter.md)。** 教學以同一個物理案例比較三種操作方法：**Rule-based**、**LLM with available information** 與 **LLM with retrieved knowledge**。[主 notebook](tutorials/main.ipynb)只讀取 repository 內已提交的證據，不會呼叫模型。

4. **查看[已儲存的結果](examples/fe_walter/results.zh-TW.md)。** 這些結果與圖表可供檢視，不需要重新執行推論或水文模擬。

若要查看小型通用網路，另見選讀的[多水庫範例](examples/multiple_reservoirs/experiment.yaml)。

## 決策方法

請為每個 agent 設定 `reservoir_id`，並選擇 `type: rule_based` 或 `type: llm`。Rule-based agent 會載入已註冊的規則模組；Hanasaki 是 F.E. Walter 範例選用的模組，並非框架的必要條件。LLM agent 會選擇 `model_profile` 與 `prompt_file`，也可在 `customization` 中加入 context 或檢索知識。核心不會自動加入共用 system prompt，但案例 extension 可明確組合一個 system prompt。

[使用手冊](https://wenyuchiou.github.io/HydroOpsLLM/)說明研究建置、模型供應商設定、已儲存回覆、稽核與中斷後續跑。

## 授權與引用

專案授權待定。HydroCNHS 保留其 [BSD 3-Clause 授權](licenses/HydroCNHS-BSD-3-Clause.txt)。另見[第三方軟體聲明](THIRD_PARTY_NOTICES.md)與[來源及引用](docs/REFERENCE.md)。
