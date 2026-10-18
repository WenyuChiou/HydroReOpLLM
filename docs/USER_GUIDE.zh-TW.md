# 使用指南

[English](USER_GUIDE.md) | [繁體中文](USER_GUIDE.zh-TW.md)

保留已接受的 HydroCNHS 水文模型，再加入水庫蓄水、河網與操作 agent。請依序閱讀，
每個設定章節都會展示完整檔案。

1. [安裝](GETTING_STARTED.md)：安裝套件並檢查指令。
2. [設定總覽](INPUT_OUTPUT.md)：了解需要哪些檔案。
3. [全域設定](GLOBAL_SETTINGS.md)：決定日期、執行名稱與輸出位置。
4. [水文](HYDROLOGY_SETUP.md)：提供原生模型與氣象資料。
5. [水庫與河網](BUILD_SIMULATION.zh-TW.md)：連接入流、蓄水與下游。
6. [Agents 與 LLM](CONFIGURATION.md)：選擇規則或 LLM，再設定 prompt 與資訊。
7. [檢查與執行](RUNNING.md)：驗證設定、準備入流、執行與查核。
8. [案例](CASE_STUDIES.md)：依完整研究範例操作。
9. [結果](RESULTS_GUIDE.md)：區分建議放流、實際放流、溢流與水位。
10. [問題排查](TROUBLESHOOTING.md)：診斷無效或未完成結果。
11. [API 文件](API_REFERENCE.md)：查詢設定對應的函數。

[模板清單](TEMPLATES.md)集中列出通用設定。相對路徑以宣告它的檔案為起點。
Profile 是一組具名設定，例如某個模型設定；共用 profile 不會共用水庫狀態與歷史。

HydroCNHS 先計算上游入流，再進行逐日水庫操作。更換 operator 不會改變已保存的
上游水文。Agent 提出控制放流，水庫物理計算決定實際放流、溢流與剩餘蓄水，
下一天從該結果繼續。

集水區建置、參數估計與校正驗證請參考
[HydroCNHS 官方教學](https://github.com/cylin928/HydroCNHS/tree/main/tutorials)；
本手冊集中說明新增的水庫與 LLM 功能。
