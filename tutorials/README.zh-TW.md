# HydroReOpLLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

開啟 [F.E. Walter notebook 教學](main.ipynb)，依序操作同一份筆記本。
教學依序連接：實驗入口 → 已接受水文 → 水庫與網路 → agent 方法 → prompt
或檢索知識 → 保存的 2016 結果。

| Notebook | 用途 |
|---|---|
| [主教學](main.ipynb) | 逐一閱讀完整設定、檢查三種決策方法，再查看保存的全年結果。 |
| [下游驗證](downstream_validation.ipynb) | 準備 White Haven 至 Lehighton 的實測邊界檢驗，檢查輸入，再依序進行校準與獨立驗證。 |

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

[通用設定](../docs/INPUT_OUTPUT.md) · [HydroCNHS 設定](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter 範例](../examples/fe_walter/README.zh-TW.md)
