# FE Walter：每日耦合流程

[English](coupling.md) | [繁體中文](coupling.zh-TW.md) · [案例](README.zh-TW.md)

先閱讀[目前的 FE Walter 教學](../../tutorials/fe_walter.md)，再在此跟著一天的決策查看共同模擬。
三種方法改變決策來源，水庫物理與 routing 使用相同介面。

## 1. 目前範例執行什麼

上游模擬已使用**氣象 → GWLF → Lohmann routing**產生壩址入流。
操作執行器讀取這份保存的序列。

| 元件 | 目前 FE Walter 教學 |
|---|---|
| 上游水文 | 已模擬並保存；操作執行不重新計算 |
| 每日操作 | HydroCNHS 透過 Dam API 呼叫策略，更新蓄水並 routing 實際出流 |
| 下游河段 | Identity unit hydrograph，`UH=[1.0]`；用於介面示範，不是已校正旅行時間 |

目前 network runner 以 `assigned_Q` 提供局部流量，並使用 `RainfallRunoff: Other`；
仍然執行原生每日 Dam／routing 迴圈。修改產流參數不會改變已凍結的入流 CSV。

若操作不回饋上游水文，預先計算入流可以與同一次執行內計算等價。
前提是輸入、初始條件、日期及 routing 相同，而且同一份水沒有重複 routing。

## 2. 跟著共同的每日時鐘

第 **t** 日，host 先把上游可用水 routing 到水庫。
本回溯模擬提供當日已模擬的平均入流；它不是即時入流預報。

| 步驟 | 過程 | 傳給後續的資訊 |
|---|---|---|
| 1 | 準備決策資訊 | 已 routing 的入流、期初蓄水／水位，以及決策當時可取得的資訊 |
| 2 | 執行規則或 LLM 方法 | Requested release；LLM 方法另保留理由與方法專用欄位 |
| 3 | 檢查回覆並執行水庫物理 | 實際受控放流、spill 與期末蓄水 |
| 4 | Routing 總出流並保存紀錄 | 受控放流 + spill 只進河網一次；trace 保留檢查與原始 audit 判定 |
| 5 | 前進至第 t + 1 日 | 期末蓄水成為期初蓄水；下一次 prompt 取得實際放流歷史 |

本教學的損失為零，每日收支為
`期末蓄水 = 期初蓄水 + 86400 ×（入流 − 受控放流 − spill）`，
流量使用 m³/s，蓄水使用 m³。

LLM 改變蓄水與下游流量，不修改 GWLF 參數或上游氣象。
若使用模擬下游測站作為回饋，必須取已完成的前一步；
當日放流造成的 routing 結果，在當日決策之前尚不可取得。

## 3. 接入由氣象驅動的原生執行

目前的 experiment CLI 已分兩階段連接氣象與水庫操作：`prepare` 計算並保存上游入流，
`run` 再逐日執行水庫操作與下游 routing，設定入口是 `coupled/current/experiment.yaml`。
以下是進階的**原生 host 整合步驟**，供需要直接將 agent 接入自己 HydroCNHS host 的研究者使用；
一般使用者可直接使用上述正式入口。

1. **準備另一份原生模型。** 複製水文設定，保留真實子集水區的氣象、面積、GWLF 參數與 Lohmann routing。
   水文 warm-up／前置狀態與水庫初始蓄水需分別準備。
2. **加入 Dam 連接。** 在原生 module path 註冊 `llm_reservoir_abm.py`，
   並在 `WaterSystem.ABM.DamAPI` 註冊 `LLMReservoirAgent`。
   依各庫 profile 提供 `ABM.LLMReservoirAgent.<name>.Attributes.Physical`。
   `Inputs.Links` 設定一個已 routing 的 inlet 為 `-1`，agent 自己的出口名稱為 `+1`；
   下游 routing 必須接該出口。
3. **綁定操作方法。** 每個受控 agent 接上獨立、提供 `decide(observation)` 的 policy。
   原生 agent 的簡易 `Attributes.Policy` 設定不會建立 experiment 的 LLM backend。
   重用已設定的 policy、prompt、knowledge、回覆檢查與 auditor，
   並保留 `record_transition` 回饋，提供實際放流歷史。
4. **連接資訊與證據。** 將選定的 information builder 綁定該原生模型。
   Prompt／回覆 trace、audit 與已執行操作需接上同一 run 的輸出 writer；
   單獨呼叫原生 model 不會匯出 experiment runner 的完整證據包。
5. **驗證順序，再執行原生 host。** 執行前，對各 agent 呼叫
   `verify_simulation_sequence(model.sys_parsed_data["SimSeq"])`。
   順序必須是已 routing 的 inlet → Dam 操作 → 下游 routing。
   以 `model.run(temp, prec, pet)` 提供氣象。
   需要模擬產流的真實子集水區，不可再用 `assigned_Q` 覆蓋；計算用匯總 placeholder 仍需指定零局部產流。

**原生執行細節。** 隨附核心在開始時先計算整段產流序列，之後逐日執行 routing 與 agents。
「每日耦合」指共同時鐘與因果資訊交換。
若土地利用或其他過程會在決策後改變產流，需另接明確且經測試的回饋整合。

## 4. 擴充到連接的多水庫

各節點提供局部／增量集水區入流。上游水庫出流由河網 routing，
不可又加進下游的 local-inflow CSV。旅行時間決定它何時到達下一座水庫。

每座受控水庫需自己的物理 profile、policy 與歷史；被動出口不需要 LLM。
詳見[多水庫](../../tutorials/advanced.ipynb)與[決策資訊](../../docs/INFORMATION.zh-TW.md)。

## 5. 驗證連接

目前教學可查看[保存決策與結果](results.zh-TW.md)。
新的氣象驅動整合，在模型請求前需驗證以下連接：

| 連接 | 所需證據 |
|---|---|
| 氣象 → 壩址入流 | 已接受的輸入、參數、前置條件與上游 routing；條件一致時對照水文參考 |
| Dam → 河網 | 只更新一次蓄水、只注入一次受控放流 + spill；水庫與河網收支閉合 |
| 今日 → 下一次決策 | 日期連續、期末接期初蓄水、實際放流歷史；沒有未來測站資訊 |
| 決策 → 證據 | Requested／implemented release、原始 audit 與 trace 來源保持連結 |

保存的三日範例僅驗證給定入流的整合。
氣象到操作的執行證據，請見英文[2016 年耦合結果](results.md)。
保存檔驗證不代表操作策略已通過驗收。

接著閱讀[規則式操作](benchmark/README.zh-TW.md)、
[使用可用資訊的 LLM](zero_shot/README.zh-TW.md)，或[使用檢索知識的 LLM](dkp/README.zh-TW.md)。

來源細節：[原生 HydroCNHS 設定](../../docs/HYDROLOGY_SETUP.md) ·
[原生模擬](../../src/hydrocnhs/hydrocnhs.py) ·
[目前 network runner](../../src/llm_reservoir_agent/network.py) · [Dam agent](../../src/llm_reservoir_agent/agent.py)。
