# 未提供額外操作知識的 LLM

[English](README.md) | [繁體中文](README.zh-TW.md)

從 [FE Walter 教學](../../../tutorials/README.md)的共用
`experiment.yaml` 開始，再選擇這個方法。目前維護的檔案如下：

| 檔案 | 用途 |
|---|---|
| [llm_available.yaml](../coupled/llm_available.yaml) | 選擇此方法，引用共用水文與水庫設定 |
| [agents.llm_available.yaml](../coupled/agents.llm_available.yaml) | 連接水庫、system 指令與選用資訊 |
| [available_information.txt](../prompts/available_information.txt) | 目前使用的 system 指令 |

[2016 年結果](../results.zh-TW.md)展示已保存的水位與放流量，來源會註明執行時使用的指令。

此舊目錄名稱保留為文件連結。先前的可執行設定與 prompt 快照保存在[恢復索引](../../../archive/fe_walter/README.md)。
