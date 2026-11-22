# HydroReOpLLM 使用手冊

[English manual](README.md) · [專案首頁](../README.zh-TW.md)

HydroReOpLLM 可以從既有的入流資料開始，也可以讓 HydroCNHS 依氣象資料計算來水。每個時間步，操作策略先根據入流與水庫狀態提出放流量。水庫模組再依可用水量與出口限制計算實際放流、溢流及期末庫容。比較策略時，請分別檢查策略要求的放流量與實際放流量。

## 第一次執行

準備 Git 和 Python 3.12，在終端機下載主庫。

```sh
git clone https://github.com/WenyuChiou/HydroReOpLLM.git
cd HydroReOpLLM
```

Windows PowerShell 可直接執行以下指令。首次安裝需要網路，單庫範例可以離線執行。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c environment/requirements-bundled.txt .
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow check examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow run examples/daily_offline/single.yaml
.\.venv\Scripts\python.exe -m llm_reservoir_agent.workflow verify runs/daily-single --require-offline
```

macOS 或 Linux 請用 `python3.12 -m venv .venv` 建立環境，接著把上述安裝及模擬指令的 Python 執行檔改為 `.venv/bin/python`。

## 如何判斷這次有跑對

`check` 會列出預計執行的步驟和模型呼叫次數。這個範例預計呼叫模型 0 次。`run` 會在 `runs/daily-single/` 產生結果。`verify` 應回報 `PASS`，實際網路呼叫次數為 0。

打開 `reservoir_trajectory.csv`，應能看到 2020 年 2 月 28 日至 3 月 2 日共四筆日資料。每天的控制放流量都是 1 m³/s，水量平衡殘差為 0，最後一天的期末庫容為 1,345,600 m³。這組數值對應隨附的合成單庫範例。要保留原結果並重跑，請在設定檔中指定新的 `output` 目錄。

## 換成自己的案例

耦合範例執行完成後，可用 `reservoir-experiment verify runs/independent-rivers-rule --require-offline`
驗證整個輸出目錄。若只要檢查水庫操作，可指定其下的 `operation/`。執行 `prepare` 後，還需要完成 `run` 才能驗證操作結果。

已有逐日模型回覆時，可用 `llm-reservoir-daily` 重播，再對重播輸出執行 `verify --require-offline`。
驗證器會比對保存的來源雜湊、日期與要求放流量，並檢查重播期間的模型服務呼叫次數是否為零。完整指令見[執行手冊](RUNNING.md#replay-saved-daily-responses)。

| 你要做的事 | 從這裡開始 |
| --- | --- |
| 輸入已有的入流序列 | [入流資料與設定範本](../templates/prepared/README.md) |
| 從降雨及氣溫模擬入流 | [HydroCNHS 設定](HYDROLOGY_SETUP.md) |
| 比較單庫、串聯或獨立操作的多座水庫 | [單庫與串聯範例](../examples/daily_offline/README.md)、[多庫手冊](MULTI_RESERVOIR.md) |
| 切換逐時、逐日或固定時段 | [時間尺度與單位](TIME_SCALES.md) |
| 改用 LLM，記錄模型權重與執行設定 | [模型服務與可重現性](MODEL_PROVIDERS.md) |
| 中斷後續跑，或檢查驗證錯誤 | [執行與續跑](RUNNING.md)、[疑難排解](TROUBLESHOOTING.md) |

模型服務指南列出追蹤本機模型所需的權重雜湊、量化方式與推論服務版本。如果要重現某次實驗，請連同該次使用的設定、提示詞和輸入檔一起保存。
