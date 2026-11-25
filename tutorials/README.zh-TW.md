# 離線合成案例教學

本教學筆記本會讀取隨附的單庫測試範例、檢核其水量平衡，並執行命令列工作流程，全程無須網路連線，也不會呼叫任何模型服務。

請於專案根目錄中，在同一個環境安裝 Jupyter 並開啟筆記本。

```powershell
python -m pip install jupyterlab
jupyter lab tutorials/offline_synthetic.ipynb
```

請選擇專案環境作為核心，並依序執行各個儲存格。筆記本會在作業系統的暫存目錄下建立暫時設定檔與輸出檔案，完成後隨即刪除，不會更動隨附範例。筆記本刻意未保留已儲存的輸出結果與執行計數。

執行完水量平衡儲存格後，可將畫面顯示的狀態轉換欄位對照 `reservoir_trajectory.csv`：請求放流量為操作員的決策動作，控制放流量為物理模型實際套用的出流口流量，溢流量另行獨立計算，而期末庫容會成為下一個時間步的期初庫容。若需保留命令列執行結果並查看完整追蹤清單，請參閱[結果判讀指南](../docs/RESULTS_GUIDE.zh-TW.md)。

[使用文件](../docs/README.zh-TW.md) · [範例檔案](../examples/daily_offline/README.zh-TW.md)
