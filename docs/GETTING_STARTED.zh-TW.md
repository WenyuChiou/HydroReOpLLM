# 安裝並執行第一個案例

HydroReOpLLM 需要 Python 3.12 或以上版本。請先在空的工作目錄中建立虛擬環境。若使用 Windows PowerShell，請執行以下指令。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

在 Linux 或 macOS 上，請使用 `python3.12 -m venv .venv` 與 `source .venv/bin/activate`。
接著從 PyPI 安裝套件，並將隨附範例複製到工作目錄中。

```sh
python -m pip install hydroreopllm
python -c "import shutil, sysconfig; from pathlib import Path; shutil.copytree(Path(sysconfig.get_path('data')) / 'share/llm-reservoir-agent/examples', 'examples')"
```

套件隨附的範例集包含離線逐日案例及其本機規則。若下載原始碼專案，還會包含耦合案例範本、時間尺度範例以及筆記本教學。

若要取得最新的原始碼、教學與案例範本，請依循[下載與安裝說明](../README.zh-TW.md#下載與安裝)，並[使用原始碼虛擬環境執行範例](../README.zh-TW.md#執行單庫範例並驗證輸出)。兩種安裝方式皆已包含 HydroCNHS。

## 執行離線範例

```powershell
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

輸出目錄必須尚未存在。重複執行範例前，請先修改 `run_id` 與 `output`。成功執行後，`runs/daily-single` 目錄內會建立 `summary.json`、決策日誌與物理日誌、`reservoir_trajectory.csv`、`network_flows.csv` 與 `network_balance.csv`。`verify --require-offline` 會讀取這些檔案，確認該次執行紀錄的模型服務呼叫次數為 0，而不會重新執行案例。

接著請閱讀[設定檔說明](CONFIGURATION.zh-TW.md)、[決策時可用資訊](INFORMATION.zh-TW.md)與[結果判讀指南](RESULTS_GUIDE.zh-TW.md)。[筆記本教學](../tutorials/README.zh-TW.md)也提供同一個離線案例的逐步操作說明。
