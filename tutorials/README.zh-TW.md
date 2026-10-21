# HydroReOpLLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

請先開啟 [F.E. Walter 五年操作教學](operation.ipynb)。教學依序連接
2021–2025 實驗：讀取設定 → 由氣象計算入流 → 規則法操作水庫 →
檢查水量平衡 → 繪製這次執行的結果。

| Notebook | 用途 |
|---|---|
| [五年操作](operation.ipynb) | 實際執行水文與規則基準，查看逐日進度，再繪製水位與下游流量。 |
| [歷史 2016 操作說明](main.ipynb) | 閱讀完整設定與已驗收的 2016 教學結果。這些 LLM 曲線早於每日季節情境，不能視為五年結果。 |
| [下游驗證](downstream_validation.ipynb) | 準備 White Haven 至 Lehighton 的實測邊界檢驗，檢查輸入，再依序進行校準與獨立驗證。 |

五年教學以空白輸出交付，讓使用者逐格執行本機 CPU 模擬。它沿用已接受的
輸入與參數，直接用新結果呼叫繪圖函數，不呼叫 LLM 或下載資料。
歷史 notebook 繼續讀取保存的證據。

下游 notebook 預設只檢查輸入準備。下載、原生固定參數試算與校準都需明確開啟各自的開關；教學內沒有 LLM 執行。

## 開啟 notebook

先在本機 clone 中完成[安裝](../docs/GETTING_STARTED.md)，再從 repository 根目錄
使用該 Python 環境開啟教學：

```powershell
python -m pip install jupyterlab
jupyter lab tutorials/operation.ipynb
```

選擇已安裝套件的環境作為 notebook kernel，依序執行各 cell。
完整設定解釋與可執行程式統一維護在 notebook 中。

## 建置與檢查

```powershell
python tutorials/build_notebooks.py --notebook operation.ipynb --execute
python tutorials/build_notebooks.py --check
```

第一個指令會實際執行水文與規則法教學，將輸出寫入新的
`runs/fe-walter-tutorial-*` 資料夾，保留既有研究結果。
省略 `--notebook` 的完整建置會以保存資料執行歷史教學，並將五年操作教學
保留為空白輸出，供使用者自行執行。

[通用設定](../docs/INPUT_OUTPUT.md) · [HydroCNHS 設定](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter 範例](../examples/fe_walter/README.zh-TW.md)
