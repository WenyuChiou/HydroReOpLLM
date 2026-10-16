# HydroOpsLLM 使用範例

[English](README.md) | [繁體中文](README.zh-TW.md)

請從 [FE Walter 完整示範](fe_walter/README.zh-TW.md)開始。三種決策方法共用原生
HydroCNHS Dam 耦合與 routing，並使用 HydroOpsLLM 新增的共同水庫物理計算與 audit／trace。

套用到新流域時，請將本 repo 的[水文設定](../docs/HYDROLOGY_SETUP.md)與
[HydroCNHS 官方文件](https://cylin928.github.io/HydroCNHS/)搭配使用，設定產流、
參數、routing、校正與驗證。合成離線設定與既有教學 notebooks 仍保留供開發驗證；
預設使用者示範則執行範圍受限的本機 Ollama 案例。
