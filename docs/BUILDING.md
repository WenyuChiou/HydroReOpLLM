# Build the HTML manual

From a complete checkout, install the documentation tools and build:

```powershell
python -m pip install -e ".[docs]" -c environment/requirements-bundled.txt
python tutorials/build_notebooks.py --check
python docs/build.py
```

Open `build/docs/index.html`. This is the documentation-site home, with chapter
navigation, three examples, single/multiple-reservoir tutorials and downloadable
notebooks. The notebook downloads retain the original committed bytes.
Tables and figures come from saved MIME outputs.
MyST-NB execution is **off**: building the site does not run a simulation, start
Ollama or call a provider. Source/data links lead to the private GitHub repo and
require its normal access. The site is a local build; it is not publicly deployed.

To refresh saved-data tables/plots separately:

```powershell
python tutorials/build_notebooks.py --execute --check
```

This reads committed evidence with network access blocked. It does not rerun the
LLM experiments. Original model replies, scientific inputs and audit verdicts
remain unchanged.

## 繁體中文

在完整 repo 使用上方安裝及建置指令，再開啟 `build/docs/index.html`。
文件站提供中英文首頁、章節目錄、三個範例、單／多水庫教學及 notebook 下載，
直接顯示保存的表格／圖片；下載檔保留已提交 notebook 的原始 bytes。
MyST-NB 不執行 cells；建置不啟動 Ollama、呼叫 provider 或執行模擬。
原始碼／資料連結仍需私人 repo 權限，文件站尚未公開部署。
另用 `--execute --check` 更新保存資料的圖表時，網路會被封鎖，
不重跑 LLM，原始回覆、科學資料及 audit 判定不變。
The private wheel includes pinned runtime resources and the original source
notices. CI installs it separately and runs
`python -I scripts/check_installed_runtime.py`: a two-day synthetic check with
network blocked. It does not establish operating-policy performance. Keep the
repository checkout for the complete examples and tutorials; an external shared
data bundle needs an explicit YAML `case_root`.
