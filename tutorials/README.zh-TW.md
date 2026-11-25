# F.E. Walter 提示詞教學

此筆記本使用 F.E. Walter 論文案例的前七天入流，對 Rule-based、With operational knowledge 與 Without operational knowledge 執行離線 `check`，並顯示兩個 LLM 案例使用的系統提示詞與每日提示詞。預設流程不會發出模型請求。

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab
python -m jupyterlab tutorials/fe_walter.ipynb
```

請從儲存庫根目錄開啟筆記本，並選擇已安裝 HydroReOpLLM 的環境。預設儲存格會顯示：

1. 三個設定共用的論文入流與 2021 年 1 月 1–7 日的教學期間；
2. 兩個 LLM 設定各自選用的提示詞檔案；
3. With operational knowledge 設定中的 `knowledge.fe_walter_operating_guidance` 參照；以及
4. 三個入口皆通過離線設定檢查。

最後的儲存格會列印一條 Rule-based 離線指令和兩條可自行執行的 Ollama 指令。請先檢閱提示詞、以 `gemma4:12b` 啟動 Ollama、指定新的輸出路徑，並確認接受 `--allow-network` 所代表的本機網路使用，再手動執行。筆記本本身不會進行即時推論。

選擇執行前，請先閱讀 [F.E. Walter 指南](../examples/fe_walter/README.zh-TW.md)及[執行生命週期](../docs/RUNNING.zh-TW.md)。
