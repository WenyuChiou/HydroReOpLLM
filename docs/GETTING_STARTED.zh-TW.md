# 安裝與首次執行

<div class="hero-band" markdown="1">

HydroReOpLLM 需要 **Python 3.12 以上版本**。安裝套件（`hydroreopllm`／CLI `reservoir-experiment`）後，幾分鐘內即可跑通雙水庫入門範本。

</div>

## 下載並安裝原始碼

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

若在空白工作目錄透過 wheel 安裝，請先匯出隨附範例：

```sh
reservoir-experiment init-examples
```

## 執行雙水庫入門範本

以零次 LLM 呼叫執行 10 天雙水庫串聯系統（`upper` → `lower` → `outlet`）：

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

- `check` 於離線狀態檢查檔案、日期、上下限與演算設定。
- `run` 將模擬 CSV 與決策日誌寫入 `runs/prepared-template/`。
- `verify --require-offline` 確認水量平衡閉合（`PASS`）且網路呼叫為 `0`。

接著可閱讀[雙水庫入門範本](../examples/template/README.zh-TW.md)與[結果判讀與水量平衡](RESULTS_GUIDE.zh-TW.md)。

## 檢查 F.E. Walter 水庫案例

離線檢查全部三種 F.E. Walter 研究條件（`0` 次模型呼叫）：

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- 立即執行 `reservoir-experiment run examples/fe_walter/rule_based.yaml` 即可跑通離線 **Rule-based（Hanasaki 規則）** 基準。
- 依 [F.E. Walter 水庫案例](../examples/fe_walter/README.zh-TW.md)或 [F.E. Walter 互動教學](../tutorials/README.zh-TW.md)可離線重播 21 組論文模擬，或以本機 Ollama 執行 **Without operational knowledge（無操作知識）**／**With operational knowledge（具操作知識）**。

## 安全地重跑實驗

已完成的輸出資料夾不會被覆寫。修改水庫物理限制、入流或提示詞後，請在 `experiment.yaml` 更換新的 `run_id` 與未使用的 `output`，再依序執行 `check`、`run` 與 `verify`。
