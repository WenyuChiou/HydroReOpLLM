# 安裝與首次執行

<div class="hero-band" markdown="1">

HydroReOpLLM 需要 **Python 3.12 以上版本**。依照下方步驟安裝套件（`hydroreopllm`／CLI 指令 `reservoir-experiment`），即可在五分鐘內完成您的第一次雙水庫離線串聯模擬。

</div>

## 下載並安裝原始碼

複製儲存庫、建立 Python 3.12 虛擬環境，並使用隨附的鎖定依賴清單（`environment/requirements-bundled.txt`）完成安裝：

<div class="panel-grid panel-grid-2" markdown="1">
<div class="panel-card" markdown="1">

### Windows PowerShell

```powershell
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -c environment/requirements-bundled.txt .
```

</div>
<div class="panel-card" markdown="1">

### macOS 或 Linux

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c environment/requirements-bundled.txt .
```

</div>
</div>

## 使用已安裝的 wheel

若您已透過 wheel 將 HydroReOpLLM 安裝在乾淨環境中，請在空白工作目錄執行以下指令以匯出隨附的 `template` 與 `fe_walter` 範例：

```sh
reservoir-experiment init-examples
```

執行後會在目前工作目錄建立 `./examples/` 資料夾。

## 執行通用離線範本

通用範本會模擬一座為期 10 天的雙水庫串聯系統（`upper` → `lower` → `outlet`），採用預設固定放流量且不呼叫任何 LLM：

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

- `check` 在不執行物理計算的前提下，驗證所有路徑、日期、水庫邊界與演算權重。
- `run` 執行模擬並將 CSV 與決策紀錄寫入 `runs/prepared-template/`。
- `verify --require-offline` 確認水量平衡閉合（`PASS`）且網路呼叫次數為 `0`。

接著請閱讀[通用範本欄位指南](../examples/template/README.zh-TW.md)與[解讀執行結果](RESULTS_GUIDE.zh-TW.md)。

## 檢查 F.E. Walter 範例

於離線狀態（零模型呼叫）檢查全部三份 F.E. Walter 研究設定檔：

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- 立即以 `reservoir-experiment run examples/fe_walter/rule_based.yaml` 執行離線 **Hanasaki** 基準。
- 若想離線重播 21 組已發表模擬，或以本機 Ollama 執行 **Seasonal Target**／**DKP**，請參閱 [F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)或 [F.E. Walter 教學](../tutorials/README.zh-TW.md)。

## 安全地重跑實驗

已完成的輸出資料夾受到保護，絕不會被覆寫。修改水庫限制、入流量或提示詞後若要重跑，請在 `experiment.yaml` 指定新的 `run_id` 與尚未使用的 `output` 目錄，再依序執行 `check`、`run` 與 `verify`。
