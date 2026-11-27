# 實作導向教學課程（Hands-On Curriculum）

透過循序漸進的實作課程快速掌握 **HydroReOpLLM**。每個模組皆遵循一致的 **設定（Configure）→ 操作（Operate）→ 實際執行（Execute）→ 判讀與繪圖（Inspect & Plot）** 學習節奏，提供**預先執行**的 Jupyter Notebook——全程**離線執行**（`0` 網路呼叫）且僅寫入系統暫存資料夾，您可直接於 GitHub 瀏覽完整數值與圖表，或在本地一鍵重跑而不汙染專案目錄。

## 五大模組實作課綱

| 模組 | 主題 | 學習路徑（設定 → 操作 → 執行 → 看到結果） | 指南與筆記本 |
| --- | --- | --- | --- |
| **01** | **環境設定與首次離線規則基準** | 檢視 F.E. Walter `rule_case.json` 與 `inflows.csv`，執行 2021 全年 Hanasaki 規則（`365` 天），以 `verify_run` 驗證水量平衡並繪製水位與放流對照圖。 | [模組指南](01_setup_and_first_run/README.md) · [Notebook](01_setup_and_first_run/01_setup_and_rule_baseline.ipynb) |
| **02** | **LLM 提示詞、結構化格式與操作知識（DKP）** | 對照 `seasonal_target.yaml`（無操作知識）與 `dkp.yaml`（含操作知識），檢視第 1 天提示詞、JSON Schema 與 `dkp.md` 規則檢索，離線重播 2021 並對照 USGS `01447780` 與 `01447800` 計算 KGE/RMSE。 | [模組指南](02_prompt_and_knowledge_design/README.md) · [Notebook](02_prompt_and_knowledge_design/02_llm_prompt_and_knowledge.ipynb) |
| **03** | **集水區水文、10 年率定驗證與 HydroCNHS 耦合** | 載入台灣新店溪 4 子集水區（`U1, U2, D1, D2`）`hydrology.yaml` 與 `forcing.csv.gz`，驗證無重複計量入流綁定、檢視 10 年率定驗證（`2016–2025`）並繪製 2025 日歷線與月水量平衡。 | [模組指南](03_watershed_hydrology_and_cv/README.md) · [Notebook](03_watershed_hydrology_and_cv/03_hydrocnhs_cv_and_coupling.ipynb) |
| **04** | **多水庫混合串聯操作（新店溪翡翠 → 直潭）** | 設定 `feitsui → zhitan → xindian_outlet`、Lohmann 單位歷線與經濟部水利署 36 旬運用規線，離線執行雙規則基準與混合 LLM 聯合調度重播，驗證演算捲積並繪製 2025 三面板結果對照翡翠水庫管理局（TFRA）觀測。 | [模組指南](04_multi_reservoir_hybrid_cascade/README.md) · [Notebook](04_multi_reservoir_hybrid_cascade/04_xindian_hybrid_cascade.ipynb) |
| **05** | **ODD+LLM 協議、可重現性與稽核軌跡** | 檢視 `odd_llm_manifest.json`（區塊 A–E）、驗證 SHA-256 軌跡、以 `export-odd` 匯出論文級 ODD+LLM Markdown 報告，並執行離線重播與質量平衡稽核。 | [模組指南](05_odd_llm_reproducibility_and_audit/README.md) · [Notebook](05_odd_llm_reproducibility_and_audit/05_odd_llm_reproducibility.ipynb) |
| **整合版** | **F.E. Walter 全流程單一筆記本** | 涵蓋系統架構、2021 論文 Figure 3 重播、提示詞設計、串聯案例預覽與選用本機 Ollama 實機執行（`RUN_LLM = True`）。 | [Notebook (`fe_walter.ipynb`)](fe_walter.ipynb) |

## 安裝與啟動 JupyterLab

請先[下載並安裝 HydroReOpLLM](../docs/GETTING_STARTED.zh-TW.md)，啟用 `.venv` 後從專案根目錄啟動 JupyterLab（所有筆記本無論從根目錄、`tutorials/` 或各模組資料夾開啟，都會自動偵測專案根目錄）：

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab ipykernel
python -m jupyterlab tutorials/01_setup_and_first_run/01_setup_and_rule_baseline.ipynb
```

1. 在右上角核心選單選擇 `.venv` Python 核心（若未顯示，執行一次註冊指令：`python -m ipykernel install --user --name hydroreopllm --display-name "Python (.venv HydroReOpLLM)"`）。
2. 點選 **Run → Run All Cells**。所有模組預設全程離線執行（`0` 網路呼叫），且僅寫入 `tempfile.TemporaryDirectory()`。

## 延伸閱讀與完整案例

- **研究案例與 Ollama 實機設定**：[單一水庫案例（F.E. Walter）](../examples/fe_walter/README.zh-TW.md)、[多水庫串聯案例（新店溪）](../examples/multi_reservoir/README.zh-TW.md)。
- **技術手冊**：[入流與 HydroCNHS 設定](../docs/HYDROLOGY_SETUP.zh-TW.md)、[實驗設定檔](../docs/CONFIGURATION.zh-TW.md)、[規則與 LLM 提示詞設計](../docs/AGENT_DESIGN.zh-TW.md)、[多水庫網路](../docs/MULTI_RESERVOIR.zh-TW.md)與[結果判讀與水量平衡](../docs/RESULTS_GUIDE.zh-TW.md)。
