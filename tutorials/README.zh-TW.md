# HydroReOpLLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

開啟 [F.E. Walter notebook 教學](main.ipynb)，依序操作同一份筆記本。
教學依序連接：實驗入口 → 已接受水文 → 水庫與網路 → agent 方法 → prompt
或檢索知識 → 保存的 2016 結果。

| Notebook | 用途 | 資料與模型服務 |
|---|---|---|
| [主教學](main.ipynb) | 逐一閱讀完整設定、檢查三種決策方法，再查看保存的全年結果。 | 只讀取已提交的保存結果；不需要模型服務。 |
| [操作](operation.ipynb) | 由氣象計算 F.E. Walter 入流，以 Hanasaki 規則操作 2021–2025，並與觀測比較。 | 氣象、已校正模型與觀測都在 repository 內；全部在本機計算，不需要模型服務。 |
| [進階](advanced.ipynb) | 閱讀通用的 `examples/multiple_reservoirs` 設定：ID、拓樸、方法混用與狀態分離。 | 讀取 `examples/multiple_reservoirs` 的檔案；不執行模擬，不需要模型服務。 |
| [下游驗證](downstream_validation.ipynb) | 準備 White Haven 至 Lehighton 的實測邊界檢驗，檢查輸入，再依序進行校準與獨立驗證。 | 預設只檢查輸入；下載、原生試算與校準各需明確開啟開關；不需要模型服務。 |

主 notebook 只讀取 repository 內保存的證據；預設流程不呼叫模型、不下載、不執行
水文或水庫模擬。

下游 notebook 預設只檢查輸入準備。下載、原生固定參數試算與校準都需明確開啟各自的開關；教學內沒有 LLM 執行。

## 開啟 notebook

先在本機 clone 中完成[安裝](../docs/GETTING_STARTED.md)，再從 repository 根目錄
使用該 Python 環境開啟教學：

```powershell
python -m pip install jupyterlab
jupyter lab tutorials/main.ipynb
```

選擇已安裝套件的環境作為 notebook kernel，依序執行各 cell。
完整設定解釋與可執行程式統一維護在 notebook 中。

## 建置與檢查

```powershell
python tutorials/build_notebooks.py --notebook main.ipynb --execute
python tutorials/build_notebooks.py --check
```

此指令只以現有檔案執行主 notebook，保留已驗收的 CSV、圖表匯出與進階筆記本。
若要以保存資料更新所有筆記本與圖表，可省略 `--notebook`。保存軌跡沿用來源執行
當時的 prompt，產生時間早於每日季節資訊的加入。

CI 執行 `python tutorials/build_notebooks.py --execute --check`。它在同一個行程內，
以保存的證據並封鎖網路，重新產生並執行 `main.ipynb` 與 `advanced.ipynb`。
發布的 `operation.ipynb` 只包含教學原始碼。在 Jupyter 依序執行即可查看表格與圖，
也可用 `--notebook operation.ipynb --execute` 在本機驗算。
`downstream_validation.ipynb` 則獨立執行。

[通用設定](../docs/INPUT_OUTPUT.md) · [HydroCNHS 設定](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter 範例](../examples/fe_walter/README.zh-TW.md)
