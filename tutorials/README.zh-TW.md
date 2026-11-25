# 用 notebook 執行 F.E. Walter

[在 GitHub 開啟 notebook](https://github.com/WenyuChiou/HydroReOpLLM/blob/main/tutorials/fe_walter.ipynb)。

開啟 notebook 可先看到通過驗證的 Rule-based 結果表和圖。要重跑時，在 clone 下來的專案使用 Python 3.12 或更新版本安裝套件，再啟動 JupyterLab。

```sh
python -m pip install -c environment/requirements-bundled.txt . jupyterlab
python -m jupyterlab tutorials/fe_walter.ipynb
```

選擇已安裝 HydroReOpLLM 的 Python 環境，按 **Run All**。筆記本會離線執行並驗證 2021 年 1 月 1–7 日的 Rule-based 基準，顯示每日結果表、入流、控制放流與蓄水量圖，以及儲存結果的位置。看完結果後，再檢查兩個 LLM 案例分別使用哪些提示詞和操作指引。

想跑 **Without operational knowledge** 和 **With operational knowledge** 時，先啟動已有 `gemma4:12b` 的本機 Ollama，再把 `RUN_LLM` 設為 `True` 並執行最後兩格。筆記本會把兩組 LLM 結果與 Rule-based 畫在一起。預設為 `False`，直接 Run All 可離線執行。

完整研究期間的執行方式見 [F.E. Walter 指南](../examples/fe_walter/README.zh-TW.md)，輸出檔的解讀方式見[結果指南](../docs/RESULTS_GUIDE.zh-TW.md)。
