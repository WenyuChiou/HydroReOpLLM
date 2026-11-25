# HydroReOpLLM

[![繁體中文使用手冊](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/docs-badge-zh-TW.svg)](https://wenyuchiou.github.io/HydroReOpLLM/zh-TW.html) · [English manual](https://wenyuchiou.github.io/HydroReOpLLM/) · [English](README.md)

![水庫、河川與 LLM 操作員示意圖](https://wenyuchiou.github.io/HydroReOpLLM/assets/branding/cover.png)

HydroReOpLLM 使用局部入流量或氣象時間序列模擬水庫操作。在每個時間步，先由操作策略提出放流量，再由物理模型套用庫容與放流限制，將水量往下游演算，並記錄決策與水量平衡。操作策略可採用規則、指定放流量，或讀取本機操作指引的 LLM。

## 模擬如何運作

入流量可來自現成的時間序列，也可由 HydroCNHS 根據氣象資料計算。在每個時間步，操作員讀取可用狀態與操作知識後提出放流量。物理模型執行放流、計算溢流量與期末庫容，串聯網路則將上游出流量傳遞至下游節點。

| 想嘗試的功能 | 從這裡開始 |
| --- | --- |
| 追蹤指定放流量如何影響單庫與下游水庫 | [單庫與串聯水庫](https://wenyuchiou.github.io/HydroReOpLLM/examples/daily_offline/index.zh-TW.html) |
| 用氣象資料計算兩座獨立操作水庫的入流量 | [雙水庫耦合範例](https://wenyuchiou.github.io/HydroReOpLLM/examples/multiple_reservoirs/index.zh-TW.html) |
| 確認模型可讀取哪些資料，並記錄所用版本 | [決策時可用的資訊](https://wenyuchiou.github.io/HydroReOpLLM/INFORMATION.zh-TW.html)與[模型服務](https://wenyuchiou.github.io/HydroReOpLLM/LLM_MODULES.zh-TW.html) |
| 建立自己的案例並解讀結果 | [設定檔](https://wenyuchiou.github.io/HydroReOpLLM/CONFIGURATION.zh-TW.html)與[結果指南](https://wenyuchiou.github.io/HydroReOpLLM/RESULTS_GUIDE.zh-TW.html) |

## 安裝 Python 套件

啟用 Python 3.12 虛擬環境後，從 PyPI 安裝已發布的套件。

```sh
python -m pip install hydroreopllm
```

在空資料夾中複製套件隨附的範例，接著執行並驗證四天的單庫模擬。

```sh
python -c "import shutil, sysconfig; from pathlib import Path; shutil.copytree(Path(sysconfig.get_path('data')) / 'share/llm-reservoir-agent/examples', 'examples')"
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

## 下載與安裝

若要取得最新原始碼、教學筆記本與案例範本，請使用 Git 下載預設分支。首次安裝時會下載 Python 相依套件。

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

Windows PowerShell。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt .
```

macOS 或 Linux。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -c environment/requirements-bundled.txt .
```

## 執行單庫範例並驗證輸出

在專案根目錄中使用剛建立的虛擬環境，Windows 指令如下。

```powershell
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow check examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow run examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow verify runs/daily-single --require-offline
```

macOS 或 Linux 請將上述三個指令的執行檔改為 `.venv/bin/python`。此範例以一座合成水庫模擬四天，指定放流量為每秒 1 立方公尺，無須模型服務或 API 金鑰。結果會寫入本機的 `runs/daily-single/`。重新執行前，請先在 YAML 設定檔中指定新的 `output` 目錄。

## Git 專案內的範例與測試

- [使用手冊與範例驗證](docs/README.zh-TW.md)
- [可直接執行的四天合成水庫教學筆記本](tutorials/offline_synthetic.ipynb)
- [逐日單庫與串聯水庫](examples/daily_offline/README.zh-TW.md)
- [兩座獨立操作的水庫與氣象驅動入流量](examples/multiple_reservoirs/README.zh-TW.md)
- [逐日、逐時與固定時間步長](examples/time_scales/README.zh-TW.md)
- [從範本建立案例](templates/prepared/README.zh-TW.md)

若要執行測試，請在同一虛擬環境中安裝測試相依套件，Windows 指令如下。

```powershell
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

## 授權

HydroReOpLLM 採用 [BSD 三條款授權](LICENSE)。隨附的 HydroCNHS 保留 [Chung-Yi Lin 的 BSD 三條款授權聲明](licenses/HydroCNHS-BSD-3-Clause.txt)。[來源與修改紀錄](THIRD_PARTY_NOTICES.md)
