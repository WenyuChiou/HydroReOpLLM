# F.E. Walter 水庫

兩個範例共用七天的合成入流和同一份水庫設定，示範如何搭配同一個本機 Ollama 模型執行兩種每日放流策略。Prompt 採用教學案例的設定及套件的 JSON 動作格式。

| 案例 | 設定檔 | System prompt | 每日 prompt |
| --- | --- | --- | --- |
| 季節目標（Seasonal Target） | [seasonal_target.yaml](seasonal_target.yaml) | [季節目標 system prompt](prompts/seasonal_target.system.txt) | [季節目標每日 prompt](prompts/seasonal_target.user.txt) |
| 決策知識套件（DKP） | [dkp.yaml](dkp.yaml) | [DKP system prompt](prompts/dkp.system.txt) | [DKP 每日 prompt](prompts/dkp.user.txt) |

DKP 案例另外提供[在地操作指引](dkp.md)。兩個案例共用相同的季節目標與[準備好的入流](case.json)。

## 檢查兩份設定

在專案根目錄，或套件匯出的 `examples/` 上一層目錄，執行下列指令。

```shell
reservoir-experiment check examples/fe_walter/seasonal_target.yaml
reservoir-experiment check examples/fe_walter/dkp.yaml
```

檢查會驗證輸入並預覽 prompt，模型呼叫數為零。

## 用本機 Ollama 執行

請啟動已有 `gemma4:12b` 的 Ollama 服務。兩個 YAML 都預設連到 `http://127.0.0.1:11434`。若本機使用另一個連接埠或模型標籤，請在兩份設定檔調整 `models.local.base_url` 或 `models.local.model`。

```shell
reservoir-experiment run examples/fe_walter/seasonal_target.yaml --allow-network
reservoir-experiment run examples/fe_walter/dkp.yaml --allow-network
reservoir-experiment verify runs/fe-walter-seasonal-target
reservoir-experiment verify runs/fe-walter-dkp
```

重跑時請使用新的 `run_id` 和 `output`。可在 `decisions.jsonl` 和 `physics.jsonl` 查看放流請求與實際放流，在 `provider_attempts.jsonl` 查看送出的訊息。

[跟著教學操作兩個案例](https://wenyuchiou.github.io/HydroReOpLLM/tutorials/index.zh-TW.html)
