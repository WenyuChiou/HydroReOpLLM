# HydroOpsLLM

[![使用手冊](docs/_static/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroOpsLLM/)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM 將大型語言模型的決策接入 HydroCNHS 水文模擬，用於水庫操作研究。

![HydroOpsLLM 封面](docs/figures/hydroopslm-cover.png)

HydroCNHS 計算流量，各水庫的 agent 提出放流需求，再由物理模型實施、更新蓄水並演算下游出流。實施結果供下一日決策使用。在 YAML 為每個 agent 設定 `reservoir_id` 與 `type: rule_based` 或 `type: llm`。

## 安裝

使用 Python 3.12。專案維持私人期間需要 repo 存取權。

```sh
git clone https://github.com/WenyuChiou/HydroOpsLLM.git
cd HydroOpsLLM
```

建立並啟用環境：

```sh
# Linux / macOS
python3.12 -m venv .venv
source .venv/bin/activate
```

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

```sh
python --version
python -m pip install -e . -c environment/requirements-bundled.txt
```

## 執行小型範例

這個四天的合成範例包含兩座獨立水庫，各有自己的河川出口。使用規則式操作，不需模型或 API key。

```sh
reservoir-experiment check examples/multiple_reservoirs/experiment.yaml
reservoir-experiment prepare examples/multiple_reservoirs/experiment.yaml
reservoir-experiment run examples/multiple_reservoirs/experiment.yaml
reservoir-experiment verify runs/independent-rivers-rule/operation --require-offline
```

`prepare` 先依水文模型的完整初始化期間，從氣象資料計算入流；`run` 再逐日推進水庫操作與下游演算。目前上游逕流在操作迴圈開始前準備完成。

依[建立模擬](docs/BUILD_SIMULATION.md)設定水文、水庫參數與 agent。[F.E. Walter 案例](examples/fe_walter/README.md)以同一個物理案例說明三種方法：Rule-based、LLM 與可用資訊、LLM 與檢索知識。

## 設定 LLM

每個 LLM agent 選擇 `model_profile` 與 `prompt_file`，並可在 `customization` 加入知識或 context。核心不會自動加入共用 system prompt。原生介面支援 **OpenAI、Anthropic Claude、Google Gemini 與 Ollama**，另保留 OpenAI-compatible 介面。

`check` 預覽設定與 prompt，不呼叫模型。新的 LLM 執行需明確指定 `--allow-network`。憑證、參數、重試與 fallback 設定見[模型設定](docs/USER_GUIDE.md)。

[使用手冊](https://wenyuchiou.github.io/HydroOpsLLM/)依序說明輸入準備、code 架構、原始回覆、audit 與中斷續跑。Notebook 與教學結果可直接查看，不需重新推論。

## 授權與來源

專案授權待定。HydroCNHS 保留其 [BSD 3-Clause 授權](licenses/HydroCNHS-BSD-3-Clause.txt)。另見[第三方聲明](THIRD_PARTY_NOTICES.md)及[來源與引用](docs/REFERENCE.md)。
