# HydroReOpLLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

請先開啟 [F.E. Walter 五年操作教學](operation.ipynb)。教學依序連接
2021–2025 已準備實驗：凍結水文輸入 → 共用物理案例 → 規則基準 →
兩種已準備的 LLM 方法 → 離線預檢 → 保存的基準證據。

| Notebook | 用途 |
|---|---|
| [五年操作](operation.ipynb) | 檢查目前 2021–2025 準備內容與已完成的規則基準，不執行水文、水庫操作或 LLM。 |
| [歷史 2016 操作說明](main.ipynb) | 閱讀完整設定與已驗收的 2016 教學結果。這些 LLM 曲線早於每日季節情境，不能視為五年結果。 |
| [下游驗證](downstream_validation.ipynb) | 準備 White Haven 至 Lehighton 的實測邊界檢驗，檢查輸入，再依序進行校準與獨立驗證。 |

五年與歷史 notebook 都只讀取 repository 內保存的證據；預設流程不呼叫模型、
不下載、不執行水文或水庫模擬。

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

此指令只以現有檔案執行五年操作 notebook，保留已驗收的 2016 CSV、圖表與
其他筆記本。若要以保存資料更新所有筆記本與歷史教學圖表，可省略 `--notebook`。

[通用設定](../docs/INPUT_OUTPUT.md) · [HydroCNHS 設定](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter 範例](../examples/fe_walter/README.zh-TW.md)
