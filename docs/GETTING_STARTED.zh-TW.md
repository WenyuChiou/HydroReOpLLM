# 安裝並執行第一個案例

HydroReOpLLM 需要 Python 3.12 或更新版本。目前的原始碼版本包含本手冊介紹的公開範本與 F.E. Walter 範例。

<a id="install-from-a-clone"></a>

## 下載並安裝原始碼

建立並啟用虛擬環境，再安裝目前的原始碼版本。

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

依照作業系統建立並啟用虛擬環境。

Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS 或 Linux

```sh
python3.12 -m venv .venv
source .venv/bin/activate
```

接著安裝目前的原始碼。

```sh
python -m pip install -c environment/requirements-bundled.txt .
```

PyPI 套件名稱為 `hydroreopllm`，Python 匯入名稱為 `llm_reservoir_agent`，命令列指令為 `reservoir-experiment`。由目前原始碼建置的 wheel 包含本手冊列出的範例。較早的 PyPI 版本可能使用不同的範例路徑。

## 使用已安裝的 wheel

安裝由目前原始碼建置的 wheel 後，切換到空白工作目錄，再匯出套件內的範例。

```sh
reservoir-experiment init-examples
```

指令會建立 `examples/`。請留在包含該目錄的工作目錄，再執行下列指令。

## 執行通用離線範本

此範本由兩個 agent 操作串聯水庫，無須 API 金鑰或模型伺服器。請在儲存庫根目錄或包含已匯出範例的工作目錄執行。

```sh
reservoir-experiment check examples/template/experiment.yaml
reservoir-experiment run examples/template/experiment.yaml
reservoir-experiment verify runs/prepared-template --require-offline
```

`check` 會驗證路徑、日期、資料雜湊、操作員與物理水系。`verify` 會讀取已儲存的證據，結果應為 `PASS` 且 `observed_network_calls: 0`。接著可閱讀[範本欄位指南](../examples/template/README.zh-TW.md)與[結果指南](RESULTS_GUIDE.zh-TW.md)。

## 檢查 F.E. Walter 範例

三份設定皆可在不發出模型請求的情況下檢查。

```sh
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

Rule-based 可用 `reservoir-experiment run examples/fe_walter/rule_based.yaml` 離線執行。兩個 LLM 案例可依研究指南還原指定的 Ollama 模型，再用研究執行程式重跑。[F.E. Walter 範例指南](../examples/fe_walter/README.zh-TW.md)提供提示詞連結與完整研究期間的執行方式。

## 重跑案例

每個已完成的輸出皆不可變更。請複製案例目錄或編輯自己的工作副本，再設定新的 `run_id` 與尚未使用的 `output`。所有路徑皆相對於 YAML 檔案解析。再次執行 `run` 前，請先執行 `check`，完成後再驗證新的輸出目錄。
