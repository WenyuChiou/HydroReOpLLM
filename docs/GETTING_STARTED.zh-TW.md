# 安裝與首次執行

<div class="hero-band" markdown="1">

HydroReOpLLM 需要 **Python 3.12 以上版本**。請依以下步驟安裝鎖定依賴的套件（PyPI 名稱 `hydroreopllm`／匯入名稱 `llm_reservoir_agent`／CLI 指令 `reservoir-experiment`），並驗證離線雙水庫範本與 F.E. Walter 範例。

</div>

## 下載並安裝原始碼

複製儲存庫、建立 Python 3.12 虛擬環境，並搭配鎖定版本清單（`environment/requirements-bundled.txt`）進行安裝：

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

若您已將建置好的 wheel 安裝至乾淨環境中，請先切換至空白工作目錄再匯出隨附範例，並於該工作目錄執行後續指令：

```sh
reservoir-experiment init-examples
```

此指令會將 `examples/template/` 與 `examples/fe_walter/` 乾淨複製到 `./examples/`（不含 `__pycache__` 殘留檔案）。

## 執行通用離線範本

通用範本執行一座雙水庫串聯系統（`upper` → `lower` → `outlet`），採用預設固定放流量，不發出任何模型請求：

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

- `check` 在不執行物理計算的前提下，驗證檔案雜湊值、日期、操作員覆蓋率與演算拓樸。
- `run` 執行 10 天的串聯操作，並將結果寫入 `runs/prepared-template/`。
- `verify --require-offline` 確認 `status: PASS`、`observed_network_calls: 0` 與水量平衡完全閉合。

接著請閱讀[通用範本欄位指南](../examples/template/README.zh-TW.md)與[解讀執行結果](RESULTS_GUIDE.zh-TW.md)。

## 檢查 F.E. Walter 範例

三份 F.E. Walter 研究設定檔皆可在離線狀態（零模型呼叫）下完成驗證：

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- 可直接使用 `reservoir-experiment run examples/fe_walter/rule_based.yaml` 執行離線 **Hanasaki** 規則基準。
- 若要執行 **Seasonal Target** 或 **DKP** 的 LLM 推論（或離線重播 21 組論文基準分數），請參閱 [F.E. Walter Dam 案例研究](../examples/fe_walter/README.zh-TW.md)或依照 [F.E. Walter 教學](../tutorials/README.zh-TW.md)逐步操作。

## 安全地重跑實驗

已完成的輸出目錄具有不可變性（`RunOutputExistsError` 會阻止覆寫既有成果）。再次執行任何實驗前，請於 `experiment.yaml` 中更換全新的 `run_id` 與尚未使用的 `output` 路徑（相對於該 YAML 檔案），重新執行 `check` 後再執行 `run` 與 `verify`。
