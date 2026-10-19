# HydroReOpLLM 教學

[English](README.md) | [繁體中文](README.zh-TW.md)

先讀 [F.E. Walter 設定教學](fe_walter.md)，再開啟[主 notebook](main.ipynb)。
教學依序連接：實驗入口 → 已接受水文 → 水庫與網路 → agent 方法 → prompt
或檢索知識 → 保存的 2016 結果。

| Notebook | 用途 |
|---|---|
| [主教學](main.ipynb) | 用保存全年資料比較 **Rule-based**、**未使用知識檢索的 LLM** 與 **使用知識檢索的 LLM**。 |

Notebook 只讀取 repository 內保存的證據；預設流程不呼叫模型、不下載、不執行
水文或水庫模擬。

## 建置與檢查

```powershell
python tutorials/build_notebooks.py --execute
python tutorials/build_notebooks.py --check
```

Builder 也會在 `examples/fe_walter/coupled/outputs/current_tutorial/` 產生教學
CSV 與一張合併操作圖；水位與放流單圖仍保留為次要匯出檔。它只合併保存資料，
檢查日期、入流、初始狀態與單位，不作插值。曲線沿用來源執行所記錄的 prompt 與
context；建置教學不會加入新的每日或即時日期 context。

[通用設定](../docs/INPUT_OUTPUT.md) · [HydroCNHS 設定](../docs/HYDROLOGY_SETUP.md) ·
[F.E. Walter 範例](../examples/fe_walter/README.zh-TW.md)
