# F.E. Walter 水庫

Rule-based 基準與兩個 LLM 案例共用 F.E. Walter 論文案例的每日模擬入流、初始蓄水量和下游演算參數。預設期間為 2021 年 1 月 1 日至 7 日，方便先熟悉流程再跑完整期間。

| 案例 | 設定檔 | System prompt | 每日 prompt |
| --- | --- | --- | --- |
| Rule-based | [rule_based.yaml](rule_based.yaml) | — | — |
| Without operational knowledge（只用季節目標） | [seasonal_target.yaml](seasonal_target.yaml) | [季節目標 system prompt](prompts/seasonal_target.system.txt) | [季節目標每日 prompt](prompts/seasonal_target.user.txt) |
| With operational knowledge（加入 DKP） | [dkp.yaml](dkp.yaml) | [DKP system prompt](prompts/dkp.system.txt) | [DKP 每日 prompt](prompts/dkp.user.txt) |

兩個 LLM 案例共用季節目標。**With operational knowledge** 也會把[在地操作指引](dkp.md)放進每日提示詞。三個設定共用[水庫及河網設定](case.json)。[入流 CSV](inflows.csv)收錄 2021-01-01 至 2025-12-31 共 1,826 天的 GWLF 模擬入流，包含水庫上游入流，以及 White Haven 和 Lehighton 的區間逕流。流量單位為 m³/s。案例設定以 SHA-256 鎖定這份 CSV。

## 檢查三份設定

在專案根目錄，或套件匯出的 `examples/` 上一層目錄，執行下列指令。

```shell
reservoir-experiment check examples/fe_walter/rule_based.yaml
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

檢查會驗證輸入並預覽 prompt，模型呼叫數為零。

## 離線執行 Rule-based

Hanasaki 規則使用模擬開始前的 [1996–2015 年 F.E. Walter 入流統計](rule_statistics.json)。公開規則的實作與論文封存規則有所不同。

```shell
reservoir-experiment run examples/fe_walter/rule_based.yaml
reservoir-experiment verify runs/fe-walter-rule-based --require-offline
```

## 使用本機 Ollama 執行 LLM 案例

請啟動已有 `gemma4:12b` 的 Ollama 服務。兩個 YAML 都預設連到 `http://127.0.0.1:11434`。若本機使用另一個連接埠或模型標籤，請在兩份設定檔調整 `models.local.base_url` 或 `models.local.model`。

```shell
reservoir-experiment run examples/fe_walter/seasonal_target.yaml --allow-network
reservoir-experiment run examples/fe_walter/dkp.yaml --allow-network
reservoir-experiment verify runs/fe-walter-seasonal-target
reservoir-experiment verify runs/fe-walter-dkp
```

重跑時請使用新的 `run_id` 和 `output`。可在 `decisions.jsonl` 和 `physics.jsonl` 查看放流請求與實際放流，在 `provider_attempts.jsonl` 查看送出的訊息。

## 執行完整研究期間

在每份 YAML 中保留 `start_date` 為 `'2021-01-01'`，將 `end_date` 改為 `'2025-12-31'`。Rule-based 的 `max_calls` 保持 `0`。兩個 LLM 案例則將 `max_calls` 設為 `3652`，每天最多允許兩次模型請求。設定新的 `run_id` 和 `output` 後，即可用上面的指令檢查和執行。

公開 LLM 案例使用 SI 單位的提示詞、精簡版操作指引及目前的模擬器。論文封存實驗使用 V3.7 後端、原始提示詞，以及 Ollama 0.40.6 上的 Gemma，模型 manifest 的 SHA-256 為 `4eb23ef187e2c5462566d6a1d3bbbc2f1346d0b4327cbb66d58fffbcc9b2b05c`。公開設定產生的結果應視為新的模擬結果。

[跟著教學操作三個設定](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html)
