# 用升級版 HydroCNHS 執行 FE Walter

[English](README.md) | [繁體中文](README.zh-TW.md) · [全部範例](../README.zh-TW.md)

三種方法共用 FE Walter 入流、物理設定與河網。這些是**本框架的使用範例**；
來源程式提供決策邏輯與 prompt 慣例，模擬由本 repo 執行。

| 方法 | 完整步驟 | 離線 YAML | 決策來源 |
|---|---|---|---|
| Hanasaki-based benchmark | [操作](benchmark/README.zh-TW.md) | [YAML](benchmark/experiment.yaml) | 決定性的防洪放流規則 |
| Zero-shot | [操作](zero_shot/README.zh-TW.md) | [YAML](zero_shot/experiment.tutorial.yaml) | 保留 prompt／schema，使用合成回覆 |
| DKP | [操作](dkp/README.zh-TW.md) | [YAML](dkp/experiment.tutorial.yaml) | 保留 prompt、知識檢索，使用合成回覆 |

1. 依[首頁](../../README.zh-TW.md)安裝。
2. 查看共同 [case](../../cases/fe_walter_reference/case.json) 與
   [入流 CSV](../../cases/fe_walter_reference/inflows.csv)：daily 2016-01-01–03、m³/s、
   初始蓄水 1,992.61 acre-ft、零損失，下游 `UH=[1.0]`。
3. 開啟上表中方法的操作頁，查看 YAML、prompt／知識或統計資料。
4. 使用該 YAML 執行 `check → run → verify --require-offline`。
5. 查看蓄水／放流、下游流量、audit 與 raw trace。再次執行請換 `run_id`／`output`；
   已有結果不會覆寫。

## 共用模擬路徑

`run_experiment.py → workflow → experiment → network → hydrocnhs.Model.run`

HydroCNHS 將入流 routing 至 Dam agent；決策 backend 提出放流，共同物理程式執行放流、
spill 及蓄水更新，將 total outflow 注入下游一次。實際結果回饋至隔日歷史。
三種方法都走這條執行鏈，使用共同 audit／trace writer。

本例使用**固定、已完成上游 routing 的模擬入流**，以 `assigned_Q` 傳給原生 HydroCNHS。
實際執行 Dam 耦合與下游 routing，沒有重算降雨產流。完整產流設定見[水文手冊](../../docs/HYDROLOGY_SETUP.md)。
初始蓄水與 identity routing 是診斷假設，尚未證明真實實驗 readiness。

## 策略來源

兩個 LLM 範例透過本 repo 的 `reference_v3_7` adapter，保留 Anik V3.7 system 文字、
每日 prompt 格式、schema、檢索與策略 audit。這個 selector 指的是策略相容 adapter，
模擬仍由本框架執行。Benchmark 只改編固定版本的放流函數。來源檔案及 hashes 保留供重現，
各方法操作頁提供連結。離線合成回覆不能評估 LLM 策略品質；真實 YAML 維持 temperature
**0.7**，執行前仍需[readiness 檢查](../../docs/LIVE_READINESS.md)。
