# HydroReOpLLM

[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html) · [English](README.md)

![水庫、河川與 LLM 操作員示意圖](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM 以 HydroCNHS 為基礎，使用既有入流資料模擬水庫操作，並支援指定放流量或由 LLM 作出的放流決策。

## 快速開始

從此原始碼版本執行無須 API 金鑰的通用既有入流範本。系統需要 Python 3.12 或更新版本。

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

再次執行前，請設定新的 `run_id` 與 `output`。詳見[安裝與首次執行](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-TW.html)及[結果指南](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.zh-TW.html)。

## 公開範例

| 入口 | 用途 | 網路使用 |
| --- | --- | --- |
| [`examples/template/experiment.yaml`](examples/template/README.zh-TW.md) | 通用雙 agent 合成入流流程 | 無 |
| [`examples/fe_walter/rule_based.yaml`](examples/fe_walter/README.zh-TW.md) | F.E. Walter 離線 Hanasaki 規則 | 無 |
| [`examples/fe_walter/seasonal_target.yaml`](examples/fe_walter/README.zh-TW.md) | F.E. Walter **Without operational knowledge**（只用季節目標） | 透過研究執行程式連線本機 Ollama |
| [`examples/fe_walter/dkp.yaml`](examples/fe_walter/README.zh-TW.md) | F.E. Walter **With operational knowledge**（加入決策知識包 DKP） | 透過研究執行程式連線本機 Ollama |

[開啟線上 F.E. Walter 教學](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html)。

請先執行 `reservoir-experiment check`。此指令可在不連線 Ollama 的情況下驗證任一 F.E. Walter 設定。三個 F.E. Walter 設定都使用論文的 2021–2025 年入流，預設先跑七天。[案例指南](examples/fe_walter/README.zh-TW.md)說明如何離線重算論文分數，以及如何還原原始模型重新推論。

## 測試與授權

在下載的專案中，以 `python -m pip install -c environment/requirements-bundled.txt ".[test]"` 安裝測試依賴，再執行 `python -m pytest -q`。

[BSD 3-Clause 授權](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [第三方授權與來源](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
