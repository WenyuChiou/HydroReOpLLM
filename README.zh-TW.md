# HydroReOpLLM

[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html) · [English](README.md)

![水庫、河川與 LLM 操作員示意圖](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM 以 HydroCNHS 為基礎，使用既有入流或集水區水文模擬，支援規則式（rule-based）或 LLM 驅動的水庫放流決策。

## 快速開始

於無須 API 金鑰的離線環境執行通用雙水庫範本（需 Python 3.12 以上版本）：

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python -m pip install -c environment/requirements-bundled.txt .
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

重複執行前請更換新的 `run_id` 與 `output`。詳見[安裝與首次執行](https://wenyuchiou.github.io/HydroReOpLLM/GETTING_STARTED.zh-TW.html)及[解讀執行結果](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.zh-TW.html)。

## 公開範例

| 入口 | 研究條件／用途 | 網路使用 |
| --- | --- | --- |
| [`examples/template/experiment.yaml`](examples/template/README.zh-TW.md) | 通用雙水庫既有入流串聯系統 | 無 |
| [`examples/fe_walter/rule_based.yaml`](examples/fe_walter/README.zh-TW.md) | **Rule-based（Hanasaki 規則）**（滯洪基準） | 無 |
| [`examples/fe_walter/seasonal_target.yaml`](examples/fe_walter/README.zh-TW.md) | **Without operational knowledge（無操作知識）**（`seasonal_target.yaml`） | 透過研究執行程式連線本機 Ollama |
| [`examples/fe_walter/dkp.yaml`](examples/fe_walter/README.zh-TW.md) | **With operational knowledge（具操作知識）**（`dkp.yaml`） | 透過研究執行程式連線本機 Ollama |

請搭配 [F.E. Walter 教學](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html)逐步操作，或閱讀 [F.E. Walter 案例指南](examples/fe_walter/README.zh-TW.md)以離線重現已發表分數。

## 測試與授權

安裝測試依賴 `python -m pip install -c environment/requirements-bundled.txt ".[test]"` 後，執行 `python -m pytest -q`。

[BSD 3-Clause 授權](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/LICENSE) · [第三方授權與來源](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/THIRD_PARTY_NOTICES.md)
