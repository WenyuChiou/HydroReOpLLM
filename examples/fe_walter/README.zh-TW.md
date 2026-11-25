# 重現 F.E. Walter 研究結果

| 研究條件 | 設定 | System prompt | 1 月 1 日的 user message |
| --- | --- | --- | --- |
| Rule-based | [rule_based.yaml](rule_based.yaml) | | |
| Without operational knowledge | [seasonal_target.yaml](seasonal_target.yaml) | [Seasonal Target](prompts/seasonal_target.system.txt) | [Seasonal Target 第一天](prompts/seasonal_target.user.txt) |
| With operational knowledge | [dkp.yaml](dkp.yaml) | [DKP](prompts/dkp.system.txt) | [DKP 第一天](prompts/dkp.user.txt) |

三個案例都使用 2021 年 1 月 1 日至 2025 年 12 月 31 日的[模擬入流](inflows.csv)。[每日訊息程式](study/formatter.py)以當天的水庫狀態和前兩天的決策與實際放流組裝 prompt。With 組還會從完整的 [Decision Knowledge Package](dkp.md) 擷取符合當天條件的章節。[回覆格式](study/response_schemas.json)列出原始決策欄位和放流單位。兩組 LLM 共用[水庫設定](case.json)。MOSART-Urban 基準使用自己的[論文設定](rule_case.json)及 [1996–2015 年的參考入流統計](rule_statistics.json)。

## 離線重算論文分數

請在專案根目錄或匯出已安裝範例的目錄執行以下指令。

```sh
python examples/fe_walter/study/replay.py --output runs/walter-paper-replay
```

程式以封存的每日放流決策重跑水庫和河道，涵蓋兩組 LLM 各十個 seed。程式也重跑 MOSART-Urban 基準，並以原始 USGS 觀測驗證 21 組模擬的 KGE 與 RMSE。`01447780` 是水庫水位，`01447800` 是壩下放流的代理流量，`01449000` 是 Lehighton 的下游流量。各組分數可在 `scores.csv` 查看。水庫水位的中位數為 With 組的 KGE 0.858、NSE 0.711，以及 Without 組的 KGE 0.806、NSE 0.514。重播會發出零次模型請求。[教學 notebook](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb)可查看存檔中的前七天結果。

## 用論文模型重新推論

使用 Ollama 0.40.6。安裝程式會從公開的 Ollama registry 取得固定版本的模型檔，逐一驗證檔案大小和 SHA-256。下載約需 7.6 GB。研究執行程式會在推論前後核對 Ollama 版本和 Gemma 4 12B 的 manifest。

```sh
python examples/fe_walter/study/model.py .walter-ollama
```

另開一個終端，在同一目錄啟動伺服器。PowerShell 指令如下。

```powershell
$env:OLLAMA_MODELS = (Resolve-Path .walter-ollama).Path
$env:OLLAMA_HOST = "127.0.0.1:11446"
ollama serve
```

macOS 或 Linux 可執行以下指令。

```sh
OLLAMA_MODELS="$PWD/.walter-ollama" OLLAMA_HOST=127.0.0.1:11446 ollama serve
```

可以先跑七天教學，或加上 `--full` 跑完整 1,826 天。要做全組比較，將兩個 LLM 條件各跑 seed 1 至 10，每次指定新的輸出目錄。不同平台重新推論可能有差異。要精確重算論文分數，可用上面的離線重播。

```sh
python examples/fe_walter/study/run.py rule_based --full --output runs/walter-rule
python examples/fe_walter/study/run.py seasonal_target --full --seed 3 --ollama-port 11446 --output runs/walter-without-s3 --allow-network
python examples/fe_walter/study/run.py dkp --full --seed 3 --ollama-port 11446 --output runs/walter-with-s3 --allow-network
```
