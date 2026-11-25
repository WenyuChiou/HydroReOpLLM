# F.E. Walter 提示詞教學

此筆記本使用 F.E. Walter 論文案例的前七天入流，比較 Seasonal Target 與 DKP。它會讀取兩份 YAML 與各自具名的系統、使用者提示詞，再對兩個案例執行離線 `check`。預設流程不會發出模型請求。

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab
python -m jupyterlab tutorials/fe_walter.ipynb
```

請從儲存庫根目錄開啟筆記本，並選擇已安裝 HydroReOpLLM 的環境。預設儲存格會顯示：

1. 兩案例共用的論文入流設定與 2021 年 1 月 1–7 日的教學期間；
2. 每份 YAML 所選用的 Seasonal Target 與 DKP 提示詞檔案；
3. 僅 DKP 設定具有的 `knowledge.fe_walter_operating_guidance` 參照；以及
4. 兩個入口皆通過離線設定檢查。

最後的儲存格只會列印兩行可自行選擇執行的本機 Ollama 指令。請先檢閱提示詞、以 `gemma4:12b` 啟動 Ollama、指定新的輸出路徑，並確認接受 `--allow-network` 所代表的本機網路使用，再手動執行。筆記本本身不會進行即時推論。

選擇執行前，請先閱讀 [F.E. Walter 指南](../examples/fe_walter/README.zh-TW.md)及[執行生命週期](../docs/RUNNING.zh-TW.md)。
