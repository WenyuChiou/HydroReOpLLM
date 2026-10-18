# Publish or build the HTML manual

Read the [online manual](https://wenyuchiou.github.io/HydroReOpLLM/). The repository README documentation
badge and About website link lead to this site. GitHub Pages serves the HTML,
figures and original notebook downloads; source/data links still require access
to the private repository.

## GitHub Pages

On each push to `main`, the `Documentation site` workflow builds the committed
pages and saved notebook outputs, validates local links and download bytes, and
deploys only `build/docs`. It never executes notebook cells, starts Ollama or
calls a model. Maintainers can also dispatch this workflow on `main`.

The build job reads repository contents and Pages settings. Only the deployment
job receives Pages and OIDC write permissions, through the `github-pages`
environment. The source repository stays private; the rendered manual is public.

## Sharing preview

The manual publishes Open Graph and Twitter image metadata on each page.
The 1280 × 640 [preview](https://wenyuchiou.github.io/HydroReOpLLM/_static/hydroopslm-social-preview.png)
uses the selected cover without cropping. Its
[editable SVG](https://wenyuchiou.github.io/HydroReOpLLM/_static/hydroopslm-social-preview.svg)
retains the original vector artwork and HydroCNHS credit. These settings apply
to links to the public manual; they do not change the private repository's
social preview. For a fork, update `html_baseurl` in `docs/conf.py` to your own
public site URL.

## Local build

From a complete checkout, install the documentation tools and build:

```powershell
python -m pip install -e ".[docs]" -c environment/requirements-bundled.txt
python tutorials/build_notebooks.py --check
python docs/build.py
python scripts/check_docs_site.py build/docs
```

Open `build/docs/index.html`. This is the documentation-site home, with chapter
navigation, the FE Walter case and its downloadable results notebook. Notebook
downloads retain the original committed bytes.
Tables and figures come from saved MIME outputs.
MyST-NB execution is **off**: building the site does not run a simulation, start
Ollama or call a provider. Source/data links lead to the private GitHub repo and
require its normal access. The same HTML can be viewed locally or on GitHub Pages.

To refresh saved-data tables/plots separately:

```powershell
python tutorials/build_notebooks.py --execute --check
```

This reads committed evidence with network access blocked. It does not rerun the
LLM experiments. Original model replies, scientific inputs and audit verdicts
remain unchanged.

## 繁體中文

在完整 repo 使用上方安裝及建置指令，再開啟 `build/docs/index.html`。
文件站提供中英文首頁、章節目錄、FE Walter 三方法案例及結果 notebook 下載，
直接顯示保存的表格／圖片；下載檔保留已提交 notebook 的原始 bytes。
MyST-NB 不執行 cells；建置不啟動 Ollama、呼叫 provider 或執行模擬。
[線上文件站](https://wenyuchiou.github.io/HydroReOpLLM/)由 GitHub Pages 提供；README 的文件 badge 可直接進入。
原始碼／資料連結仍需私人 repo 權限。部署僅發布建置後的 HTML、圖片與 notebook，
不執行 notebook cells，也不啟動模型；repo 維持私人。
另用 `--execute --check` 更新保存資料的圖表時，網路會被封鎖，
不重跑 LLM，原始回覆、科學資料及 audit 判定不變。
The private wheel includes pinned runtime resources and the original source
notices. CI installs it separately and runs
`python -I scripts/check_installed_runtime.py`: a two-day synthetic check with
network blocked. It does not establish operating-policy performance. Keep the
repository checkout for the complete examples and tutorials; an external shared
data bundle needs an explicit YAML `case_root`.


## Branch previews

For preview source links, use `python docs/build.py --source-ref YOUR_BRANCH`, replacing `YOUR_BRANCH` with your branch name. The published manual defaults to `main`.

分支預覽可用 `--source-ref` 指定原始碼連結的版本；正式文件預設使用 `main`。
