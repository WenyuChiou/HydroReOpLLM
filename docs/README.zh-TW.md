# 概覽

[English](README.md) | [繁體中文](README.zh-TW.md)

HydroOpsLLM 將水庫決策接入 HydroCNHS 水文模擬。
水文模型產生河川流量並送入水庫；每個時間步，LLM 根據可用資訊提出放流建議。

共同水庫計算決定實際放流、溢流與蓄水，再將出流送往下游。
更新後的條件提供給下一次決策，形成持續循環。
目前案例採每日時間步；規則式 agent 也可使用相同水庫計算進行比較。

![HydroOpsLLM 核心流程](figures/hydrocnhs-coupling-framework-en.png)

[高清 PNG](figures/hydrocnhs-coupling-framework-en.png) · [180 mm 向量 PDF](figures/hydrocnhs-coupling-framework-en.pdf)。

先從[安裝](GETTING_STARTED.md)開始，再[建立模擬](BUILD_SIMULATION.zh-TW.md)，
接著進入 [FE Walter 案例](../examples/fe_walter/README.zh-TW.md)。
