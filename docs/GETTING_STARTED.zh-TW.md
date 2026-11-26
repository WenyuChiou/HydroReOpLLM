# 安裝與 CLI 指令

<div class="hero-band" markdown="1">

HydroReOpLLM 需要 **Python 3.12 以上版本**。安裝套件（`hydroreopllm`／CLI 指令 `reservoir-experiment`）後，即可直接離線檢查並執行內建的單一水庫與多水庫案例。

</div>

<a id="install-from-a-clone"></a>

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

若在空白工作目錄透過 wheel 安裝，請先匯出隨附範例資料夾（`examples/fe_walter/` 與 `examples/multi_reservoir/`）：

```sh
reservoir-experiment init-examples
```

## CLI 指令總覽

| 指令 | 用途 |
| --- | --- |
| `reservoir-experiment init-examples` | 將內建公開範例匯出至目前目錄的 `examples/`（或指定新資料夾）。 |
| `reservoir-experiment check` | 離線驗證 `<config>` 的路徑、日期、物理限制、河網與第 1 天提示詞預覽。 |
| `reservoir-experiment prepare` | 僅限耦合 HydroCNHS：先跑集水區水文模式並輸出 `inflows.csv`。 |
| `reservoir-experiment run` | 執行模擬並將結果寫入全新資料夾（即時 LLM 須加 `--allow-network`）。 |
| `reservoir-experiment verify` | 查核 `<output>` 的水量平衡、河道演算、水情時序（可加 `--require-offline`）。 |
| `reservoir-experiment resume` | 由 `--from-run` 重播已完成步驟，並以新 `--output` 與 `--run-id` 接續跑完。 |

## 快速執行範例指令

### 單一水庫案例（F.E. Walter）

先離線執行 **Rule-based（Hanasaki 規則）** 基準，並檢查兩組 LLM 設定檔：

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

- 欲離線重播論文結果，或以本機 Ollama 執行 **Without operational knowledge（無操作知識）** 與 **With operational knowledge（具操作知識）**，請參閱[單一水庫案例（F.E. Walter）](../examples/fe_walter/README.zh-TW.md)與[互動式 Notebook 教學](../tutorials/README.zh-TW.md)。

### 多水庫串聯案例（新店溪：翡翠水庫 → 直潭壩）

離線執行 2020 年 5 月梅雨期間新店溪串聯水庫（`feitsui` → `zhitan` → `xindian_outlet`）的雙庫 Hanasaki 基準，並檢查上游翡翠 Hanasaki＋下游直潭 LLM 的混合設定：

```sh
reservoir-experiment check examples/multi_reservoir/rule_based.yaml
reservoir-experiment run examples/multi_reservoir/rule_based.yaml
reservoir-experiment verify runs/multi-reservoir-rule-based --require-offline
reservoir-experiment check examples/multi_reservoir/hybrid_llm.yaml
```

- 詳細欄位與河道延遲說明見[多水庫串聯案例](../examples/multi_reservoir/README.zh-TW.md)，輸出表格判讀見[結果判讀與水量平衡](RESULTS_GUIDE.zh-TW.md)。

## 安全地重跑實驗

已完成的輸出資料夾受到保護，不會被覆寫。修改水庫物理限制、入流或提示詞後，請在設定檔更換新的 `run_id` 與尚未使用的 `output` 路徑，再依序執行 `check`、`run` 與 `verify`。
