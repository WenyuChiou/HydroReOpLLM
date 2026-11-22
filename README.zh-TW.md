# HydroReOpLLM

[繁體中文使用手冊](docs/README.zh-TW.md) · [English manual](docs/README.md) · [English](README.md)

HydroReOpLLM 使用局部入流或氣象時間序列模擬水庫操作。每個時間步先由操作策略提出放流量，再由物理模型套用庫容與放流限制，將水量往下游演算，並記錄決策和水量平衡。操作策略可採用規則、指定放流量，或讀取本地操作指引的 LLM。

## 安裝 Python 套件

在 Python 3.12 虛擬環境中，可直接從 GitHub 安裝套件。

```sh
python -m pip install "hydroreopllm @ git+https://github.com/WenyuChiou/HydroReOpLLM.git"
```

版本發布至 PyPI 後，可用 `python -m pip install hydroreopllm` 安裝。若要執行套件內附範例，請在新的資料夾執行以下指令。

```sh
python -c "import shutil, sysconfig; from pathlib import Path; shutil.copytree(Path(sysconfig.get_path('data')) / 'share/llm-reservoir-agent/examples', 'examples')"
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

## 下載與安裝

需要 Git 和 Python 3.12。首次安裝會下載 Python 相依套件。

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt .
```

macOS 或 Linux：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -c environment/requirements-bundled.txt .
```

## 執行單庫範例並驗證輸出

在倉庫根目錄，使用剛建立的虛擬環境。Windows 指令如下。

```powershell
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow check examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow run examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow verify runs/daily-single --require-offline
```

macOS 或 Linux 將上述三條指令的執行檔換成 `.venv/bin/python`。這個範例用一座合成水庫模擬四天，指定放流量為每秒 1 立方公尺，無須模型服務或 API 金鑰。結果寫入本機的 `runs/daily-single/`。重跑前請在 YAML 設定中指定新的 `output` 目錄。

## Git 專案內的範例與測試

- [使用手冊與範例驗證](docs/README.zh-TW.md)
- [可直接執行的四天合成水庫教學筆記本](tutorials/offline_synthetic.ipynb)
- [每日單庫與串聯水庫](examples/daily_offline/README.md)
- [兩座獨立操作的水庫與氣象驅動入流](examples/multiple_reservoirs/README.md)
- [逐日、逐時和固定時間步](examples/time_scales/README.md)
- [從模板建立案例](templates/prepared/README.md)

要執行測試，請在同一虛擬環境安裝測試依賴。Windows 指令如下。

```powershell
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

## 授權

HydroReOpLLM 採用 [BSD 三條款授權](LICENSE)。隨附的 HydroCNHS 保留 [Chung-Yi Lin 的 BSD 三條款授權聲明](licenses/HydroCNHS-BSD-3-Clause.txt)。[來源與修改記錄](THIRD_PARTY_NOTICES.md)
