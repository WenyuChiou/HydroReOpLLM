# 安裝並執行第一個案例

HydroReOpLLM 需要 Python 3.12 或更新版本。從 PyPI 安裝後即可執行隨附的範例。若要使用筆記本及完整的範例與範本，請下載原始碼。首次安裝時會下載 Python 依賴套件。

<a id="install-from-pypi"></a>

## 從 PyPI 安裝

請在空白工作目錄中建立並啟用虛擬環境。

在 Windows PowerShell 中執行以下指令，讓目前的終端使用虛擬環境。

```powershell
py -3.12 -m venv .venv
$env:Path = "$PWD\.venv\Scripts;$env:Path"
```

在 macOS 或 Linux 中執行以下指令。

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

安裝套件，並將隨附的範例複製到工作目錄。

```sh
python -m pip install hydroreopllm
reservoir-experiment init-examples
```

PyPI 套件名稱是 `hydroreopllm`，Python 匯入名稱是 `llm_reservoir_agent`，命令列指令是 `reservoir-experiment`。

接著[執行離線範例](#執行離線範例)。

<a id="install-from-a-clone"></a>

## 下載並安裝原始碼

下載原始碼後，切換至專案根目錄。

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

依照[作業系統對應指令](#install-from-pypi)建立並啟用 `.venv`，再從目前的原始碼安裝套件。

```sh
python -m pip install -c environment/requirements-bundled.txt .
```

原始碼已包含 `examples/`。現在可以[執行離線範例](#執行離線範例)，或[開啟筆記本教學](../tutorials/README.zh-TW.md)。

## 執行離線範例

此範例無需 API 金鑰。保持虛擬環境啟用，並在包含 `examples/` 的目錄中執行以下指令。

```sh
reservoir-experiment check examples/daily_offline/single.yaml
reservoir-experiment run examples/daily_offline/single.yaml
reservoir-experiment verify runs/daily-single --require-offline
```

`verify` 會讀取已儲存的執行結果，並回報 `PASS`、執行 4 天及 `observed_network_calls: 0`。開啟 `runs/daily-single/summary.json`，確認 `status` 為 `COMPLETED`，且 `summary.final_storage_m3.Lake_1` 為 `1345600.0`。`reservoir_trajectory.csv` 最後一列的 `storage_end_m3` 應顯示相同數值。[結果指南](RESULTS_GUIDE.zh-TW.md)也有其他輸出檔案的說明。

<a id="repeat-a-run"></a>

## 重跑案例

在 `examples/daily_offline/single.yaml` 中，將 `run_id` 和 `output` 改成下列值。`output` 是相對於 YAML 檔案的路徑。

```yaml
run_id: daily-single-v2
output: ../../runs/daily-single-v2
```

用同一份 YAML 檔再次執行 `check` 和 `run`，再驗證新的輸出目錄。前一次的結果仍可用來比較。

```sh
reservoir-experiment verify runs/daily-single-v2 --require-offline
```
