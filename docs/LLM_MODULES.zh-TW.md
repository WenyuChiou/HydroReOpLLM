# 選擇操作策略與模型

可以先用指定放流建立可重跑的基準，再改用規則或 LLM。在相同案例上比較兩種策略時，保留相同的入流、初始庫容、時間步長與物理限制，每次使用獨立的輸出目錄。

## 先驗證規則，再檢查 LLM 設定

```sh
reservoir-experiment check examples/daily_offline/single.mosart.yaml
reservoir-experiment run examples/daily_offline/single.mosart.yaml
reservoir-experiment verify runs/daily-single-mosart --require-offline
reservoir-experiment check examples/multiple_reservoirs/experiment.llm.yaml
```

最後一行會檢查混合操作案例的設定與預估呼叫需求。要真的呼叫模型，還需讓指定的模型服務可連線，並在執行時明確加入 `--allow-network`。

## 保存可重現的設定

相同的模型標籤可能在不同時間指向不同權重。保存實際載入模型的 digest、量化方式、執行服務版本、取樣參數、seed、prompt 與操作知識文件。各提供者支援的識別與固定方式請見[模型服務章節](MODEL_PROVIDERS.md)。
